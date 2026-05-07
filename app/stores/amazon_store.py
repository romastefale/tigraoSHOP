from __future__ import annotations

from app.config import Settings
from app.core.models import Store
from app.services.affiliate import AffiliateService
from app.stores.generic import MetadataStoreAdapter


class AmazonStoreAdapter(MetadataStoreAdapter):
    def __init__(self, settings: Settings, affiliate: AffiliateService) -> None:
        super().__init__(settings, affiliate, Store.AMAZON, "Amazon")
