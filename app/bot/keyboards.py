from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.render import STORE_LABELS
from app.core.models import OfferCard, SearchResult, Store
from app.core.titles import main_product_name


def _button(text: str, *, style: str | None = None, **kwargs: object) -> InlineKeyboardButton:
    payload = {"text": text, **kwargs}
    if style:
        payload["style"] = style
    try:
        return InlineKeyboardButton(**payload)
    except Exception:
        payload.pop("style", None)
        return InlineKeyboardButton(**payload)


def offer_keyboard(card: OfferCard, offer_id: int | None = None) -> InlineKeyboardMarkup:
    store_name = STORE_LABELS.get(card.store, card.store.value)
    search_query = main_product_name(card.title, max_chars=50)
    rows: list[list[InlineKeyboardButton]] = [
        [_button(store_name, url=card.offer_url, style="success")],
        [_button("Similares", switch_inline_query_current_chat=search_query, style="danger")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def store_choice_keyboard(query: str) -> InlineKeyboardMarkup:
    rows = [
        [
            _button("Todas", callback_data="search_store:all", style="primary"),
            _button("Mercado Livre", callback_data="search_store:mercadolivre", style="success"),
        ],
        [
            _button("Amazon", callback_data="search_store:amazon", style="primary"),
            _button("Shopee", callback_data="search_store:shopee", style="primary"),
        ],
        [
            _button("AliExpress", callback_data="search_store:aliexpress", style="primary"),
            _button("SHEIN", callback_data="search_store:shein", style="primary"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def search_result_keyboard(result: SearchResult | OfferCard) -> InlineKeyboardMarkup:
    store_name = STORE_LABELS.get(result.store, result.store.value)
    url = result.offer_url if isinstance(result, OfferCard) else result.url
    return InlineKeyboardMarkup(
        inline_keyboard=[[_button(store_name, url=url, style="success")]]
    )
