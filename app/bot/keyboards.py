from __future__ import annotations

from urllib.parse import quote_plus

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


def mercadolivre_search_url(title: str) -> str:
    query = main_product_name(title, max_chars=80).strip()
    slug = quote_plus(query).replace("+", "-")
    encoded = quote_plus(query).replace("+", "%20")
    return f"https://lista.mercadolivre.com.br/{slug}#D%5BA:{encoded}%5D"


def offer_keyboard(card: OfferCard, offer_id: int | None = None) -> InlineKeyboardMarkup:
    store_name = STORE_LABELS.get(card.store, card.store.value)
    rows: list[list[InlineKeyboardButton]] = [
        [_button(store_name, url=card.offer_url, style="success")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def store_choice_keyboard(query: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
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
                _button("Magalu", callback_data="search_store:magalu", style="primary"),
            ],
        ]
    )


def search_result_keyboard(result: SearchResult | OfferCard) -> InlineKeyboardMarkup:
    store_name = STORE_LABELS.get(result.store, result.store.value)
    url = result.offer_url if isinstance(result, OfferCard) else result.url
    return InlineKeyboardMarkup(
        inline_keyboard=[[_button(store_name, url=url, style="success")]]
    )
