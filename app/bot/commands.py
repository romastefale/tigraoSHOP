from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.bot.keyboards import offer_keyboard
from app.bot.render import render_offer_html
from app.config import Settings
from app.core.parser import parse_offer_input
from app.core.permissions import can_delete_in_chat
from app.db.repo import OfferRepository
from app.services.offer_service import OfferService

router = Router(name="commands")

HELP_TEXT = """Envie link, ID ou pesquise uma oferta.

Privado:
• cole o link do produto
• envie o ID do produto
• use /s termo de busca

Grupo:
• /of link
• /of ID
• /s termo

Também funciona respondendo uma foto com /of link para usar a imagem como destaque."""


def _command_payload(message: Message) -> str:
    text = message.text or message.caption or ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def _reply_photo_file_id(message: Message) -> str | None:
    if not message.reply_to_message:
        return None
    reply = message.reply_to_message
    if reply.photo:
        return reply.photo[-1].file_id
    if reply.document and reply.document.mime_type and reply.document.mime_type.startswith("image/"):
        return reply.document.file_id
    return None


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
    product_input = parse_offer_input(payload, photo_file_id=photo_file_id, force_search=force_search)

    if product_input.source in {"empty", "search"} and force_search:
        results = await service.search(product_input.query or payload, limit=5, timeout=settings.inline_timeout_seconds)
        if not results:
            await message.reply("Não encontrei oferta para essa busca.")
            return
        first = results[0]
        if hasattr(first, "offer_url"):
            card = first
        else:
            product_input = parse_offer_input(first.url)
            result = await service.build_offer(product_input)
            if not result.card:
                await message.reply("Encontrei resultado, mas não consegui montar o card.")
                return
            card = result.card
    else:
        result = await service.build_offer(product_input)
        if not result.card:
            target = message.reply if message.chat.type == ChatType.PRIVATE else message.answer
            await target(result.error or "Não consegui montar essa oferta.")
            return
        card = result.card

    await repo.save_offer(card)
    markup = offer_keyboard(card)
    html = render_offer_html(card)

    if await can_delete_in_chat(bot, message, settings):
        try:
            await message.delete()
        except Exception:
            pass

    if card.photo_file_id:
        await message.answer_photo(card.photo_file_id, caption=html, parse_mode=ParseMode.HTML, reply_markup=markup)
    elif card.image_url:
        try:
            await message.answer_photo(card.image_url, caption=html, parse_mode=ParseMode.HTML, reply_markup=markup)
        except Exception:
            await message.answer(html, parse_mode=ParseMode.HTML, reply_markup=markup)
    else:
        await message.answer(html, parse_mode=ParseMode.HTML, reply_markup=markup)

    await repo.log_usage(message.from_user.id if message.from_user else None, message.chat.id, "offer", card.store)


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer("tigraoSHOP pronto.\n\n" + HELP_TEXT)


@router.message(Command("help"))
async def help_cmd(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("of"))
async def offer_cmd(message: Message, bot: Bot, offer_service: OfferService, offer_repo: OfferRepository, settings: Settings) -> None:
    await _publish_offer(message, bot, offer_service, offer_repo, settings, _command_payload(message))


@router.message(Command("s"))
async def search_cmd(message: Message, bot: Bot, offer_service: OfferService, offer_repo: OfferRepository, settings: Settings) -> None:
    payload = _command_payload(message)
    if not payload:
        await message.reply("Use /s termo de busca.")
        return
    await _publish_offer(message, bot, offer_service, offer_repo, settings, payload, force_search=True)


@router.message(F.chat.type == ChatType.PRIVATE, F.text)
async def private_plain_text(message: Message, bot: Bot, offer_service: OfferService, offer_repo: OfferRepository, settings: Settings) -> None:
    text = message.text or ""
    if text.startswith("/"):
        return
    await _publish_offer(message, bot, offer_service, offer_repo, settings, text)
