from __future__ import annotations

from urllib.parse import quote_plus

from app.config import Settings
from app.core.metadata import fetch_metadata
from app.core.models import OfferCard, ProductInput, SearchResult, Store, StoreResult
from app.core.titles import main_product_name
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
        fallback_title = product_input.query or product_input.raw_text or f"Oferta {self.name}"
        title = main_product_name(meta.title or fallback_title, max_chars=90)
        card = OfferCard(
            store=self.store,
            product_id=product_input.product_id,
            title=title,
            price=meta.price,
            image_url=meta.image_url,
            photo_file_id=product_input.photo_file_id,
            original_url=url,
            offer_url=url,
            source_quality="metadata" if meta.title or meta.price or meta.image_url else "fallback",
        )
        return StoreResult(card=card)

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        url = self._search_url(query)
        if not url:
            return []
        title = main_product_name(query, max_chars=70)
        return [
            SearchResult(
                title=title,
                url=url,
                store=self.store,
                price=None,
                product_id=None,
                image_url=None,
            )
        ]

    def _url_from_id(self, product_id: str | None) -> str | None:
        if not product_id:
            return None
        if self.store == Store.AMAZON:
            return f"https://www.amazon.com.br/dp/{product_id}"
        if self.store == Store.ALIEXPRESS:
            return f"https://www.aliexpress.com/item/{product_id}.html"
        return None

    def _search_url(self, query: str) -> str | None:
        encoded = quote_plus(query.strip())
        if not encoded:
            return None
        if self.store == Store.AMAZON:
            return f"https://www.amazon.com.br/s?k={encoded}"
        if self.store == Store.SHOPEE:
            return f"https://shopee.com.br/search?keyword={encoded}"
        if self.store == Store.ALIEXPRESS:
            return f"https://www.aliexpress.com/wholesale?SearchText={encoded}"
        if self.store == Store.SHEIN:
            return f"https://br.shein.com/pdsearch/{encoded}/"
        return None
