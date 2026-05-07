from __future__ import annotations

import re
from urllib.parse import urlparse

from app.core.models import ProductInput, Store
from app.core.security import normalize_user_url

URL_RE = re.compile(r"https?://[^\s<>]+|www\.[^\s<>]+", re.IGNORECASE)
MLB_RE = re.compile(r"\bMLB-?\d{6,}\b", re.IGNORECASE)
ML_SHORT_CODE_RE = re.compile(r"\b[A-Z0-9]{4,8}-[A-Z0-9]{3,8}\b", re.IGNORECASE)
ASIN_RE = re.compile(r"\bB0[A-Z0-9]{8}\b|\b\d{9}[0-9X]\b", re.IGNORECASE)
SHOPEE_DOT_RE = re.compile(r"(?:i\.)?(\d{5,})\.(\d{5,})")
SHOPEE_PRODUCT_RE = re.compile(r"/product/(\d{5,})/(\d{5,})", re.IGNORECASE)
ALIEXPRESS_ITEM_RE = re.compile(r"/(?:item/)?(\d{8,})\.html", re.IGNORECASE)
MAGALU_SKU_RE = re.compile(r"/(?:p/)?([a-z0-9]{5,})/?(?:\?|$)", re.IGNORECASE)
PRICE_RE = re.compile(
    r"(?:preço\s*base|somente|por\s+apenas|por|preço)\s*:?\s*R\$\s*([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}|[0-9]{1,7},[0-9]{2})",
    re.IGNORECASE,
)


def detect_store_from_url(url: str) -> Store:
    host = (urlparse(url).netloc or "").lower()
    if "mercadolivre" in host or "mercadolibre" in host or "meli." in host:
        return Store.MERCADOLIVRE
    if "shopee" in host or "shp.ee" in host or "shope.ee" in host:
        return Store.SHOPEE
    if "amazon" in host or host in {"a.co", "amzn.to"} or "amzn." in host:
        return Store.AMAZON
    if "aliexpress" in host or "aliexpi" in host:
        return Store.ALIEXPRESS
    if "magazineluiza" in host or "magalu" in host or "maga.lu" in host or "magazinevoce" in host:
        return Store.MAGALU
    return Store.UNKNOWN


def detect_store_from_id(text: str) -> Store:
    if MLB_RE.search(text) or ML_SHORT_CODE_RE.search(text):
        return Store.MERCADOLIVRE
    if ASIN_RE.search(text):
        return Store.AMAZON
    if SHOPEE_DOT_RE.search(text):
        return Store.SHOPEE
    return Store.UNKNOWN


def extract_product_id(store: Store, text: str) -> str | None:
    if store == Store.MERCADOLIVRE:
        match = MLB_RE.search(text)
        if match:
            return match.group(0).replace("-", "").upper()
        path_match = re.search(r"/MLB-?(\d{6,})", text, re.IGNORECASE)
        if path_match:
            return f"MLB{path_match.group(1)}"
    if store == Store.AMAZON:
        asin_path = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", text, re.IGNORECASE)
        if asin_path:
            return asin_path.group(1).upper()
        match = ASIN_RE.search(text)
        if match:
            return match.group(0).upper()
    if store == Store.SHOPEE:
        product_match = SHOPEE_PRODUCT_RE.search(text)
        if product_match:
            return f"{product_match.group(1)}.{product_match.group(2)}"
        dot_match = SHOPEE_DOT_RE.search(text)
        if dot_match:
            return f"{dot_match.group(1)}.{dot_match.group(2)}"
    if store == Store.ALIEXPRESS:
        match = ALIEXPRESS_ITEM_RE.search(text)
        if match:
            return match.group(1)
    if store == Store.MAGALU:
        parsed = urlparse(text)
        match = MAGALU_SKU_RE.search(parsed.path or "")
        if match:
            return match.group(1)
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
        r"\s+Encontre\s+na\s+Shopee\s+agora!?$",
        r"\s+Compre\s+na\s+Shopee.*$",
        r"\s+Encontre\s+no\s+Mercado\s+Livre\s+agora!?$",
        r"\s+Confira\s+no\s+Mercado\s+Livre.*$",
        r"\s+na\s+Amazon\s+agora!?$",
        r"\s+Confira\s+na\s+Amazon.*$",
        r"\s+Encontre\s+no\s+AliExpress.*$",
        r"\s+Compre\s+no\s+AliExpress.*$",
        r"\s+Encontre\s+no\s+Magalu.*$",
        r"\s+Compre\s+no\s+Magalu.*$",
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
