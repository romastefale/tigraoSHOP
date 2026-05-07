from app.bot.render import render_offer_html
from app.core.models import OfferCard, Store


def test_render_offer_hyperlinks_product_name() -> None:
    card = OfferCard(
        store=Store.MERCADOLIVRE,
        product_id="MLB123",
        title="Produto <teste>",
        price="R$ 99,90",
        old_price="R$ 129,90",
        affiliate_url="https://mercadolivre.com.br/oferta?x=1",
        original_url="https://mercadolivre.com.br/oferta",
    )
    html = render_offer_html(card)
    assert '<a href="https://mercadolivre.com.br/oferta?x=1">Produto &lt;teste&gt;</a>' in html
    assert "<b>R$ 99,90</b>" in html
    assert "<s>R$ 129,90</s>" in html
