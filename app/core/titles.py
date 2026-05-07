from __future__ import annotations

import re

_PRODUCT_SUFFIXES = [
    "distribuidor autorizado",
    "loja oficial",
    "envio imediato",
    "frete grátis",
    "mercado livre",
    "amazon",
    "shopee",
    "aliexpress",
    "shein",
]


def main_product_name(title: str | None, max_chars: int = 72) -> str:
    if not title:
        return "Oferta"

    value = re.sub(r"\s+", " ", title).strip(" -–—|,.;\n\t ")
    value = re.sub(r"\s+\|\s+.*$", "", value)
    value = re.sub(r"\s+em oferta.*$", "", value, flags=re.IGNORECASE)

    for suffix in _PRODUCT_SUFFIXES:
        value = re.sub(rf"\s*[-–—,|]\s*{re.escape(suffix)}.*$", "", value, flags=re.IGNORECASE)

    dash_parts = re.split(r"\s+[-–—]\s+", value)
    if len(dash_parts) > 1 and len(dash_parts[0]) >= 10:
        value = dash_parts[0]

    comma_parts = [part.strip() for part in value.split(",") if part.strip()]
    if len(comma_parts) > 1 and len(comma_parts[0]) >= 10:
        value = comma_parts[0]

    value = re.sub(r"\s+", " ", value).strip(" -–—|,.;")
    if len(value) <= max_chars:
        return value

    truncated = value[:max_chars].rsplit(" ", 1)[0].strip(" -–—|,.;")
    return truncated or value[:max_chars].strip()
