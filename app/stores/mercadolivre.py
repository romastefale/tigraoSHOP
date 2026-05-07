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
                        listing_data = await self._find_listing_data(client, data.get("id") or product_input.product_id, data.get("title"))
                        card = OfferCard(
                            store=Store.MERCADOLIVRE,
                            product_id=data.get("id") or product_input.product_id,
                            title=data.get("title") or "Produto Mercado Livre",
                            price=self._format_price((listing_data or {}).get("price") or data.get("price")),
                            old_price=self._format_price((listing_data or {}).get("original_price") or data.get("original_price")),
                            installments=self._format_installments((listing_data or {}).get("installments")),
                            image_url=data.get("thumbnail"),
                            photo_file_id=product_input.photo_file_id,
                            original_url=permalink,
                            offer_url=permalink,
                            source_quality="api",
                        )
                        return StoreResult(card=card)
            except Exception as exc:
                return StoreResult(ok=False, error=str(exc))

        if product_input.url:
            meta = await fetch_metadata(product_input.url, self.settings.request_timeout_seconds)
            listing_data: dict[str, object] = {}
            if meta.title:
                try:
                    async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                        listing_data = await self._find_listing_data(client, None, meta.title)
                except Exception:
                    listing_data = {}
            offer_url = str(listing_data.get("permalink") or product_input.url)
            card = OfferCard(
                store=Store.MERCADOLIVRE,
                product_id=product_input.product_id or self._string_or_none(listing_data.get("id")),
                title=self._string_or_none(listing_data.get("title")) or meta.title or "Oferta Mercado Livre",
                price=self._format_price(listing_data.get("price") or meta.price),
                old_price=self._format_price(listing_data.get("original_price")),
                installments=self._format_installments(listing_data.get("installments")),
                image_url=self._string_or_none(listing_data.get("thumbnail")) or meta.image_url,
                photo_file_id=product_input.photo_file_id,
                original_url=product_input.url,
                offer_url=offer_url,
                source_quality="api" if listing_data else "metadata",
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
                    installments=self._format_installments(item.get("installments")),
                    product_id=item.get("id"),
                    image_url=item.get("thumbnail"),
                )
            )
        return results

    async def _find_listing_data(self, client: httpx.AsyncClient, item_id: str | None, title: str | None) -> dict[str, object]:
        if not item_id and not title:
            return {}
        queries = [item_id, title]
        for query in [q for q in queries if q]:
            try:
                response = await client.get(
                    "https://api.mercadolibre.com/sites/MLB/search",
                    params={"q": query, "limit": 20},
                )
                if response.status_code != 200:
                    continue
                data = response.json()
            except Exception:
                continue
            results = data.get("results") or []
            if item_id:
                for item in results:
                    if item.get("id") == item_id:
                        return item
            if results:
                return results[0]
        return {}

    @staticmethod
    def _string_or_none(value: object) -> str | None:
        if value in (None, ""):
            return None
        return str(value)

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

    @classmethod
    def _format_installments(cls, installments: object) -> str | None:
        if not isinstance(installments, dict):
            return None
        quantity = installments.get("quantity")
        amount = cls._format_price(installments.get("amount"))
        if not quantity or not amount:
            return None
        rate = installments.get("rate")
        suffix = " sem juros" if rate in (0, 0.0, "0", "0.0", None) else ""
        return f"{quantity}x de {amount}{suffix}"
