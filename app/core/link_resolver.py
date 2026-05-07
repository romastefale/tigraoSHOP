from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

import httpx

from app.core.security import is_safe_url, normalize_user_url


@dataclass(slots=True)
class ResolvedProductLink:
    original_url: str
    final_url: str
    content: str = ""
    redirect_chain: list[str] = field(default_factory=list)
    candidate_urls: list[str] = field(default_factory=list)
    ok: bool = True
    error: str | None = None


_GENERIC_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36 tigraoSHOP",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def _first_meta(content: str, *names: str) -> str | None:
    for name in names:
        patterns = [
            rf'<meta[^>]+property=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(name)}["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{re.escape(name)}["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, flags=re.IGNORECASE | re.DOTALL)
            if match:
                return html.unescape(match.group(1)).strip()
    return None


def _canonical_url(base_url: str, content: str) -> str | None:
    match = re.search(
        r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
        content,
        flags=re.IGNORECASE | re.DOTALL,
    ) or re.search(
        r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']canonical["\']',
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    return urljoin(base_url, html.unescape(match.group(1)).strip())


def _dedupe_urls(urls: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for url in urls:
        normalized = normalize_user_url(url)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


async def resolve_product_link(url: str, timeout: float = 4.0, max_bytes: int = 800_000) -> ResolvedProductLink:
    original = normalize_user_url(url)
    if not is_safe_url(original):
        return ResolvedProductLink(original_url=original, final_url=original, ok=False, error="URL não permitida.")

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers=_GENERIC_HEADERS) as client:
            response = await client.get(original)
            final_url = str(response.url)
            content = response.text[:max_bytes]
            redirect_chain = [str(item.url) for item in response.history] + [final_url]
    except Exception as exc:
        return ResolvedProductLink(original_url=original, final_url=original, ok=False, error=str(exc))

    candidates = _dedupe_urls(
        [
            final_url,
            _canonical_url(final_url, content) or "",
            _first_meta(content, "og:url", "twitter:url") or "",
        ]
    )

    return ResolvedProductLink(
        original_url=original,
        final_url=final_url,
        content=content,
        redirect_chain=redirect_chain,
        candidate_urls=candidates,
    )
