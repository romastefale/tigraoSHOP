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
            try:
                async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                    response = await client.get(f"https://api.mercadolibre.com/items/{product_input.product_id}")
                    if response.status_code != 200:
                        return StoreResult(ok=False, error="Não consegui consultar esse item no Mercado Livre.")
                    data = response.json()
                    listing = await self._find_listing_data(client, data.get("id") or product_input.product_id, data.get("title"))
                    return self._build_confirmed_card(product_input, data, listing)
            except Exception as exc:
                return StoreResult(ok=False, error=f"Falha ao consultar o Mercado Livre: {exc}")

        if product_input.url:
            meta = await fetch_metadata(product_input.url, self.settings.request_timeout_seconds)
            if not meta.title:
                return StoreResult(ok=False, error="Não consegui ler o produto do Mercado Livre com segurança.")
            try:
                async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                    listing = await self._find_listing_data(client, None, meta.title)
            except Exception:
                listing = {}

            listing_price = self._format_price(listing.get("price"))
            confirmed_price = meta.price or listing_price
            if not confirmed_price:
                return StoreResult(ok=False, error="Preço não confirmado com segurança no Mercado Livre.")

            # Em URL de produto, a página pública do próprio Mercado Livre é a fonte
            # mais direta. A busca por título pode retornar item parecido; por isso,
            # quando houver preço confiável nos metadados da página, ele prevalece.
            price_source = meta.price_source or "mercadolivre_search_api_confirmed"
            source_quality = "confirmed_page" if meta.price else "confirmed_api"

            card = OfferCard(
                store=Store.MERCADOLIVRE,
                product_id=self._string_or_none(listing.get("id")) or product_input.product_id,
                title=meta.title or self._string_or_none(listing.get("title")) or "Produto Mercado Livre",
                price=confirmed_price,
                old_price=self._format_price(listing.get("original_price")) if not meta.price else None,
                installments=self._format_installments(listing.get("installments")) if listing_price else None,
                image_url=meta.image_url or self._best_image({}, listing),
                photo_file_id=product_input.photo_file_id,
                original_url=product_input.url,
                offer_url=str(listing.get("permalink") or product_input.url),
                source_quality=source_quality,
                price_source=price_source,
                note="Preço confirmado automaticamente no Mercado Livre. Confira condições e disponibilidade abrindo a loja.",
            )
            return StoreResult(card=card)

        return StoreResult(ok=False, error="Produto Mercado Livre sem link ou ID.")

    def _build_confirmed_card(self, product_input: ProductInput, data: dict[str, object], listing: dict[str, object]) -> StoreResult:
        item_price = self._format_price(data.get("price"))
        listing_price = self._format_price(listing.get("price"))
        if item_price and listing_price and item_price != listing_price:
            return StoreResult(ok=False, error="Preço divergente entre item e listagem. Card bloqueado.")
        confirmed_price = listing_price or item_price
        if not confirmed_price:
            return StoreResult(ok=False, error="Preço não confirmado com segurança no Mercado Livre.")
        permalink = str(data.get("permalink") or listing.get("permalink") or product_input.url or "")
        if not permalink:
            return StoreResult(ok=False, error="Link do produto não confirmado no Mercado Livre.")
        card = OfferCard(
            store=Store.MERCADOLIVRE,
            product_id=self._string_or_none(data.get("id")) or product_input.product_id,
            title=self._string_or_none(data.get("title")) or self._string_or_none(listing.get("title")) or "Produto Mercado Livre",
            price=confirmed_price,
            old_price=self._format_price(listing.get("original_price") or data.get("original_price")),
            installments=self._format_installments(listing.get("installments")),
            image_url=self._best_image(data, listing),
            photo_file_id=product_input.photo_file_id,
            original_url=product_input.url or permalink,
            offer_url=permalink,
            source_quality="confirmed_api",
            price_source="mercadolivre_item_api_confirmed",
            note="Preço confirmado automaticamente no Mercado Livre. Confira condições e disponibilidade abrindo a loja.",
        )
        return StoreResult(card=card)

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        try:
            async with httpx.AsyncClient(timeout=self.settings.inline_timeout_seconds) as client:
                response = await client.get("https://api.mercadolibre.com/sites/MLB/search", params={"q": query, "limit": limit})
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []
        results: list[SearchResult] = []
        for item in data.get("results", [])[:limit]:
            url = item.get("permalink") or ""
            price = self._format_price(item.get("price"))
            if not url or not price:
                continue
            results.append(SearchResult(title=item.get("title") or "Produto Mercado Livre", url=url, store=Store.MERCADOLIVRE, price=price, installments=self._format_installments(item.get("installments")), product_id=item.get("id"), image_url=self._best_image({}, item), price_source="mercadolivre_search_api_confirmed"))
        return results

    async def _find_listing_data(self, client: httpx.AsyncClient, item_id: str | None, title: str | None) -> dict[str, object]:
        if not item_id and not title:
            return {}
        for query in [value for value in (item_id, title) if value]:
            try:
                response = await client.get("https://api.mercadolibre.com/sites/MLB/search", params={"q": query, "limit": 20})
                if response.status_code != 200:
                    continue
                results = response.json().get("results") or []
            except Exception:
                continue
            if item_id:
                for item in results:
                    if item.get("id") == item_id:
                        return item
            if results:
                return results[0]
        return {}

    @staticmethod
    def _best_image(item_data: dict[str, object], listing_data: dict[str, object] | None = None) -> str | None:
        listing_data = listing_data or {}
        for source in (listing_data, item_data):
            pictures = source.get("pictures")
            if isinstance(pictures, list):
                for picture in pictures:
                    if isinstance(picture, dict):
                        url = picture.get("secure_url") or picture.get("url")
                        if isinstance(url, str) and url.startswith("http"):
                            return url
            for key in ("secure_thumbnail", "thumbnail"):
                url = source.get(key)
                if isinstance(url, str) and url.startswith("http"):
                    return url.replace("http://", "https://")
        return None

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
            return None
        if number <= 0:
            return None
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
        suffix = " sem juros" if installments.get("rate") in (0, 0.0, "0", "0.0") else ""
        return f"{quantity}x de {amount}{suffix}"
