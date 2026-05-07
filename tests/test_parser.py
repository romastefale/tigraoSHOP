from app.core.models import Store
from app.core.parser import parse_offer_input
from app.stores.mercadolivre_price import clean_item_id


def test_parse_mercado_livre_id() -> None:
    product = parse_offer_input("MLB1234567890")
    assert product.store == Store.MERCADOLIVRE
    assert product.product_id == "MLB1234567890"
    assert product.source == "id"


def test_parse_mercado_livre_url() -> None:
    product = parse_offer_input("https://produto.mercadolivre.com.br/MLB-1234567890-produto-exemplo")
    assert product.store == Store.MERCADOLIVRE
    assert product.product_id == "MLB1234567890"


def test_parse_mercado_livre_short_link_host() -> None:
    product = parse_offer_input("https://meli.la/abc123")
    assert product.store == Store.MERCADOLIVRE
    assert product.url == "https://meli.la/abc123"


def test_clean_item_id_variants() -> None:
    assert clean_item_id("MLB-1234567890") == "MLB1234567890"
    assert clean_item_id("MLB1234567890") == "MLB1234567890"


def test_non_mercado_livre_url_stays_unknown() -> None:
    product = parse_offer_input("https://shopee.com.br/produto-i.123456.987654321")
    assert product.store == Store.UNKNOWN
    assert product.product_id is None


def test_non_mercado_livre_id_stays_unknown() -> None:
    product = parse_offer_input("B0ABCDEFGH")
    assert product.store == Store.UNKNOWN
    assert product.product_id is None


def test_parse_search() -> None:
    product = parse_offer_input("air fryer 5l", force_search=True)
    assert product.source == "search"
    assert product.query == "air fryer 5l"
