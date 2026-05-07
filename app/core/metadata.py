from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx


@dataclass(slots=True)
class PageMetadata:
    title: str | None = None
    image_url: str | None = None
    price: str | None = None
    price_source: str | None = None


def _find_meta(content: str, *names: str) -> str | None:
    for name in names:
        patterns = [
            rf'<meta[^>]+property=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(name)}["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{re.escape(name)}["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return html.unescape(match.group(1)).strip()
    return None


def _find_title(content: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return html.unescape(title)


def _format_brl(value: object) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if text.startswith("R$"):
        return re.sub(r"\s+", " ", text)
    try:
        number = float(text.replace(".", "").replace(",", ".") if "," in text else text)
    except ValueError:
        return None
    if number <= 0:
        return None
    formatted = f"R$ {number:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _walk_json(value: Any) -> list[Any]:
    nodes = [value]
    if isinstance(value, dict):
        for item in value.values():
            nodes.extend(_walk_json(item))
    elif isinstance(value, list):
        for item in value:
            nodes.extend(_walk_json(item))
    return nodes


def _jsonld_type(node: dict[str, Any]) -> set[str]:
    raw_type = node.get("@type") or node.get("type")
    if isinstance(raw_type, list):
        return {str(item).lower() for item in raw_type}
    if raw_type:
        return {str(raw_type).lower()}
    return set()


def _iter_jsonld(content: str) -> list[Any]:
    scripts = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    parsed: list[Any] = []
    for raw_script in scripts:
        cleaned = html.unescape(raw_script).strip()
        try:
            parsed.append(json.loads(cleaned))
        except json.JSONDecodeError:
            continue
    return parsed


def _find_jsonld_image(content: str) -> str | None:
    for data in _iter_jsonld(content):
        for node in _walk_json(data):
            if not isinstance(node, dict):
                continue
            image = node.get("image") or node.get("thumbnailUrl")
            if isinstance(image, str) and image.startswith("http"):
                return image
            if isinstance(image, list):
                for item in image:
                    if isinstance(item, str) and item.startswith("http"):
                        return item
                    if isinstance(item, dict):
                        url = item.get("url") or item.get("contentUrl")
                        if isinstance(url, str) and url.startswith("http"):
                            return url
    return None


def _find_jsonld_price(content: str) -> tuple[str | None, str | None]:
    for data in _iter_jsonld(content):
        for node in _walk_json(data):
            if not isinstance(node, dict):
                continue
            node_types = _jsonld_type(node)
            is_product_or_offer = bool(node_types & {"product", "offer", "aggregateoffer"})
            if not is_product_or_offer and not any(key in node for key in ("offers", "priceSpecification")):
                continue
            price = node.get("price") or node.get("lowPrice") or node.get("highPrice")
            currency = node.get("priceCurrency") or node.get("currency")
            if price:
                formatted = _format_brl(price)
                if formatted and (not currency or str(currency).upper() in {"BRL", "R$"}):
                    return formatted, "jsonld_product_offer"
    return None, None


def _is_safe_product_price_context(url: str, content: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    host = parsed.netloc.lower()
    blocked_paths = ("/social/", "/loja/", "/stores/", "/search", "/lista/", "/ofertas")
    if any(part in path for part in blocked_paths):
        return False
    if "mercadolivre" in host and "/p/" not in path and not re.search(r"/MLB-?\d+", path, re.IGNORECASE):
        return False
    product_markers = (
        'property="product:price:amount"',
        "property='product:price:amount'",
        '"@type":"Product"',
        '"@type": "Product"',
        '"@type":"Offer"',
        '"@type": "Offer"',
    )
    return any(marker in content for marker in product_markers)


def _trusted_meta_price(content: str) -> tuple[str | None, str | None]:
    raw = _find_meta(content, "product:price:amount", "og:price:amount")
    formatted = _format_brl(raw)
    return (formatted, "product_meta") if formatted else (None, None)


async def fetch_metadata(url: str, timeout: float = 4.0) -> PageMetadata:
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36 tigraoSHOP",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            },
        ) as client:
            response = await client.get(url)
            final_url = str(response.url)
            content = response.text[:600_000]
    except Exception:
        return PageMetadata()

    image_url = _find_meta(content, "og:image", "twitter:image") or _find_jsonld_image(content)
    price = None
    price_source = None
    if _is_safe_product_price_context(final_url, content):
        price, price_source = _trusted_meta_price(content)
        if not price:
            price, price_source = _find_jsonld_price(content)

    return PageMetadata(
        title=_find_meta(content, "og:title", "twitter:title") or _find_title(content),
        image_url=image_url,
        price=price,
        price_source=price_source,
    )
