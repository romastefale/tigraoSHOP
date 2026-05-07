from __future__ import annotations

import httpx

from app.config import Settings
from app.core.metadata import fetch_metadata
from app.core.models import OfferCard, ProductInput, SearchResult, Store, StoreResult
from app.stores.base import BaseStoreAdapter


class MercadoLivreAdapter(BaseStoreAdapter):
    name = "Mercado Livre"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def get_offer(self, product_input: ProductInput) -> StoreResult:
        if product_input.product_id:
            api_url = f"https://api.mercadolibre.com/items/{product_input.product_id}"
            try:
                async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                    response = await client.get(api_url)
                    if response.status_code == 200:
                        data = response.json()
                        permalink = data.get("permalink") or product_input.url or ""
                        card = OfferCard(
                            store=Store.MERCADOLIVRE,
                            product_id=data.get("id") or product_input.product_id,
                            title=data.get("title") or "Produto Mercado Livre",
                            price=self._format_price(data.get("price")),
                            old_price=self._format_price(data.get("original_price")),
                            image_url=data.get("thumbnail"),
                            photo_file_id=product_input.photo_file_id,
                            original_url=permalink,
                            affiliate_url=permalink,
                            source_quality="api",
                        )
                        return StoreResult(card=card)
            except Exception as exc:
                return StoreResult(ok=False, error=str(exc))

        if product_input.url:
            meta = await fetch_metadata(product_input.url, self.settings.request_timeout_seconds)
            card = OfferCard(
                store=Store.MERCADOLIVRE,
                product_id=product_input.product_id,
                title=meta.title or "Oferta Mercado Livre",
                price=self._format_price(meta.price),
                image_url=meta.image_url,
                photo_file_id=product_input.photo_file_id,
                original_url=product_input.url,
                affiliate_url=product_input.url,
                source_quality="metadata",
            )
            return StoreResult(card=card)

        return StoreResult(ok=False, error="Produto Mercado Livre sem link ou ID.")

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        try:
            async with httpx.AsyncClient(timeout=self.settings.inline_timeout_seconds) as client:
                response = await client.get(
                    "https://api.mercadolibre.com/sites/MLB/search",
                    params={"q": query, "limit": limit},
                )
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []

        results: list[SearchResult] = []
        for item in data.get("results", [])[:limit]:
            url = item.get("permalink") or ""
            if not url:
                continue
            results.append(
                SearchResult(
                    title=item.get("title") or "Produto Mercado Livre",
                    url=url,
                    store=Store.MERCADOLIVRE,
                    price=self._format_price(item.get("price")),
                    product_id=item.get("id"),
                    image_url=item.get("thumbnail"),
                )
            )
        return results

    @staticmethod
    def _format_price(value: object) -> str | None:
        if value in (None, ""):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        formatted = f"R$ {number:,.2f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
