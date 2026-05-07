from __future__ import annotations

import html
import re
from dataclasses import dataclass

import httpx


@dataclass(slots=True)
class PageMetadata:
    title: str | None = None
    image_url: str | None = None
    price: str | None = None


def _find_meta(content: str, *names: str) -> str | None:
    for name in names:
        patterns = [
            rf'<meta[^>]+property=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(name)}["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{re.escape(name)}["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return html.unescape(match.group(1)).strip()
    return None


def _find_title(content: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return html.unescape(title)


async def fetch_metadata(url: str, timeout: float = 4.0) -> PageMetadata:
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 tigraoSHOP"},
        ) as client:
            response = await client.get(url)
            content = response.text[:300_000]
    except Exception:
        return PageMetadata()

    return PageMetadata(
        title=_find_meta(content, "og:title", "twitter:title") or _find_title(content),
        image_url=_find_meta(content, "og:image", "twitter:image"),
        price=_find_meta(content, "product:price:amount", "og:price:amount", "price"),
    )
