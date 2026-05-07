from __future__ import annotations

from app.config import Settings
from app.core.models import Store
from app.stores.generic import MetadataStoreAdapter


class ShopeeStoreAdapter(MetadataStoreAdapter):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings, Store.SHOPEE, "Shopee")
