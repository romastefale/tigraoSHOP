from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, Update
from fastapi import FastAPI, HTTPException, Request

from app.bot.router import build_router
from app.config import Settings, get_settings
from app.db.repo import OfferRepository
from app.services.affiliate import AffiliateService
from app.services.offer_service import OfferService
from app.stores.registry import build_adapters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings: Settings = get_settings()
bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML) if settings.bot_token else None
dp = Dispatcher()
repo = OfferRepository(settings.database_url)
affiliate = AffiliateService(settings)
offer_service = OfferService(build_adapters(settings, affiliate), repo)

# Dependencies injected into aiogram handlers.
dp["settings"] = settings
dp["offer_repo"] = repo
dp["offer_service"] = offer_service

if bot:
    dp.include_router(build_router())

app = FastAPI(title="tigraoSHOP", version="0.1.0")


@app.on_event("startup")
async def on_startup() -> None:
    await repo.init()
    if not bot:
        logger.warning("BOT_TOKEN not configured. Healthcheck only mode.")
        return
    await bot.set_my_commands(
        [
            BotCommand(command="of", description="Criar card de oferta por link ou ID"),
            BotCommand(command="s", description="Pesquisar oferta"),
            BotCommand(command="help", description="Como usar"),
        ]
    )
    if settings.webhook_url:
        await bot.set_webhook(settings.webhook_url, drop_pending_updates=True)
        logger.info("Webhook configured: %s", settings.webhook_url)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    if bot:
        await bot.session.close()


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"ok": "true", "service": "tigraoSHOP"}


@app.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request) -> dict[str, bool]:
    if secret != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="invalid secret")
    if not bot:
        raise HTTPException(status_code=503, detail="bot not configured")
    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}
