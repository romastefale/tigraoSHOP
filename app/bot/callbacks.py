from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.db.repo import OfferRepository

router = Router(name="callbacks")


@router.callback_query(F.data.startswith("copy_link:"))
async def copy_link_callback(callback: CallbackQuery, offer_repo: OfferRepository) -> None:
    raw_id = (callback.data or "").split(":", maxsplit=1)[-1]
    try:
        offer_id = int(raw_id)
    except ValueError:
        offer_id = 0

    card = await offer_repo.get_offer(offer_id) if offer_id else None
    if not card:
        await callback.answer("Não consegui localizar o link desta oferta.", show_alert=True)
        return

    url = card.offer_url
    if len(url) <= 180:
        await callback.answer(f"Copie o link:\n{url}", show_alert=True)
        return

    try:
        await callback.bot.send_message(callback.from_user.id, url)
        await callback.answer("Link enviado no seu privado.", show_alert=True)
    except Exception:
        await callback.answer("Link longo. Abra pelo botão da loja e copie pela página.", show_alert=True)
