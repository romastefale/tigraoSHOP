from __future__ import annotations

from html import escape

from app.core.models import OfferCard, SearchResult, Store
from app.core.titles import main_product_name

STORE_LABELS = {
    Store.SHOPEE: "Shopee",
    Store.MERCADOLIVRE: "Mercado Livre",
    Store.AMAZON: "Amazon",
    Store.ALIEXPRESS: "AliExpress",
    Store.MAGALU: "Magalu",
    Store.SHEIN: "SHEIN",
    Store.UNKNOWN: "Loja",
}


def render_offer_html(card: OfferCard) -> str:
    title = escape(main_product_name(card.title, max_chars=90))
    url = escape(card.offer_url, quote=True)
    lines = [f'🛍 <a href="{url}">{title}</a>', ""]
    if card.price:
        price_line = f"💰 <b>{escape(card.price)}</b> à vista"
        if card.old_price and card.old_price != card.price:
            price_line += f" <s>{escape(card.old_price)}</s>"
        lines.append(price_line)
    else:
        lines.append("💰 <b>Preço disponível abrindo a loja</b>")
    if card.installments:
        lines.append(f"💳 {escape(card.installments)}")
    if card.shipping:
        lines.append(f"🚚 {escape(card.shipping)}")
    if card.rating:
        lines.append(f"⭐ {escape(card.rating)}")
    if card.note:
        lines.append("")
        lines.append(escape(card.note))
    return "\n".join(lines)


def render_search_result(title: str, price: str | None, store: Store) -> str:
    parts = [STORE_LABELS.get(store, store.value), main_product_name(title, max_chars=70)]
    if price:
        parts.append(f"{price} à vista")
    else:
        parts.append("preço na loja")
    return " · ".join(parts)


def render_search_result_html(result: SearchResult | OfferCard, position: int | None = None) -> str:
    if isinstance(result, OfferCard):
        title = main_product_name(result.title, max_chars=90)
        url = result.offer_url
        price = result.price
        installments = result.installments
        store = result.store
    else:
        title = main_product_name(result.title, max_chars=90)
        url = result.url
        price = result.price
        installments = result.installments
        store = result.store

    prefix = f"{position}. " if position else ""
    lines = [f'{prefix}<a href="{escape(url, quote=True)}">{escape(title)}</a>']
    lines.append(f"Loja: <b>{escape(STORE_LABELS.get(store, store.value))}</b>")
    if price:
        lines.append(f"Preço: <b>{escape(price)}</b> à vista")
    else:
        lines.append("Preço: disponível abrindo a loja")
    if installments:
        lines.append(f"Parcelas: {escape(installments)}")
    return "\n".join(lines)
