from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite

from app.core.models import OfferCard, Store


class OfferRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    @property
    def path(self) -> str:
        if self.database_url.startswith("sqlite+aiosqlite:///"):
            return self.database_url.replace("sqlite+aiosqlite:///", "", 1)
        return self.database_url

    async def init(self) -> None:
        db_path = Path(self.path)
        if db_path.parent and str(db_path.parent) != ".":
            db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS offers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store TEXT NOT NULL,
                    product_id TEXT,
                    title TEXT NOT NULL,
                    price TEXT,
                    old_price TEXT,
                    image_url TEXT,
                    photo_file_id TEXT,
                    original_url TEXT NOT NULL,
                    offer_url TEXT NOT NULL,
                    rating TEXT,
                    shipping TEXT,
                    source_quality TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(store, product_id)
                )
                """
            )
            await self._ensure_column(db, "offers", "offer_url", "TEXT")
            await db.execute("UPDATE offers SET offer_url = original_url WHERE offer_url IS NULL OR offer_url = ''")
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS groups (
                    chat_id INTEGER PRIMARY KEY,
                    clean_mode INTEGER DEFAULT 0,
                    admin_log_chat_id INTEGER,
                    allowed INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    chat_id INTEGER,
                    action TEXT NOT NULL,
                    store TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()

    @staticmethod
    async def _ensure_column(db: aiosqlite.Connection, table: str, column: str, column_type: str) -> None:
        cursor = await db.execute(f"PRAGMA table_info({table})")
        rows = await cursor.fetchall()
        columns = {row[1] for row in rows}
        if column not in columns:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

    async def save_offer(self, card: OfferCard) -> int:
        payload = card.model_dump_json()
        product_key = card.product_id or card.original_url
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO offers
                    (store, product_id, title, price, old_price, image_url, photo_file_id,
                     original_url, offer_url, rating, shipping, source_quality, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(store, product_id) DO UPDATE SET
                    title=excluded.title,
                    price=excluded.price,
                    old_price=excluded.old_price,
                    image_url=excluded.image_url,
                    photo_file_id=excluded.photo_file_id,
                    original_url=excluded.original_url,
                    offer_url=excluded.offer_url,
                    rating=excluded.rating,
                    shipping=excluded.shipping,
                    source_quality=excluded.source_quality,
                    payload=excluded.payload,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    card.store.value,
                    product_key,
                    card.title,
                    card.price,
                    card.old_price,
                    card.image_url,
                    card.photo_file_id,
                    card.original_url,
                    card.offer_url,
                    card.rating,
                    card.shipping,
                    card.source_quality,
                    payload,
                ),
            )
            await db.commit()
            cursor = await db.execute(
                "SELECT id FROM offers WHERE store = ? AND product_id = ?",
                (card.store.value, product_key),
            )
            row = await cursor.fetchone()
            return int(row[0]) if row else 0

    async def get_offer(self, offer_id: int) -> OfferCard | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT payload FROM offers WHERE id = ?", (offer_id,))
            row = await cursor.fetchone()
        if not row:
            return None
        data: dict[str, Any] = json.loads(row[0])
        if "offer_url" not in data and "affiliate_url" in data:
            data["offer_url"] = data.pop("affiliate_url")
        return OfferCard.model_validate(data)

    async def search_cached(self, query: str, limit: int = 5) -> list[OfferCard]:
        like = f"%{query.strip()}%"
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT payload FROM offers WHERE title LIKE ? ORDER BY updated_at DESC LIMIT ?",
                (like, limit),
            )
            rows = await cursor.fetchall()
        cards: list[OfferCard] = []
        for row in rows:
            data: dict[str, Any] = json.loads(row[0])
            if "offer_url" not in data and "affiliate_url" in data:
                data["offer_url"] = data.pop("affiliate_url")
            cards.append(OfferCard.model_validate(data))
        return cards

    async def log_usage(self, user_id: int | None, chat_id: int | None, action: str, store: Store | None = None) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO usage_events (user_id, chat_id, action, store) VALUES (?, ?, ?, ?)",
                (user_id, chat_id, action, store.value if store else None),
            )
            await db.commit()
