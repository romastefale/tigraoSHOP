from __future__ import annotations

import re

from aiogram import Bot, F, Router
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import LinkPreviewOptions, Message

from app.bot.keyboards import offer_keyboard
from app.bot.render import render_offer_html
from app.bot.search_flow import parse_store_search, send_search_results, send_store_choice
from app.config import Settings
from app.core.models import ProductInput, SearchResult
from app.core.parser import URL_RE, parse_offer_input
from app.core.permissions import can_delete_in_chat
from app.core.resolver import resolve_url
from app.db.repo import OfferRepository
from app.services.offer_service import OfferService

router = Router(name="commands")
NO_PREVIEW = LinkPreviewOptions(is_disabled=True)

HELP_TEXT = """<b>Como usar o tigraoSHOP</b>

Por enquanto estou funcionando apenas com <b>Mercado Livre</b>.

<b>Enviar oferta pronta</b>
Cole um link do Mercado Livre no privado ou use no grupo:
<code>/of link-do-mercado-livre</code>

Também aceito ID de anúncio e códigos de compartilhamento:
<code>/of MLB1234567890</code>
<code>/of HV0JHT-NJ03</code>
<code>/of https://meli.la/1qjkdLZ</code>

<b>Pesquisar ofertas</b>
No privado ou no grupo:
<code>/s fone bluetooth</code>
<code>/s mercado livre fone bluetooth</code>

Se você usar <code>/s</code> com link, ID ou código do Mercado Livre, eu trato como oferta direta, não como busca.

Só mostro resultados com preço confirmado. Se o preço não for confirmado com segurança, eu não publico o card.

<b>Imagem de destaque</b>
Responda uma foto com:
<code>/of link-do-mercado-livre</code>

A foto respondida será usada como imagem principal do post.

<b>Inline</b>
Digite em qualquer conversa:
<code>@seu_bot produto</code>

O inline também pesquisa apenas Mercado Livre."""

START_TEXT = """<b>tigraoSHOP pronto.</b>

Hoje estou tímido: só Mercado Livre, com foco em preço confirmado.

Você pode começar de três formas:

1. Cole um link do Mercado Livre aqui no privado.
2. Use <code>/of link</code>, <code>/of MLB123...</code> ou <code>/of HV0JHT-NJ03</code>.
3. Pesquise com <code>/s nome do produto</code>.

Se o preço não for confirmado com segurança, eu bloqueio a publicação."""


def _command_payload(message: Message) -> str:
    text = message.text or message.caption or ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def _extract_message_url(message: Message | None) -> str | None:
    if not message:
        return None
    text = message.text or message.caption or ""
    entities = list(message.entities or []) + list(message.caption_entities or [])
    for entity in entities:
        url = getattr(entity, "url", None)
        if url:
            return url
        try:
            extracted = entity.extract_from(text)
        except Exception:
            extracted = None
        if extracted and URL_RE.search(extracted):
            return extracted
    match = URL_RE.search(text)
    return match.group(0) if match else None


def _reply_photo_file_id(message: Message) -> str | None:
    if not message.reply_to_message:
        return None
    reply = message.reply_to_message
    if reply.photo:
        return reply.photo[-1].file_id
    if reply.document and reply.document.mime_type and reply.document.mime_type.startswith("image/"):
        return reply.document.file_id
    return None


def _effective_payload(message: Message, payload: str) -> str:
    if payload:
        return payload
    reply_url = _extract_message_url(message.reply_to_message)
    if reply_url:
        return reply_url
    if message.reply_to_message:
        return message.reply_to_message.text or message.reply_to_message.caption or ""
    return payload


def _strip_bot_mention(text: str, bot_username: str) -> str:
    username = bot_username.lstrip("@").strip()
    if not username:
        return text.strip()
    return re.sub(rf"@{re.escape(username)}\b", "", text, flags=re.IGNORECASE).strip()


async def _resolve_product_input(payload: str, photo_file_id: str | None, force_search: bool, settings: Settings):
    product_input = parse_offer_input(payload, photo_file_id=photo_file_id, force_search=force_search)
    if product_input.url:
        resolved_url = await resolve_url(product_input.url, settings.request_timeout_seconds)
        if resolved_url and resolved_url != product_input.url:
            resolved_input = parse_offer_input(resolved_url, photo_file_id=photo_file_id, force_search=force_search)
            resolved_input.raw_text = product_input.raw_text or resolved_input.raw_text
            resolved_input.query = product_input.query or resolved_input.query
            if resolved_input.product_id or resolved_input.store != product_input.store:
                return resolved_input
            product_input.url = resolved_url
    return product_input


def _input_from_search_result(result: SearchResult, photo_file_id: str | None) -> ProductInput:
    return ProductInput(
        source="search_result",
        store=result.store,
        raw_text=result.title,
        url=result.url,
        product_id=result.product_id,
        query=result.title,
        photo_file_id=photo_file_id,
    )


def _looks_like_direct_offer(payload: str) -> bool:
    product_input = parse_offer_input(payload, force_search=False)
    return bool(product_input.url or product_input.product_id)


async def _send_offer(message: Message, html: str, markup, card) -> None:
    if card.photo_file_id:
        await message.answer_photo(card.photo_file_id, caption=html, parse_mode=ParseMode.HTML, reply_markup=markup)
    elif card.image_url:
        try:
            await message.answer_photo(card.image_url, caption=html, parse_mode=ParseMode.HTML, reply_markup=markup)
        except Exception:
            await message.answer(html, parse_mode=ParseMode.HTML, reply_markup=markup, link_preview_options=NO_PREVIEW)
    else:
        await message.answer(html, parse_mode=ParseMode.HTML, reply_markup=markup, link_preview_options=NO_PREVIEW)


async def _publish_offer(
    message: Message,
    bot: Bot,
    service: OfferService,
    repo: OfferRepository,
    settings: Settings,
    payload: str,
    force_search: bool = False,
) -> None:
    photo_file_id = _reply_photo_file_id(message)
    payload = _effective_payload(message, payload)
    product_input = await _resolve_product_input(payload, photo_file_id, force_search, settings)

    if product_input.source in {"empty", "search"}:
        if not product_input.query and not payload:
            await message.reply("Envie link, ID do Mercado Livre ou termo de busca.", link_preview_options=NO_PREVIEW)
            return
        results = await service.search(product_input.query or payload, limit=5, timeout=settings.inline_timeout_seconds)
        if not results:
            await message.reply("Não encontrei preço confirmado no Mercado Livre para essa busca.", link_preview_options=NO_PREVIEW)
            return
        first = results[0]
        if hasattr(first, "offer_url"):
            card = first
        else:
            product_input = _input_from_search_result(first, photo_file_id)
            result = await service.build_offer(product_input)
            if not result.card:
                await message.reply(result.error or "Encontrei resultado, mas não consegui confirmar o preço.", link_preview_options=NO_PREVIEW)
                return
            card = result.card
    else:
        result = await service.build_offer(product_input)
        if not result.card:
            await message.answer(result.error or "Não consegui montar essa oferta.", link_preview_options=NO_PREVIEW)
            return
        card = result.card

    offer_id = await repo.save_offer(card)
    markup = offer_keyboard(card, offer_id=offer_id)
    html = render_offer_html(card)

    if await can_delete_in_chat(bot, message, settings):
        try:
            await message.delete()
        except Exception:
            pass

    await _send_offer(message, html, markup, card)
    await repo.log_usage(message.from_user.id if message.from_user else None, message.chat.id, "offer", card.store)


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(START_TEXT, parse_mode=ParseMode.HTML, link_preview_options=NO_PREVIEW)


@router.message(Command("help"))
async def help_cmd(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode=ParseMode.HTML, link_preview_options=NO_PREVIEW)


@router.message(Command("of"))
async def offer_cmd(message: Message, bot: Bot, offer_service: OfferService, offer_repo: OfferRepository, settings: Settings) -> None:
    await _publish_offer(message, bot, offer_service, offer_repo, settings, _command_payload(message))


@router.message(Command("s"))
async def search_cmd(message: Message, bot: Bot, offer_service: OfferService, offer_repo: OfferRepository, settings: Settings) -> None:
    payload = _command_payload(message)
    if not payload:
        await message.reply("Use <code>/s nome do produto</code>, <code>/s link</code> ou <code>/s HV0JHT-NJ03</code>.", parse_mode=ParseMode.HTML, link_preview_options=NO_PREVIEW)
        return

    if _looks_like_direct_offer(payload):
        await _publish_offer(message, bot, offer_service, offer_repo, settings, payload, force_search=False)
        return

    query, store = parse_store_search(payload)
    await send_search_results(message, offer_service, query, store=store, timeout=settings.inline_timeout_seconds)


@router.message(F.chat.type != ChatType.PRIVATE, F.text)
async def group_mention_text(message: Message, bot: Bot, offer_service: OfferService, offer_repo: OfferRepository, settings: Settings) -> None:
    text = message.text or ""
    username = settings.bot_username.lstrip("@").lower()
    if not username or f"@{username}" not in text.lower():
        return

    payload = _strip_bot_mention(text, settings.bot_username)
    if not payload:
        await message.reply("Envie um link, ID ou código do Mercado Livre junto com a menção.", link_preview_options=NO_PREVIEW)
        return

    product_input = parse_offer_input(payload, force_search=False)
    if product_input.url or product_input.product_id:
        await _publish_offer(message, bot, offer_service, offer_repo, settings, payload, force_search=False)
        return

    query, store = parse_store_search(payload)
    await send_search_results(message, offer_service, query, store=store, timeout=settings.inline_timeout_seconds)


@router.message(F.chat.type == ChatType.PRIVATE, F.text)
async def private_plain_text(message: Message, bot: Bot, offer_service: OfferService, offer_repo: OfferRepository, settings: Settings) -> None:
    text = message.text or ""
    if text.startswith("/"):
        return
    product_input = parse_offer_input(text, force_search=False)
    if product_input.url or product_input.product_id:
        await _publish_offer(message, bot, offer_service, offer_repo, settings, text, force_search=False)
        return
    await send_store_choice(message, text)
