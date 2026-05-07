from app.core.models import Store
from app.core.parser import parse_offer_input


def test_parse_mercado_livre_id() -> None:
    product = parse_offer_input("MLB1234567890")
    assert product.store == Store.MERCADOLIVRE
    assert product.product_id == "MLB1234567890"
    assert product.source == "id"


def test_parse_amazon_asin() -> None:
    product = parse_offer_input("B0ABCDEFGH")
    assert product.store == Store.AMAZON
    assert product.product_id == "B0ABCDEFGH"


def test_parse_shopee_url() -> None:
    product = parse_offer_input("https://shopee.com.br/produto-i.123456.987654321")
    assert product.store == Store.SHOPEE
    assert product.product_id == "123456.987654321"


def test_parse_aliexpress_url() -> None:
    product = parse_offer_input("https://www.aliexpress.com/item/1005001234567890.html")
    assert product.store == Store.ALIEXPRESS
    assert product.product_id == "1005001234567890"


def test_parse_search() -> None:
    product = parse_offer_input("air fryer 5l", force_search=True)
    assert product.source == "search"
    assert product.query == "air fryer 5l"
