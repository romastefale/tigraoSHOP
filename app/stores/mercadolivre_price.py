from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.security import normalize_user_url

ITEM_ID_RE = re.compile(r"\bMLB-?(\d{6,})\b", re.IGNORECASE)
META_RE_TEMPLATE = r'<meta[^>]+(?:property|name)=["\']{name}["\'][^>]+content=["\']([^"\']+)["\']|<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{name}["\']'
CANONICAL_RE = re.compile(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']|<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']canonical["\']', re.IGNORECASE | re.DOTALL)
JSONLD_RE = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.IGNORECASE | re.DOTALL)
SCRIPT_ID_RE = re.compile(r'["\'](?:id|item_id|itemId)["\']\s*:\s*["\']?(MLB-?\d{6,})["\']?', re.IGNORECASE)
SCRIPT_PRICE_RE = re.compile(r'["\'](?:price|sale_price|current_price|amount|priceAmount)["\']\s*:\s*(?:["\']?)(\d+(?:\.\d{1,2})?)(?:["\']?)', re.IGNORECASE)
VISIBLE_ML_PRICE_RE = re.compile(
    r'andes-money-amount__fraction[^>]*>\s*([0-9\.]+)\s*</[^>]+>(?:\s*<[^>]*andes-money-amount__cents[^>]*>\s*([0-9]{2})\s*</[^>]+>)?',
    re.IGNORECASE | re.DOTALL,
)
BRL_TEXT_PRICE_RE = re.compile(r"R\$\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?|[0-9]{1,7},[0-9]{2})")


@dataclass(slots=True)
class PriceEvidence:
    value: float
    source: str
    confidence: int
    item_id: str | None = None

    @property
    def formatted(self) -> str:
        formatted = f"R$ {self.value:,.2f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


@dataclass(slots=True)
class PriceDecision:
    ok: bool
    price: str | None = None
    raw_price: float | None = None
    title: str | None = None
    image_url: str | None = None
    final_url: str | None = None
    item_id: str | None = None
    source: str | None = None
    confidence: int = 0
    reason: str = ""
    evidences: list[PriceEvidence] = field(default_factory=list)


def is_mercadolivre_url(url: str) -> bool:
    host = (urlparse(url).netloc or "").lower()
    return "mercadolivre" in host or "mercadolibre" in host or "meli." in host


def normalize_ml_image_url(url: str | None) -> str | None:
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return None
    return url.replace("http://", "https://").strip()


def clean_item_id(value: str | None) -> str | None:
    if not value:
        return None
    match = ITEM_ID_RE.search(value)
    if not match:
        return None
    return f"MLB{match.group(1)}"


def extract_item_id(*values: str | None) -> str | None:
    for value in values:
        item_id = clean_item_id(value)
        if item_id:
            return item_id
    return None


def _find_meta(content: str, name: str) -> str | None:
    pattern = META_RE_TEMPLATE.format(name=re.escape(name))
    match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return html.unescape((match.group(1) or match.group(2) or "").strip()) or None


def _find_canonical(content: str) -> str | None:
    match = CANONICAL_RE.search(content)
    if not match:
        return None
    return html.unescape((match.group(1) or match.group(2) or "").strip()) or None


def _find_title(content: str) -> str | None:
    title = _find_meta(content, "og:title") or _find_meta(content, "twitter:title")
    if title:
        return re.sub(r"\s+", " ", title).strip()
    match = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return html.unescape(re.sub(r"\s+", " ", match.group(1)).strip())


def _find_image(content: str) -> str | None:
    image = _find_meta(content, "og:image") or _find_meta(content, "twitter:image")
    return normalize_ml_image_url(image)


def _best_image_from_item(item_data: dict[str, Any], fallback: str | None = None) -> str | None:
    pictures = item_data.get("pictures")
    if isinstance(pictures, list):
        for picture in pictures:
            if isinstance(picture, dict):
                for key in ("secure_url", "url"):
                    url = normalize_ml_image_url(picture.get(key))
                    if url:
                        return url
    for key in ("secure_thumbnail", "thumbnail"):
        url = normalize_ml_image_url(item_data.get(key))
        if url:
            return url
    return normalize_ml_image_url(fallback)


def _parse_price(value: object) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip().replace("R$", "").strip()
        text = re.sub(r"[^0-9\.,]", "", text)
        if not text:
            return None
        try:
            number = float(text.replace(".", "").replace(",", ".") if "," in text else text)
        except ValueError:
            return None
    if number <= 0:
        return None
    return round(number + 1e-9, 2)


def _iter_jsonld(content: str) -> list[Any]:
    parsed: list[Any] = []
    for raw in JSONLD_RE.findall(content):
        try:
            parsed.append(json.loads(html.unescape(raw).strip()))
        except json.JSONDecodeError:
            continue
    return parsed


def _walk(value: Any) -> list[Any]:
    nodes = [value]
    if isinstance(value, dict):
        for child in value.values():
            nodes.extend(_walk(child))
    elif isinstance(value, list):
        for child in value:
            nodes.extend(_walk(child))
    return nodes


def _jsonld_evidences(content: str, item_id: str | None) -> list[PriceEvidence]:
    evidences: list[PriceEvidence] = []
    for data in _iter_jsonld(content):
        for node in _walk(data):
            if not isinstance(node, dict):
                continue
            raw_type = node.get("@type") or node.get("type")
            types = {str(raw_type).lower()} if raw_type and not isinstance(raw_type, list) else {str(t).lower() for t in raw_type or []}
            if not (types & {"product", "offer", "aggregateoffer"}) and not any(key in node for key in ("offers", "priceSpecification")):
                continue
            price = _parse_price(node.get("price") or node.get("lowPrice") or node.get("highPrice"))
            currency = str(node.get("priceCurrency") or node.get("currency") or "BRL").upper()
            if price and currency in {"BRL", "R$"}:
                evidences.append(PriceEvidence(price, "jsonld_offer", 95 if item_id else 88, item_id))
    return evidences


def _visible_price_evidences(content: str, item_id: str | None) -> list[PriceEvidence]:
    evidences: list[PriceEvidence] = []
    for fraction, cents in VISIBLE_ML_PRICE_RE.findall(content[:900_000]):
        raw = fraction.replace(".", "")
        if cents:
            raw += "." + cents
        price = _parse_price(raw)
        if price:
            evidences.append(PriceEvidence(price, "visible_ml_price", 94 if item_id else 90, item_id))
            break
    if evidences:
        return evidences
    for raw in BRL_TEXT_PRICE_RE.findall(html.unescape(content[:250_000])):
        price = _parse_price(raw)
        if price:
            evidences.append(PriceEvidence(price, "visible_brl_text", 86 if item_id else 80, item_id))
            break
    return evidences


def collect_price_evidences(content: str, item_id: str | None) -> list[PriceEvidence]:
    evidences: list[PriceEvidence] = []
    for meta_name in ("product:price:amount", "og:price:amount"):
        price = _parse_price(_find_meta(content, meta_name))
        if price:
            evidences.append(PriceEvidence(price, meta_name, 96 if item_id else 90, item_id))
    evidences.extend(_jsonld_evidences(content, item_id))
    evidences.extend(_visible_price_evidences(content, item_id))
    if not evidences:
        for raw in SCRIPT_PRICE_RE.findall(content[:900_000]):
            price = _parse_price(raw)
            if price:
                evidences.append(PriceEvidence(price, "script_price", 84 if item_id else 78, item_id))
                break
    return evidences


def choose_best_evidence(evidences: list[PriceEvidence]) -> PriceEvidence | None:
    if not evidences:
        return None
    groups: dict[float, list[PriceEvidence]] = {}
    for ev in evidences:
        groups.setdefault(ev.value, []).append(ev)
    best_value, best_group = max(groups.items(), key=lambda item: (len(item[1]), max(ev.confidence for ev in item[1])))
    best = max(best_group, key=lambda ev: ev.confidence)
    if len(best_group) >= 2:
        best.confidence = max(best.confidence, 98)
    return best


def _has_variation_warning(content: str) -> bool:
    text = re.sub(r"\s+", " ", content[:250_000]).lower()
    markers = ("escolha a cor", "escolha o tamanho", "selecione a cor", "selecione o tamanho", "variação", "voltagem")
    return any(marker in text for marker in markers)


async def analyze_mercadolivre_url(url: str, timeout: float = 4.0) -> PriceDecision:
    normalized = normalize_user_url(url)
    if not is_mercadolivre_url(normalized):
        return PriceDecision(ok=False, reason="not_mercadolivre_url", final_url=normalized)
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36 tigraoSHOP",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            },
        ) as client:
            response = await client.get(normalized)
            final_url = str(response.url)
            content = response.text[:900_000]
    except Exception as exc:
        return PriceDecision(ok=False, reason=f"resolve_failed:{exc}", final_url=normalized)

    canonical = _find_canonical(content)
    og_url = _find_meta(content, "og:url")
    script_id = None
    script_match = SCRIPT_ID_RE.search(content[:900_000])
    if script_match:
        script_id = script_match.group(1)
    item_id = extract_item_id(normalized, final_url, canonical, og_url, script_id)
    title = _find_title(content)
    image = _find_image(content)

    if item_id:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                item_response = await client.get(f"https://api.mercadolibre.com/items/{item_id}")
                if item_response.status_code == 200:
                    item_data = item_response.json()
                    if isinstance(item_data, dict):
                        image = _best_image_from_item(item_data, image)
                        title = str(item_data.get("title") or title or "Produto Mercado Livre")
        except Exception:
            pass

    evidences = collect_price_evidences(content, item_id)
    best = choose_best_evidence(evidences)

    if not best:
        return PriceDecision(ok=False, title=title, image_url=image, final_url=final_url, item_id=item_id, reason="no_price_evidence", evidences=evidences)
    if best.confidence < 85:
        return PriceDecision(ok=False, title=title, image_url=image, final_url=final_url, item_id=item_id, reason="low_confidence_price", evidences=evidences)
    if _has_variation_warning(content) and best.confidence < 90:
        return PriceDecision(ok=False, title=title, image_url=image, final_url=final_url, item_id=item_id, reason="possible_required_variation", evidences=evidences)

    return PriceDecision(
        ok=True,
        price=best.formatted,
        raw_price=best.value,
        title=title,
        image_url=image,
        final_url=final_url,
        item_id=item_id,
        source=best.source,
        confidence=best.confidence,
        reason="price_evidence_confirmed",
        evidences=evidences,
    )
