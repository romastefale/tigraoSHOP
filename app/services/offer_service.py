from __future__ import annotations

import asyncio
from collections.abc import Iterable

from app.core.models import OfferCard, ProductInput, SearchResult, Store, StoreResult
from app.db.repo import OfferRepository
from app.stores.base import BaseStoreAdapter


class OfferService:
    def __init__(self, adapters: dict[Store, BaseStoreAdapter], repo: OfferRepository) -> None:
        self.adapters = adapters
        self.repo = repo

    async def build_offer(self, product_input: ProductInput) -> StoreResult:
        if product_input.store == Store.UNKNOWN:
            return StoreResult(ok=False, error="Não consegui identificar a loja. Envie link ou ID completo.")
        adapter = self.adapters.get(product_input.store)
        if not adapter:
            return StoreResult(ok=False, error="Loja ainda não configurada.")
        result = await adapter.get_offer(product_input)
        if result.card:
            await self.repo.save_offer(result.card)
        return result

    async def search(
        self,
        query: str,
        limit: int = 5,
        timeout: float = 1.2,
        stores: Iterable[Store] | None = None,
        include_cache: bool = True,
    ) -> list[SearchResult | OfferCard]:
        cleaned = query.strip()
        if not cleaned:
            return []

        selected_stores = set(stores or [])
        if include_cache:
            cached = await self.repo.search_cached(cleaned, limit=limit)
            if selected_stores:
                cached = [card for card in cached if card.store in selected_stores]
            if cached:
                return cached[:limit]

        adapters = self.adapters.items()
        if selected_stores:
            adapters = [(store, adapter) for store, adapter in adapters if store in selected_stores]

        async def guarded(adapter: BaseStoreAdapter) -> list[SearchResult]:
            try:
                return await asyncio.wait_for(adapter.search(cleaned, limit=limit), timeout=timeout)
            except Exception:
                return []

        batches = await asyncio.gather(*(guarded(adapter) for _, adapter in adapters))
        results: list[SearchResult] = []
        for batch in batches:
            results.extend(batch)
        return self._rank_results(results, limit=limit)

    @staticmethod
    def _rank_results(results: list[SearchResult], limit: int) -> list[SearchResult]:
        def score(item: SearchResult) -> tuple[int, int]:
            has_price = 1 if item.price else 0
            has_image = 1 if item.image_url else 0
            return (has_price, has_image)

        deduped: list[SearchResult] = []
        seen: set[str] = set()
        for item in sorted(results, key=score, reverse=True):
            key = item.url or f"{item.store}:{item.title}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
            if len(deduped) >= limit:
                break
        return deduped
