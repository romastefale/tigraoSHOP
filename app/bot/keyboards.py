from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.models import OfferCard


def _button(text: str, *, style: str | None = None, copy_text: str | None = None, **kwargs: object) -> InlineKeyboardButton:
    payload = {"text": text, **kwargs}
    if style:
        payload["style"] = style
    if copy_text:
        payload["copy_text"] = {"text": copy_text}
    try:
        return InlineKeyboardButton(**payload)
    except Exception:
        payload.pop("style", None)
        payload.pop("copy_text", None)
        return InlineKeyboardButton(**payload)


def offer_keyboard(card: OfferCard, offer_id: int | None = None, can_remove: bool = False) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [_button("🟢 Ver oferta", url=card.affiliate_url, style="success")],
        [
            _button("🔵 Copiar link", copy_text=card.affiliate_url, style="primary"),
            _button("🔵 Similares", switch_inline_query_current_chat=card.title[:50], style="primary"),
        ],
    ]
    if can_remove and offer_id:
        rows.append([_button("🔴 Remover", callback_data=f"remove:{offer_id}", style="danger")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
