from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.search_flow import STORE_ALIASES, send_search_results
from app.services.offer_service import OfferService

router = Router(name="callbacks")


@router.callback_query(F.data.startswith("search_store:"))
async def search_store_callback(callback: CallbackQuery, offer_service: OfferService) -> None:
    data = callback.data or ""
    _, store_key, query = data.split(":", maxsplit=2)
    store = None if store_key == "all" else STORE_ALIASES.get(store_key)

    if not callback.message:
        await callback.answer("Mensagem indisponível.", show_alert=True)
        return

    await callback.answer("Buscando ofertas...")
    await send_search_results(callback.message, offer_service, query, store=store)
