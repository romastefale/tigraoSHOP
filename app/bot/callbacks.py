from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from app.config import Settings
from app.core.permissions import can_remove_offer

router = Router(name="callbacks")


@router.callback_query(F.data.startswith("remove:"))
async def remove_offer_callback(callback: CallbackQuery, bot: Bot, settings: Settings) -> None:
    message = callback.message
    user_id = callback.from_user.id if callback.from_user else None
    allowed = await can_remove_offer(bot, message, user_id, settings)
    if not allowed:
        await callback.answer("Apenas dono ou admin pode remover.", show_alert=True)
        return
    if message:
        try:
            await message.delete()
            await callback.answer("Removido.")
            return
        except Exception:
            pass
    await callback.answer("Não consegui remover essa mensagem.", show_alert=True)
