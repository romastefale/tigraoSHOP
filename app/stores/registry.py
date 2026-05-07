from __future__ import annotations

from app.config import Settings
from app.core.models import Store
from app.stores.aliexpress_store import AliExpressStoreAdapter
from app.stores.amazon_store import AmazonStoreAdapter
from app.stores.base import BaseStoreAdapter
from app.stores.generic import MetadataStoreAdapter as GenericAdapter
from app.stores.mercadolivre import MercadoLivreAdapter
from app.stores.shopee_store import ShopeeStoreAdapter


def build_adapters(settings: Settings) -> dict[Store, BaseStoreAdapter]:
    adapters: dict[Store, BaseStoreAdapter] = {
        Store.MERCADOLIVRE: MercadoLivreAdapter(settings),
        Store.AMAZON: AmazonStoreAdapter(settings),
        Store.SHOPEE: ShopeeStoreAdapter(settings),
        Store.ALIEXPRESS: AliExpressStoreAdapter(settings),
    }
    adapters[Store.MAGALU] = GenericAdapter(settings, Store.MAGALU, "Magalu")
    return adapters
