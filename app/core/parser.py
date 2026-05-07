from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from app.core.models import ProductInput, Store
from app.core.security import normalize_user_url

URL_RE = re.compile(r"https?://[^\s<>]+|www\.[^\s<>]+", re.IGNORECASE)
MLB_RE = re.compile(r"\bMLB-?\d{6,}\b", re.IGNORECASE)
ASIN_RE = re.compile(r"\bB0[A-Z0-9]{8}\b|\b\d{9}[0-9X]\b", re.IGNORECASE)
SHOPEE_DOT_RE = re.compile(r"(?:i\.)?(\d{5,})\.(\d{5,})")
SHOPEE_PRODUCT_RE = re.compile(r"/product/(\d{5,})/(\d{5,})", re.IGNORECASE)
ALIEXPRESS_ITEM_RE = re.compile(r"/(?:item/)?(\d{8,})\.html", re.IGNORECASE)
SHEIN_ITEM_RE = re.compile(r"(?:-p-|goods_id=)(\d{5,})", re.IGNORECASE)


def detect_store_from_url(url: str) -> Store:
    host = (urlparse(url).netloc or "").lower()
    if "mercadolivre" in host or "mercadolibre" in host or "meli" in host:
        return Store.MERCADOLIVRE
    if "shopee" in host or "shp.ee" in host:
        return Store.SHOPEE
    if "amazon" in host or host in {"a.co", "amzn.to"} or "amzn." in host:
        return Store.AMAZON
    if "aliexpress" in host:
        return Store.ALIEXPRESS
    if "shein" in host:
        return Store.SHEIN
    return Store.UNKNOWN


def detect_store_from_id(text: str) -> Store:
    if MLB_RE.search(text):
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
        try:
            query = parse_qs(urlparse(text).query)
            shop_id = query.get("vShopId", [None])[0] or query.get("shopid", [None])[0]
            item_id = query.get("vItemId", [None])[0] or query.get("itemid", [None])[0]
            if shop_id and item_id:
                return f"{shop_id}.{item_id}"
        except Exception:
            return None
    if store == Store.ALIEXPRESS:
        match = ALIEXPRESS_ITEM_RE.search(text)
        if match:
            return match.group(1)
    if store == Store.SHEIN:
        match = SHEIN_ITEM_RE.search(text)
        if match:
            return match.group(1)
    return None


def strip_shared_app_text(text: str | None) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    without_urls = URL_RE.sub("", raw)
    patterns = [
        r"^Confira\s+",
        r"\s+com\s+\d+%\s+de\s+desconto!?$",
        r"\s+Somente\s+R\$\s*[\d\.,]+\.?$",
        r"\s+Encontre\s+na\s+Shopee\s+agora!?$",
        r"\s+Encontre\s+no\s+Mercado\s+Livre\s+agora!?$",
        r"\s+na\s+Amazon\s+agora!?$",
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
            photo_file_id=photo_file_id,
        )

    return ProductInput(
        source="search" if force_search or raw else "empty",
        store=Store.UNKNOWN,
        raw_text=raw,
        query=cleaned_query or raw or None,
        photo_file_id=photo_file_id,
    )
