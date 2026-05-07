from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel

SAFE_PRICE_SCHEMA_VERSION = 3


class Store(StrEnum):
    SHOPEE = "shopee"
    MERCADOLIVRE = "mercadolivre"
    AMAZON = "amazon"
    ALIEXPRESS = "aliexpress"
    SHEIN = "shein"
    UNKNOWN = "unknown"


class ProductInput(BaseModel):
    source: str
    store: Store = Store.UNKNOWN
    raw_text: Optional[str] = None
    url: Optional[str] = None
    product_id: Optional[str] = None
    query: Optional[str] = None
    shared_price: Optional[str] = None
    photo_file_id: Optional[str] = None


class OfferCard(BaseModel):
    schema_version: int = SAFE_PRICE_SCHEMA_VERSION
    store: Store
    product_id: Optional[str] = None
    title: str
    price: Optional[str] = None
    old_price: Optional[str] = None
    installments: Optional[str] = None
    currency: str = "BRL"
    image_url: Optional[str] = None
    photo_file_id: Optional[str] = None
    offer_url: str
    original_url: str
    rating: Optional[str] = None
    shipping: Optional[str] = None
    source_quality: str = "fallback"
    price_source: Optional[str] = None
    note: str = "Confira condições e disponibilidade abrindo a loja."


class StoreResult(BaseModel):
    ok: bool = True
    card: Optional[OfferCard] = None
    error: Optional[str] = None


class SearchResult(BaseModel):
    title: str
    url: str
    store: Store
    price: Optional[str] = None
    installments: Optional[str] = None
    product_id: Optional[str] = None
    image_url: Optional[str] = None
    price_source: Optional[str] = None
