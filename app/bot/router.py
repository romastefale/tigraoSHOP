from __future__ import annotations

from aiogram import Router

from app.bot.commands import router as commands_router
from app.bot.inline import router as inline_router


def build_router() -> Router:
    router = Router(name="tigraoshop")
    router.include_router(commands_router)
    router.include_router(inline_router)
    return router
