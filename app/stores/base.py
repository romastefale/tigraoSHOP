from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.models import ProductInput, SearchResult, StoreResult


class BaseStoreAdapter(ABC):
    name: str

    @abstractmethod
    async def get_offer(self, product_input: ProductInput) -> StoreResult:
        raise NotImplementedError

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        return []
