from __future__ import annotations

import httpx

from app.config import Settings
from app.core.models import OfferCard, ProductInput, SearchResult, Store, StoreResult
from app.stores.base import BaseStoreAdapter
from app.stores.mercadolivre_price import PriceDecision, analyze_mercadolivre_url, normalize_ml_image_url


class MercadoLivreAdapter(BaseStoreAdapter):
    name = "Mercado Livre"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def get_offer(self, product_input: ProductInput) -> StoreResult:
        if product_input.url:
            decision = await analyze_mercadolivre_url(product_input.url, self.settings.request_timeout_seconds)
            return self._card_from_decision(product_input, decision)

        if product_input.product_id:
            return await self._offer_from_item_id(product_input)

        return StoreResult(ok=False, error="Produto Mercado Livre sem link ou ID.")

    async def _offer_from_item_id(self, product_input: ProductInput) -> StoreResult:
        assert product_input.product_id is not None
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.get(f"https://api.mercadolibre.com/items/{product_input.product_id}")
                if response.status_code != 200:
                    return StoreResult(ok=False, error="Não consegui consultar esse item no Mercado Livre.")
                data = response.json()
        except Exception as exc:
            return StoreResult(ok=False, error=f"Falha ao consultar o Mercado Livre: {exc}")

        price = self._format_price(data.get("price"))
        permalink = str(data.get("permalink") or "")
        if not price or not permalink:
            return StoreResult(ok=False, error="Preço não confirmado com segurança no Mercado Livre.")

        card = OfferCard(
            store=Store.MERCADOLIVRE,
            product_id=self._string_or_none(data.get("id")) or product_input.product_id,
            title=self._string_or_none(data.get("title")) or "Produto Mercado Livre",
            price=price,
            old_price=self._format_price(data.get("original_price")),
            installments=None,
            image_url=self._best_image(data),
            photo_file_id=product_input.photo_file_id,
            original_url=product_input.url or permalink,
            offer_url=permalink,
            source_quality="confirmed_api",
            price_source="items_api",
            note="",
        )
        return StoreResult(card=card)

    def _card_from_decision(self, product_input: ProductInput, decision: PriceDecision) -> StoreResult:
        if not decision.ok or not decision.price:
            reason_map = {
                "no_price_evidence": "Preço não encontrado na página do Mercado Livre.",
                "low_confidence_price": "Preço encontrado com baixa confiança. Card bloqueado.",
                "possible_required_variation": "Produto pode exigir variação de cor, tamanho ou voltagem. Preço não confirmado.",
                "not_mercadolivre_url": "Por enquanto só Mercado Livre está habilitado.",
            }
            return StoreResult(ok=False, error=reason_map.get(decision.reason, "Preço não confirmado com segurança no Mercado Livre."))

        card = OfferCard(
            store=Store.MERCADOLIVRE,
            product_id=decision.item_id or product_input.product_id,
            title=decision.title or "Produto Mercado Livre",
            price=decision.price,
            old_price=None,
            installments=None,
            image_url=normalize_ml_image_url(decision.image_url),
            photo_file_id=product_input.photo_file_id,
            original_url=product_input.url or decision.final_url or "",
            offer_url=decision.final_url or product_input.url or "",
            source_quality=f"{decision.source or 'price_evidence'}:{decision.confidence}",
            price_source=decision.source,
            note="",
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
            results.append(SearchResult(title=item.get("title") or "Produto Mercado Livre", url=url, store=Store.MERCADOLIVRE, price=price, installments=self._format_installments(item.get("installments")), product_id=item.get("id"), image_url=self._best_image(item), price_source="mercadolivre_search_api_confirmed"))
        return results

    @staticmethod
    def _best_image(item_data: dict[str, object]) -> str | None:
        pictures = item_data.get("pictures")
        if isinstance(pictures, list):
            for picture in pictures:
                if isinstance(picture, dict):
                    url = picture.get("secure_url") or picture.get("url")
                    if isinstance(url, str) and url.startswith("http"):
                        return normalize_ml_image_url(url)
        for key in ("secure_thumbnail", "thumbnail"):
            url = item_data.get(key)
            if isinstance(url, str) and url.startswith("http"):
                return normalize_ml_image_url(url)
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
