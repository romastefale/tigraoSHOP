from __future__ import annotations

import re
from urllib.parse import urlparse

from app.core.models import ProductInput, Store
from app.core.security import normalize_user_url

URL_RE = re.compile(r"https?://[^\s<>]+|www\.[^\s<>]+", re.IGNORECASE)
MLB_RE = re.compile(r"\bMLB-?\d{6,}\b", re.IGNORECASE)
ML_SHORT_CODE_RE = re.compile(r"\b[A-Z0-9]{4,8}-[A-Z0-9]{3,8}\b", re.IGNORECASE)
PRICE_RE = re.compile(
    r"(?:preço\s*base|somente|por\s+apenas|por|preço)\s*:?\s*R\$\s*([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}|[0-9]{1,7},[0-9]{2})",
    re.IGNORECASE,
)


def detect_store_from_url(url: str) -> Store:
    host = (urlparse(url).netloc or "").lower()
    if "mercadolivre" in host or "mercadolibre" in host or "meli." in host:
        return Store.MERCADOLIVRE
    return Store.UNKNOWN


def detect_store_from_id(text: str) -> Store:
    if MLB_RE.search(text) or ML_SHORT_CODE_RE.search(text):
        return Store.MERCADOLIVRE
    return Store.UNKNOWN


def extract_product_id(store: Store, text: str) -> str | None:
    if store == Store.MERCADOLIVRE:
        match = MLB_RE.search(text)
        if match:
            return match.group(0).replace("-", "").upper()
        path_match = re.search(r"/MLB-?(\d{6,})", text, re.IGNORECASE)
        if path_match:
            return f"MLB{path_match.group(1)}"
    return None


def extract_ml_short_code(text: str | None) -> str | None:
    raw = (text or "").strip()
    if not raw or URL_RE.search(raw):
        return None
    match = ML_SHORT_CODE_RE.search(raw)
    if not match:
        return None
    return match.group(0).upper()


def ml_short_code_url(code: str) -> str:
    return f"https://www.mercadolivre.com.br/sec/{code}"


def extract_shared_price(text: str | None) -> str | None:
    raw = (text or "").strip()
    if not raw:
        return None
    match = PRICE_RE.search(raw)
    if not match:
        return None
    value = match.group(1).strip()
    return f"R$ {value}"


def strip_shared_app_text(text: str | None) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    without_urls = URL_RE.sub("", raw)
    patterns = [
        r"^Confira\s+",
        r"^Olha\s+só\s+",
        r"^Veja\s+",
        r"\s+com\s+\d+%\s+de\s+desconto!?$",
        r"\s+Somente\s+R\$\s*[\d\.,]+\.?$",
        r"\s+Por\s+apenas\s+R\$\s*[\d\.,]+\.?$",
        r"\s+Preço\s+base\s*:\s*R\$\s*[\d\.,]+\.?$",
        r"\s+Encontre\s+no\s+Mercado\s+Livre\s+agora!?$",
        r"\s+Confira\s+no\s+Mercado\s+Livre.*$",
    ]
    cleaned = without_urls
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -–—|,.;!\n\t ")
    return cleaned or raw


def parse_offer_input(text: str | None, photo_file_id: str | None = None, force_search: bool = False) -> ProductInput:
    raw = (text or "").strip()
    url_match = URL_RE.search(raw)
    cleaned_query = strip_shared_app_text(raw)
    shared_price = extract_shared_price(raw)
    if url_match:
        url = normalize_user_url(url_match.group(0))
        store = detect_store_from_url(url)
        return ProductInput(
            source="reply_photo" if photo_file_id else "url",
            store=store,
            raw_text=raw,
            url=url,
            product_id=extract_product_id(store, url),
            query=cleaned_query if cleaned_query and cleaned_query != url else None,
            shared_price=shared_price,
            photo_file_id=photo_file_id,
        )

    store = detect_store_from_id(raw)
    product_id = extract_product_id(store, raw)
    if product_id:
        return ProductInput(
            source="reply_photo" if photo_file_id else "id",
            store=store,
            raw_text=raw,
            product_id=product_id,
            query=cleaned_query or None,
            shared_price=shared_price,
            photo_file_id=photo_file_id,
        )

    short_code = extract_ml_short_code(raw)
    if short_code:
        return ProductInput(
            source="reply_photo" if photo_file_id else "url",
            store=Store.MERCADOLIVRE,
            raw_text=raw,
            url=ml_short_code_url(short_code),
            product_id=None,
            query=None,
            shared_price=shared_price,
            photo_file_id=photo_file_id,
        )

    return ProductInput(
        source="search" if force_search or raw else "empty",
        store=Store.UNKNOWN,
        raw_text=raw,
        query=cleaned_query or raw or None,
        shared_price=shared_price,
        photo_file_id=photo_file_id,
    )
