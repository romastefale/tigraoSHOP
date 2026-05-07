from __future__ import annotations

from aiogram.enums import ParseMode
from aiogram.types import LinkPreviewOptions, Message

from app.bot.keyboards import search_result_keyboard, store_choice_keyboard
from app.bot.render import STORE_LABELS, render_search_result_html
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
    "amazon": Store.AMAZON,
    "shopee": Store.SHOPEE,
    "ali": Store.ALIEXPRESS,
    "aliexpress": Store.ALIEXPRESS,
    "magalu": Store.MAGALU,
    "magazine": Store.MAGALU,
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
    return text, None


async def send_store_choice(message: Message, query: str, service: OfferService | None = None, timeout: float = 1.2) -> None:
    cleaned = main_product_name(query, max_chars=60)
    text = (
        f"Escolha onde pesquisar:\n\n"
        f"<b>{cleaned}</b>\n\n"
        "Você também pode usar:\n"
        "<code>/s mercado livre fone bluetooth</code>\n"
        "<code>/s amazon carregador usb-c</code>\n"
        "<code>/s shopee drone</code>\n"
        "<code>/s ali teclado</code>\n"
        "<code>/s magalu notebook</code>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=store_choice_keyboard(cleaned), link_preview_options=NO_PREVIEW)


async def send_search_results(
    message: Message,
    service: OfferService | None,
    query: str,
    store: Store | None = None,
    timeout: float = 1.2,
) -> None:
    if service is None:
        return
    stores = [store] if store else None
    results = await service.search(query, limit=5, timeout=timeout, stores=stores, include_cache=True)
    if not results:
        await message.answer("Não encontrei ofertas para essa busca.", link_preview_options=NO_PREVIEW)
        return

    store_label = STORE_LABELS.get(store, store.value) if store else "todas as lojas"
    await message.answer(
        f"Ofertas encontradas em <b>{store_label}</b> para:\n<b>{main_product_name(query, max_chars=70)}</b>",
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
