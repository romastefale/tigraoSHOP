from __future__ import annotations

from app.config import Settings
from app.core.models import Store
from app.services.affiliate import AffiliateService
from app.stores.aliexpress_store import AliExpressStoreAdapter
from app.stores.amazon_store import AmazonStoreAdapter
from app.stores.base import BaseStoreAdapter
from app.stores.mercadolivre import MercadoLivreAdapter
from app.stores.shein_store import SheinStoreAdapter
from app.stores.shopee_store import ShopeeStoreAdapter


def build_adapters(settings: Settings, affiliate: AffiliateService) -> dict[Store, BaseStoreAdapter]:
    return {
        Store.MERCADOLIVRE: MercadoLivreAdapter(settings, affiliate),
        Store.SHOPEE: ShopeeStoreAdapter(settings, affiliate),
        Store.AMAZON: AmazonStoreAdapter(settings, affiliate),
        Store.ALIEXPRESS: AliExpressStoreAdapter(settings, affiliate),
        Store.SHEIN: SheinStoreAdapter(settings, affiliate),
    }
