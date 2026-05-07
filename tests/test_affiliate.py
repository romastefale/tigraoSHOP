from app.config import Settings
from app.core.models import Store
from app.services.affiliate import AffiliateService


def test_amazon_affiliate_tag_is_added() -> None:
    service = AffiliateService(Settings(AMAZON_ASSOCIATE_TAG="romastefale-20"))
    url = service.convert(Store.AMAZON, "https://www.amazon.com.br/dp/B0ABCDEFGH")
    assert "tag=romastefale-20" in url


def test_url_without_tag_stays_valid() -> None:
    service = AffiliateService(Settings())
    url = "https://www.mercadolivre.com.br/produto"
    assert service.convert(Store.MERCADOLIVRE, url) == url
