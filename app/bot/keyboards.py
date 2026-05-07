from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.render import STORE_LABELS
from app.core.models import OfferCard


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
    copy_action = f"copy_link:{offer_id}" if offer_id else "copy_link:0"
    rows: list[list[InlineKeyboardButton]] = [
        [_button(store_name, url=card.offer_url, style="success")],
        [
            _button("Copiar link", callback_data=copy_action, style="primary"),
            _button("Similares", switch_inline_query_current_chat=card.title[:50], style="danger"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
