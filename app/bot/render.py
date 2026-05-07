from __future__ import annotations

from html import escape

from app.core.models import OfferCard, Store

STORE_LABELS = {
    Store.SHOPEE: "Shopee",
    Store.MERCADOLIVRE: "Mercado Livre",
    Store.AMAZON: "Amazon",
    Store.ALIEXPRESS: "AliExpress",
    Store.SHEIN: "SHEIN",
    Store.UNKNOWN: "Loja",
}


def render_offer_html(card: OfferCard) -> str:
    title = escape(card.title[:180])
    url = escape(card.offer_url, quote=True)
    lines = [f'🛍 <a href="{url}">{title}</a>', ""]
    if card.price:
        price_line = f"💰 <b>{escape(card.price)}</b>"
        if card.old_price and card.old_price != card.price:
            price_line += f" <s>{escape(card.old_price)}</s>"
        lines.append(price_line)
    else:
        lines.append("💰 <b>Preço no link da oferta</b>")
    lines.append(f"🏬 {STORE_LABELS.get(card.store, card.store.value)}")
    if card.shipping:
        lines.append(f"🚚 {escape(card.shipping)}")
    if card.rating:
        lines.append(f"⭐ {escape(card.rating)}")
    lines.append("")
    lines.append(escape(card.note))
    return "\n".join(lines)


def render_search_result(title: str, price: str | None, store: Store) -> str:
    parts = [title]
    if price:
        parts.append(price)
    parts.append(STORE_LABELS.get(store, store.value))
    return " · ".join(parts)
