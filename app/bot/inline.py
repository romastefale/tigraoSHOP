from __future__ import annotations

import hashlib
from html import escape

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from app.bot.render import STORE_LABELS, render_offer_html, render_search_result
from app.config import Settings
from app.core.models import OfferCard, SearchResult, Store
from app.core.titles import main_product_name
from app.services.offer_service import OfferService

router = Router(name="inline")


def _stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:32]


def _button_url(url: str, label: str) -> InlineKeyboardMarkup:
    try:
        button = InlineKeyboardButton(text=label, url=url, style="success")
    except Exception:
        button = InlineKeyboardButton(text=label, url=url)
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def _description(price: str | None, installments: str | None) -> str:
    description = f"{price} à vista" if price else "Preço não confirmado"
    if installments:
        description += f" · {installments}"
    return description[:120]


def _article_from_card(card: OfferCard) -> InlineQueryResultArticle:
    text = render_offer_html(card)
    store_name = STORE_LABELS.get(card.store, card.store.value)
    clean_title = main_product_name(card.title, max_chars=70)
    return InlineQueryResultArticle(
        id=_stable_id(card.offer_url + card.title),
        title=f"{store_name} · {clean_title}"[:64],
        description=_description(card.price, card.installments),
        thumbnail_url=card.image_url,
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode=ParseMode.HTML,
        ),
        reply_markup=_button_url(card.offer_url, store_name),
    )


def _article_from_search(result: SearchResult) -> InlineQueryResultArticle:
    store_name = STORE_LABELS.get(result.store, result.store.value)
    clean_title = main_product_name(result.title, max_chars=70)
    summary = render_search_result(result.title, result.price, result.store)
    if result.installments:
        summary += f" · {result.installments}"
    text = f'🛍 <a href="{escape(result.url, quote=True)}">{escape(clean_title)}</a>\n\n'
    text += f"💰 <b>{escape(result.price or 'Preço confirmado indisponível')}</b> à vista\n"
    if result.installments:
        text += f"💳 {escape(result.installments)}\n"
    text += "\nPreço confirmado automaticamente no Mercado Livre. Confira condições e disponibilidade abrindo a loja."
    return InlineQueryResultArticle(
        id=_stable_id(result.url + result.title),
        title=f"{store_name} · {clean_title}"[:64],
        description=summary[:120],
        thumbnail_url=result.image_url,
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode=ParseMode.HTML,
        ),
        reply_markup=_button_url(result.url, store_name),
    )


@router.inline_query()
async def inline_query_handler(query: InlineQuery, offer_service: OfferService, settings: Settings) -> None:
    term = (query.query or "").strip()
    if not term:
        await query.answer(results=[], cache_time=5, is_personal=True)
        return

    raw_results = await offer_service.search(term, limit=8, timeout=settings.inline_timeout_seconds, stores=[Store.MERCADOLIVRE])
    articles = []
    for item in raw_results:
        if isinstance(item, OfferCard):
            if item.store == Store.MERCADOLIVRE and item.price:
                articles.append(_article_from_card(item))
        elif item.store == Store.MERCADOLIVRE and item.price:
            articles.append(_article_from_search(item))

    await query.answer(
        results=articles[:8],
        cache_time=settings.inline_cache_time,
        is_personal=True,
    )
