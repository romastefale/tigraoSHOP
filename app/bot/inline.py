from __future__ import annotations

import hashlib

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from app.bot.keyboards import mercadolivre_search_url
from app.bot.render import STORE_LABELS, render_offer_html
from app.config import Settings
from app.core.models import OfferCard, Store
from app.core.parser import parse_offer_input
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


def _description(card: OfferCard) -> str:
    description = f"{card.price} à vista" if card.price else "Oferta Mercado Livre"
    if card.installments:
        description += f" · {card.installments}"
    return description[:120]


def _article_from_card(card: OfferCard) -> InlineQueryResultArticle:
    text = render_offer_html(card)
    store_name = STORE_LABELS.get(card.store, card.store.value)
    clean_title = main_product_name(card.title, max_chars=70)
    return InlineQueryResultArticle(
        id=_stable_id((card.offer_url or "") + card.title),
        title=f"{store_name} · {clean_title}"[:64],
        description=_description(card),
        thumbnail_url=card.image_url,
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode=ParseMode.HTML,
        ),
        reply_markup=_button_url(mercadolivre_search_url(card.title), store_name),
    )


@router.inline_query()
async def inline_query_handler(query: InlineQuery, offer_service: OfferService, settings: Settings) -> None:
    term = (query.query or "").strip()
    if not term:
        await query.answer(results=[], cache_time=5, is_personal=True)
        return

    product_input = parse_offer_input(term, force_search=False)
    if not product_input.url and not product_input.product_id:
        await query.answer(results=[], cache_time=5, is_personal=True)
        return

    result = await offer_service.build_offer(product_input)
    if not result.card or result.card.store != Store.MERCADOLIVRE or not result.card.price:
        await query.answer(results=[], cache_time=5, is_personal=True)
        return

    await query.answer(
        results=[_article_from_card(result.card)],
        cache_time=settings.inline_cache_time,
        is_personal=True,
    )
