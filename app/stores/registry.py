from __future__ import annotations

from app.config import Settings
from app.core.models import Store
from app.stores.base import BaseStoreAdapter
from app.stores.mercadolivre import MercadoLivreAdapter


def build_adapters(settings: Settings) -> dict[Store, BaseStoreAdapter]:
    """Build only the currently supported public extractor.

    The bot is intentionally conservative for now: Mercado Livre links/IDs/search
    are supported, while other stores stay disabled until each expansion has a
    reliable price-confirmation strategy.
    """
    return {
        Store.MERCADOLIVRE: MercadoLivreAdapter(settings),
    }
