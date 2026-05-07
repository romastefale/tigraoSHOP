from app.core.titles import main_product_name


def test_main_product_name_removes_store_suffix() -> None:
    assert main_product_name("iPhone 17 Pro Max 2tb - Prateado - Distribuidor Autorizado") == "iPhone 17 Pro Max 2tb"


def test_main_product_name_truncates_long_description() -> None:
    title = "Celular Samsung Galaxy S26 5g, 256gb, 12gb Ram, Galaxy Ai, Câmera Tripla De 50+12+10, Tela De 6.3 Preto"
    assert main_product_name(title) == "Celular Samsung Galaxy S26 5g"
