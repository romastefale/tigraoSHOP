from __future__ import annotations

from app.config import Settings
from app.core.models import Store
from app.stores.aliexpress_store import AliExpressStoreAdapter
from app.stores.amazon_store import AmazonStoreAdapter
from app.stores.base import BaseStoreAdapter
from app.stores.mercadolivre import MercadoLivreAdapter
from app.stores.shein_store import SheinStoreAdapter
from app.stores.shopee_store import ShopeeStoreAdapter


def build_adapters(settings: Settings) -> dict[Store, BaseStoreAdapter]:
    return {
        Store.MERCADOLIVRE: MercadoLivreAdapter(settings),
        Store.SHOPEE: ShopeeStoreAdapter(settings),
        Store.AMAZON: AmazonStoreAdapter(settings),
        Store.ALIEXPRESS: AliExpressStoreAdapter(settings),
        Store.SHEIN: SheinStoreAdapter(settings),
    }
