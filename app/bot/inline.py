from __future__ import annotations

import hashlib
from html import escape

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from app.bot.render import STORE_LABELS, render_offer_html, render_search_result
from app.config import Settings
from app.core.models import OfferCard, SearchResult
from app.services.offer_service import OfferService

router = Router(name="inline")


def _stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:32]


def _button_url(url: str) -> InlineKeyboardMarkup:
    try:
        button = InlineKeyboardButton(text="🟢 Ver oferta", url=url, style="success")
    except Exception:
        button = InlineKeyboardButton(text="🟢 Ver oferta", url=url)
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def _article_from_card(card: OfferCard) -> InlineQueryResultArticle:
    text = render_offer_html(card)
    description = f"{card.price or 'Preço no link'} · {STORE_LABELS.get(card.store, card.store.value)}"
    return InlineQueryResultArticle(
        id=_stable_id(card.offer_url + card.title),
        title=card.title[:64],
        description=description[:120],
        thumbnail_url=card.image_url,
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode=ParseMode.HTML,
        ),
        reply_markup=_button_url(card.offer_url),
    )


def _article_from_search(result: SearchResult) -> InlineQueryResultArticle:
    title = result.title[:64]
    summary = render_search_result(result.title, result.price, result.store)
    text = f'🛍 <a href="{escape(result.url, quote=True)}">{escape(result.title[:180])}</a>\n\n'
    if result.price:
        text += f"💰 <b>{escape(result.price)}</b>\n"
    text += f"🏬 {STORE_LABELS.get(result.store, result.store.value)}\n\nOferta encontrada em busca rápida."
    return InlineQueryResultArticle(
        id=_stable_id(result.url + result.title),
        title=title,
        description=summary[:120],
        thumbnail_url=result.image_url,
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode=ParseMode.HTML,
        ),
        reply_markup=_button_url(result.url),
    )


@router.inline_query()
async def inline_query_handler(query: InlineQuery, offer_service: OfferService, settings: Settings) -> None:
    term = (query.query or "").strip()
    if not term:
        await query.answer(results=[], cache_time=5, is_personal=True)
        return

    raw_results = await offer_service.search(term, limit=8, timeout=settings.inline_timeout_seconds)
    articles = []
    for item in raw_results:
        if isinstance(item, OfferCard):
            articles.append(_article_from_card(item))
        else:
            articles.append(_article_from_search(item))

    await query.answer(
        results=articles[:8],
        cache_time=settings.inline_cache_time,
        is_personal=True,
    )
