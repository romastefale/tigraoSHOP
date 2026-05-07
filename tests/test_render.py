from app.bot.render import render_offer_html
from app.core.models import OfferCard, Store


def test_render_offer_hyperlinks_main_product_name() -> None:
    card = OfferCard(
        store=Store.MERCADOLIVRE,
        product_id="MLB123",
        title="Produto <teste> - Distribuidor Autorizado",
        price="R$ 99,90",
        old_price="R$ 129,90",
        installments="10x de R$ 9,99 sem juros",
        offer_url="https://mercadolivre.com.br/oferta?x=1",
        original_url="https://mercadolivre.com.br/oferta",
    )
    html = render_offer_html(card)
    assert '<a href="https://mercadolivre.com.br/oferta?x=1">Produto &lt;teste&gt;</a>' in html
    assert "<b>R$ 99,90</b> à vista" in html
    assert "<s>R$ 129,90</s>" in html
    assert "10x de R$ 9,99 sem juros" in html
    assert "Confira condições e disponibilidade abrindo a loja." in html
