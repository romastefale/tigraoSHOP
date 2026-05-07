from __future__ import annotations

import httpx

from app.core.security import is_safe_url, normalize_user_url


async def resolve_url(url: str, timeout: float = 4.0) -> str:
    normalized = normalize_user_url(url)
    if not is_safe_url(normalized):
        return normalized
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": "tigraoSHOP/1.0"},
        ) as client:
            response = await client.get(normalized)
            return str(response.url)
    except Exception:
        return normalized
