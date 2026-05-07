from __future__ import annotations

from app.config import Settings
from app.core.models import Store
from app.services.affiliate import AffiliateService
from app.stores.base import BaseStoreAdapter
from app.stores.generic import MetadataStoreAdapter
from app.stores.mercadolivre import MercadoLivreAdapter


def build_adapters(settings: Settings, affiliate: AffiliateService) -> dict[Store, BaseStoreAdapter]:
    return {
        Store.MERCADOLIVRE: MercadoLivreAdapter(settings, affiliate),
        Store.SHOPEE: MetadataStoreAdapter(settings, affiliate, Store.SHOPEE, "Shopee"),
        Store.AMAZON: MetadataStoreAdapter(settings, affiliate, Store.AMAZON, "Amazon"),
        Store.ALIEXPRESS: MetadataStoreAdapter(settings, affiliate, Store.ALIEXPRESS, "AliExpress"),
        Store.SHEIN: MetadataStoreAdapter(settings, affiliate, Store.SHEIN, "SHEIN"),
    }
