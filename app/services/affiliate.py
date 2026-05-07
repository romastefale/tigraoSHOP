from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.config import Settings
from app.core.models import Store


def _add_query(url: str, params: dict[str, str]) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in params.items():
        if value:
            query[key] = value
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


class AffiliateService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def convert(self, store: Store, url: str) -> str:
        if not url:
            return url
        if store == Store.AMAZON and self.settings.amazon_associate_tag:
            return _add_query(url, {"tag": self.settings.amazon_associate_tag})
        if store == Store.MERCADOLIVRE and self.settings.mercadolivre_affiliate_tag:
            return _add_query(url, {"matt_tool": self.settings.mercadolivre_affiliate_tag})
        if store == Store.ALIEXPRESS and self.settings.aliexpress_tracking_id:
            return _add_query(url, {"aff_fcid": self.settings.aliexpress_tracking_id})
        if store == Store.SHOPEE and self.settings.shopee_tracking_id:
            return _add_query(url, {"uls_trackid": self.settings.shopee_tracking_id})
        if store == Store.SHEIN and self.settings.shein_affiliate_tag:
            return _add_query(url, {"ref": self.settings.shein_affiliate_tag})
        if self.settings.default_affiliate_tag:
            return _add_query(url, {"ref": self.settings.default_affiliate_tag})
        return url
