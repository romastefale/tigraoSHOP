from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(default="", alias="BOT_TOKEN")
    bot_username: str = Field(default="tigraoSHOPBot", alias="BOT_USERNAME")
    owner_id: Optional[int] = Field(default=None, alias="OWNER_ID")
    admin_log_chat_id: Optional[int] = Field(default=None, alias="ADMIN_LOG_CHAT_ID")

    webhook_base_url: str = Field(default="", alias="WEBHOOK_BASE_URL")
    webhook_secret: str = Field(default="replace-this-secret", alias="WEBHOOK_SECRET")

    database_url: str = Field(default="./data/offers.db", alias="DATABASE_URL")

    # Official marketplace API credentials. All are optional.
    # The bot uses an official API only when the required credentials are present.
    mercadolivre_access_token: str = Field(default="", alias="MERCADOLIVRE_ACCESS_TOKEN")

    amazon_access_key: str = Field(default="", alias="AMAZON_ACCESS_KEY")
    amazon_secret_key: str = Field(default="", alias="AMAZON_SECRET_KEY")
    amazon_partner_tag: str = Field(default="", alias="AMAZON_PARTNER_TAG")
    amazon_marketplace: str = Field(default="www.amazon.com.br", alias="AMAZON_MARKETPLACE")

    aliexpress_app_key: str = Field(default="", alias="ALIEXPRESS_APP_KEY")
    aliexpress_app_secret: str = Field(default="", alias="ALIEXPRESS_APP_SECRET")
    aliexpress_tracking_id: str = Field(default="", alias="ALIEXPRESS_TRACKING_ID")

    shopee_partner_id: str = Field(default="", alias="SHOPEE_PARTNER_ID")
    shopee_partner_key: str = Field(default="", alias="SHOPEE_PARTNER_KEY")

    shein_app_key: str = Field(default="", alias="SHEIN_APP_KEY")
    shein_app_secret: str = Field(default="", alias="SHEIN_APP_SECRET")

    request_timeout_seconds: float = Field(default=4.0, alias="REQUEST_TIMEOUT_SECONDS")
    inline_timeout_seconds: float = Field(default=1.2, alias="INLINE_TIMEOUT_SECONDS")
    inline_cache_time: int = Field(default=30, alias="INLINE_CACHE_TIME")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def webhook_path(self) -> str:
        return f"/webhook/{self.webhook_secret}"

    @property
    def webhook_url(self) -> str:
        if not self.webhook_base_url:
            return ""
        return self.webhook_base_url.rstrip("/") + self.webhook_path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
