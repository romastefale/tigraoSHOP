from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.search_flow import STORE_ALIASES, send_search_results
from app.services.offer_service import OfferService

router = Router(name="callbacks")


def _query_from_choice_message(text: str | None) -> str:
    value = text or ""
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    for line in lines:
        if line.startswith("Escolha onde pesquisar"):
            continue
        if line.startswith("Você também pode"):
            break
        if line.startswith("/"):
            continue
        clean = re.sub(r"<[^>]+>", "", line).strip()
        if clean:
            return clean
    return ""


@router.callback_query(F.data.startswith("search_store:"))
async def search_store_callback(callback: CallbackQuery, offer_service: OfferService) -> None:
    data = callback.data or ""
    parts = data.split(":", maxsplit=1)
    store_key = parts[1] if len(parts) == 2 else "all"
    store = None if store_key == "all" else STORE_ALIASES.get(store_key)

    if not callback.message:
        await callback.answer("Mensagem indisponível.", show_alert=True)
        return

    query = _query_from_choice_message(callback.message.text or callback.message.caption)
    if not query:
        await callback.answer("Não encontrei o termo da busca. Envie /s produto novamente.", show_alert=True)
        return

    await callback.answer("Buscando ofertas...")
    await send_search_results(callback.message, offer_service, query, store=store)
