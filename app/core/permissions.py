from __future__ import annotations

from aiogram import Bot
from aiogram.types import Message

from app.config import Settings


async def is_owner(user_id: int | None, settings: Settings) -> bool:
    return bool(user_id and settings.owner_id and user_id == settings.owner_id)


async def can_delete_in_chat(bot: Bot, message: Message, settings: Settings) -> bool:
    if not message.chat or not message.from_user:
        return False
    if message.chat.type == "private":
        return False
    try:
        member = await bot.get_chat_member(message.chat.id, bot.id)
    except Exception:
        return False
    return bool(getattr(member, "can_delete_messages", False))


async def can_remove_offer(bot: Bot, message: Message | None, user_id: int | None, settings: Settings) -> bool:
    if await is_owner(user_id, settings):
        return True
    if not message or not user_id:
        return False
    try:
        member = await bot.get_chat_member(message.chat.id, user_id)
    except Exception:
        return False
    return member.status in {"administrator", "creator"}
