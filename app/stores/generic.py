from __future__ import annotations

from app.config import Settings
from app.core.metadata import fetch_metadata
from app.core.models import OfferCard, ProductInput, Store, StoreResult
from app.stores.base import BaseStoreAdapter


class MetadataStoreAdapter(BaseStoreAdapter):
    def __init__(self, settings: Settings, store: Store, display_name: str) -> None:
        self.settings = settings
        self.store = store
        self.name = display_name

    async def get_offer(self, product_input: ProductInput) -> StoreResult:
        url = product_input.url or self._url_from_id(product_input.product_id)
        if not url:
            return StoreResult(ok=False, error=f"{self.name} precisa de link para montar a oferta inicial.")
        meta = await fetch_metadata(url, self.settings.request_timeout_seconds)
        card = OfferCard(
            store=self.store,
            product_id=product_input.product_id,
            title=meta.title or f"Oferta {self.name}",
            price=meta.price,
            image_url=meta.image_url,
            photo_file_id=product_input.photo_file_id,
            original_url=url,
            offer_url=url,
            source_quality="metadata" if meta.title else "fallback",
        )
        return StoreResult(card=card)

    def _url_from_id(self, product_id: str | None) -> str | None:
        if not product_id:
            return None
        if self.store == Store.AMAZON:
            return f"https://www.amazon.com.br/dp/{product_id}"
        if self.store == Store.ALIEXPRESS:
            return f"https://www.aliexpress.com/item/{product_id}.html"
        return None
