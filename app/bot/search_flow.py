from __future__ import annotations

from aiogram.enums import ParseMode
from aiogram.types import LinkPreviewOptions, Message

from app.bot.keyboards import search_result_keyboard
from app.bot.render import render_search_result_html
from app.core.models import OfferCard, SearchResult, Store
from app.core.titles import main_product_name
from app.services.offer_service import OfferService

NO_PREVIEW = LinkPreviewOptions(is_disabled=True)

STORE_ALIASES = {
    "ml": Store.MERCADOLIVRE,
    "meli": Store.MERCADOLIVRE,
    "mercadolivre": Store.MERCADOLIVRE,
    "mercado": Store.MERCADOLIVRE,
    "mercado-livre": Store.MERCADOLIVRE,
    "mercado_livre": Store.MERCADOLIVRE,
}


def parse_store_search(payload: str) -> tuple[str, Store | None]:
    text = payload.strip()
    if not text:
        return "", None
    parts = text.split(maxsplit=1)
    if len(parts) == 2:
        store = STORE_ALIASES.get(parts[0].lower().strip("/:"))
        if store:
            return parts[1].strip(), store
    return text, Store.MERCADOLIVRE


async def send_store_choice(message: Message, query: str) -> None:
    cleaned = main_product_name(query, max_chars=60)
    text = (
        "Por enquanto estou funcionando só com Mercado Livre.\n\n"
        f"Vou pesquisar com cuidado:\n<b>{cleaned}</b>\n\n"
        "Também funciona assim:\n"
        "<code>/s mercado livre fone bluetooth</code>\n"
        "<code>/of link-do-mercado-livre</code>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML, link_preview_options=NO_PREVIEW)
    await send_search_results(message, None, query, store=Store.MERCADOLIVRE)


async def send_search_results(
    message: Message,
    service: OfferService | None,
    query: str,
    store: Store | None = None,
    timeout: float = 1.2,
) -> None:
    if service is None:
        return
    store = Store.MERCADOLIVRE
    results = await service.search(query, limit=5, timeout=timeout, stores=[store], include_cache=True)
    if not results:
        await message.answer("Não encontrei preço confirmado no Mercado Livre para essa busca.", link_preview_options=NO_PREVIEW)
        return

    await message.answer(
        f"Ofertas encontradas no <b>Mercado Livre</b> para:\n<b>{main_product_name(query, max_chars=70)}</b>",
        parse_mode=ParseMode.HTML,
        link_preview_options=NO_PREVIEW,
    )

    for index, result in enumerate(results[:5], start=1):
        html = render_search_result_html(result, position=index)
        markup = search_result_keyboard(result)
        image_url = result.image_url if isinstance(result, SearchResult) else result.image_url
        if image_url:
            try:
                await message.answer_photo(image_url, caption=html, parse_mode=ParseMode.HTML, reply_markup=markup)
                continue
            except Exception:
                pass
        await message.answer(html, parse_mode=ParseMode.HTML, reply_markup=markup, link_preview_options=NO_PREVIEW)
