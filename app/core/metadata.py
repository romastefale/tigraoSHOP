from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class PageMetadata:
    title: str | None = None
    image_url: str | None = None
    price: str | None = None


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
        return text
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


def _find_jsonld_price(content: str) -> str | None:
    scripts = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for raw_script in scripts:
        cleaned = html.unescape(raw_script).strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            continue
        for node in _walk_json(data):
            if not isinstance(node, dict):
                continue
            price = node.get("price") or node.get("lowPrice") or node.get("highPrice")
            currency = node.get("priceCurrency") or node.get("currency")
            if price:
                formatted = _format_brl(price)
                if formatted and (not currency or str(currency).upper() in {"BRL", "R$"}):
                    return formatted
                return formatted
    return None


def _find_regex_price(content: str) -> str | None:
    patterns = [
        r'"price"\s*:\s*"?(\d{2,7}(?:[\.,]\d{2})?)"?',
        r'"amount"\s*:\s*"?(\d{2,7}(?:[\.,]\d{2})?)"?',
        r'R\$\s*\d{1,3}(?:\.\d{3})*,\d{2}',
        r'R\$\s*\d{2,7},\d{2}',
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if not match:
            continue
        value = match.group(1) if match.groups() else match.group(0)
        formatted = _format_brl(value)
        if formatted:
            return formatted
    return None


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
            content = response.text[:600_000]
    except Exception:
        return PageMetadata()

    return PageMetadata(
        title=_find_meta(content, "og:title", "twitter:title") or _find_title(content),
        image_url=_find_meta(content, "og:image", "twitter:image"),
        price=(
            _find_meta(content, "product:price:amount", "og:price:amount", "price", "twitter:data1")
            or _find_jsonld_price(content)
            or _find_regex_price(content)
        ),
    )
