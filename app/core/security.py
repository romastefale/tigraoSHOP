from __future__ import annotations

from urllib.parse import urlparse

_ALLOWED_SCHEMES = {"http", "https"}
_ALLOWED_HOST_PARTS = {
    # Shopee and Shopee app share links.
    "shopee.",
    "shp.ee",
    "shope.ee",
    # Mercado Livre / Mercado Libre.
    "mercadolivre.",
    "mercadolibre.",
    "meli.",
    # Amazon and Amazon app share links.
    "amazon.",
    "amzn.",
    "a.co",
    # AliExpress and known AliExpress link forms.
    "aliexpress.",
    "s.click.aliexpress.",
    "s.aliexpress.",
    "a.aliexpress.",
    # SHEIN and SHEIN app share links.
    "shein.",
    "shein.com",
    "shein.top",
}


def is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return False
    host = (parsed.netloc or "").lower()
    return any(part in host for part in _ALLOWED_HOST_PARTS)


def normalize_user_url(url: str) -> str:
    value = url.strip().strip("<>()[]{}.,;\n\t ")
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("www."):
        return "https://" + value
    return value
