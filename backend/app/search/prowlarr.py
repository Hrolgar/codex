"""Prowlarr search provider for ebooks and audiobooks."""
from __future__ import annotations

import re

import httpx

from app.schemas.search import SearchResult

# Prowlarr category IDs
CAT_EBOOKS = 7020
CAT_AUDIOBOOKS = 7030

MEDIA_TYPE_CATEGORIES = {
    "ebook": [CAT_EBOOKS],
    "audiobook": [CAT_AUDIOBOOKS],
}


def _parse_title_author(raw: str) -> tuple[str, str | None]:
    """Extract title and author from Prowlarr result title.

    Common formats:
      'Author - Title'
      'Title by Author'
      'Title'
    """
    # Try 'Author - Title'
    if " - " in raw:
        parts = raw.split(" - ", 1)
        author = parts[0].strip()
        title = parts[1].strip()
        if author and title:
            return title, author

    # Try 'Title by Author'
    m = re.match(r"^(.+?)\s+by\s+(.+)$", raw, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    return raw.strip(), None


async def search_prowlarr(
    base_url: str,
    api_key: str,
    query: str,
    media_type: str | None = None,
) -> list[SearchResult]:
    """Search Prowlarr for books/audiobooks and return SearchResult list."""
    categories = MEDIA_TYPE_CATEGORIES.get(media_type, [CAT_EBOOKS, CAT_AUDIOBOOKS])

    url = f"{base_url.rstrip('/')}/api/v1/search"
    params = {"query": query, "categories": categories}
    headers = {"X-Api-Key": api_key}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    results: list[SearchResult] = []
    for item in data:
        raw_title = item.get("title", "")
        if not raw_title:
            continue

        title, author = _parse_title_author(raw_title)
        source = item.get("indexer", "prowlarr")

        # Try to extract ISBN from infoUrl or guid if present
        isbn = None
        for field in ("infoUrl", "guid"):
            val = item.get(field, "") or ""
            m = re.search(r"(\d{13}|\d{10})", val)
            if m:
                isbn = m.group(1)
                break

        download_url = item.get("downloadUrl") or None

        results.append(
            SearchResult(
                title=title,
                author=author,
                isbn=isbn,
                source=source,
                download_url=download_url,
                owned=False,
                match_confidence=0.0,
            )
        )

    return results
