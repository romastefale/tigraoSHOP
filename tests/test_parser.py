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


def test_parse_mercado_livre_sec_code() -> None:
    product = parse_offer_input("HV0JHT-VEUF")
    assert product.store == Store.MERCADOLIVRE
    assert product.url == "https://www.mercadolivre.com.br/sec/HV0JHT-VEUF"
    assert product.product_id is None


def test_clean_item_id_variants() -> None:
    assert clean_item_id("MLB-1234567890") == "MLB1234567890"
    assert clean_item_id("MLB1234567890") == "MLB1234567890"


def test_parse_shopee_url() -> None:
    product = parse_offer_input("https://shopee.com.br/produto-i.123456.987654321")
    assert product.store == Store.SHOPEE
    assert product.product_id == "123456.987654321"


def test_parse_shopee_short_link() -> None:
    product = parse_offer_input("https://br.shp.ee/16iSJgnN")
    assert product.store == Store.SHOPEE
    assert product.url == "https://br.shp.ee/16iSJgnN"


def test_parse_amazon_asin_and_short_links() -> None:
    assert parse_offer_input("B0ABCDEFGH").store == Store.AMAZON
    assert parse_offer_input("https://a.co/d/abc123").store == Store.AMAZON
    assert parse_offer_input("https://amzn.to/abc123").store == Store.AMAZON


def test_parse_aliexpress_links() -> None:
    product = parse_offer_input("https://www.aliexpress.com/item/1005001234567890.html")
    assert product.store == Store.ALIEXPRESS
    assert product.product_id == "1005001234567890"
    assert parse_offer_input("https://s.click.aliexpress.com/e/_ABAjz1").store == Store.ALIEXPRESS


def test_parse_magalu_links() -> None:
    assert parse_offer_input("https://www.magazineluiza.com.br/produto/p/abc123/").store == Store.MAGALU
    assert parse_offer_input("https://maga.lu/abc123").store == Store.MAGALU
    assert parse_offer_input("https://magalu.page.link/abc123").store == Store.MAGALU


def test_parse_search() -> None:
    product = parse_offer_input("air fryer 5l", force_search=True)
    assert product.source == "search"
    assert product.query == "air fryer 5l"
