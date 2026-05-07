from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings
from app.core.metadata import fetch_metadata
from app.core.models import OfferCard, ProductInput, Store, StoreResult
from app.core.titles import main_product_name
from app.stores.generic import MetadataStoreAdapter


class ShopeeStoreAdapter(MetadataStoreAdapter):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings, Store.SHOPEE, "Shopee")

    async def get_offer(self, product_input: ProductInput) -> StoreResult:
        if product_input.product_id and "." in product_input.product_id:
            shop_id, item_id = product_input.product_id.split(".", maxsplit=1)
            api_data = await self._fetch_item(shop_id, item_id)
            if api_data:
                card = self._card_from_api(product_input, shop_id, item_id, api_data)
                if card:
                    return StoreResult(card=card)

        # Fallback: metadata/JSON-LD/regex extraction from the page.
        return await super().get_offer(product_input)

    async def _fetch_item(self, shop_id: str, item_id: str) -> dict[str, Any]:
        endpoints = [
            (
                "https://shopee.com.br/api/v4/item/get",
                {"shopid": shop_id, "itemid": item_id},
            ),
            (
                "https://shopee.com.br/api/v4/pdp/get_pc",
                {"shop_id": shop_id, "item_id": item_id},
            ),
        ]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Referer": f"https://shopee.com.br/product/{shop_id}/{item_id}",
        }
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds, headers=headers) as client:
            for endpoint, params in endpoints:
                try:
                    response = await client.get(endpoint, params=params)
                    if response.status_code != 200:
                        continue
                    payload = response.json()
                except Exception:
                    continue
                item = self._extract_item(payload)
                if item:
                    return item
        return {}

    def _extract_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        candidates = [
            payload.get("data"),
            payload.get("item"),
            payload.get("data", {}).get("item") if isinstance(payload.get("data"), dict) else None,
            payload.get("data", {}).get("item_info") if isinstance(payload.get("data"), dict) else None,
        ]
        for candidate in candidates:
            if isinstance(candidate, dict) and (candidate.get("name") or candidate.get("title")):
                return candidate
        return {}

    def _card_from_api(self, product_input: ProductInput, shop_id: str, item_id: str, item: dict[str, Any]) -> OfferCard | None:
        title = main_product_name(str(item.get("name") or item.get("title") or "Oferta Shopee"), max_chars=90)
        url = product_input.url or f"https://shopee.com.br/product/{shop_id}/{item_id}"
        image_url = self._image_url(item)
        return OfferCard(
            store=Store.SHOPEE,
            product_id=f"{shop_id}.{item_id}",
            title=title,
            price=self._format_price(item.get("price") or item.get("price_min") or item.get("price_before_discount")),
            old_price=self._format_price(item.get("price_before_discount")),
            image_url=image_url,
            photo_file_id=product_input.photo_file_id,
            original_url=url,
            offer_url=url,
            source_quality="api",
        )

    def _image_url(self, item: dict[str, Any]) -> str | None:
        image = item.get("image")
        if not image and isinstance(item.get("images"), list) and item["images"]:
            image = item["images"][0]
        if not image:
            return None
        image = str(image)
        if image.startswith("http"):
            return image
        return f"https://down-br.img.susercontent.com/file/{image}"

    @staticmethod
    def _format_price(value: object) -> str | None:
        if value in (None, "", 0):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        # Shopee BR API usually returns prices multiplied by 100000.
        if number > 100_000:
            number = number / 100_000
        formatted = f"R$ {number:,.2f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
