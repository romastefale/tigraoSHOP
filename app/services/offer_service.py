from __future__ import annotations

import asyncio

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

    async def search(self, query: str, limit: int = 5, timeout: float = 1.2) -> list[SearchResult | OfferCard]:
        cached = await self.repo.search_cached(query, limit=limit)
        if cached:
            return cached[:limit]

        async def guarded(adapter: BaseStoreAdapter) -> list[SearchResult]:
            try:
                return await asyncio.wait_for(adapter.search(query, limit=limit), timeout=timeout)
            except Exception:
                return []

        batches = await asyncio.gather(*(guarded(adapter) for adapter in self.adapters.values()))
        results: list[SearchResult] = []
        for batch in batches:
            results.extend(batch)
        return results[:limit]
