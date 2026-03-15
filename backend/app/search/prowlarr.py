"""Prowlarr search provider for ebooks, audiobooks, and comics."""
from __future__ import annotations

import json
import re

import httpx

from app.schemas.search import SearchResult

# Prowlarr category IDs
CAT_BOOKS = 7000      # Books (parent category)
CAT_EBOOKS = 7020     # Books/EBook
CAT_AUDIOBOOKS = 3030 # Audio/Audiobook
CAT_COMICS = 7030     # Books/Comics

MEDIA_TYPE_CATEGORIES = {
    "ebook": [CAT_BOOKS, CAT_EBOOKS],
    "audiobook": [CAT_BOOKS, CAT_AUDIOBOOKS],
    "comic": [CAT_BOOKS, CAT_COMICS],
}

ALL_CATEGORIES = [CAT_BOOKS, CAT_EBOOKS, CAT_AUDIOBOOKS, CAT_COMICS]


def _clean_search_query(query: str) -> str:
    """Remove trailing language codes that users might add to search queries."""
    words = query.strip().split()
    LANG_CODES = {
        'en', 'eng', 'english',
        'no', 'nor', 'norwegian',
        'sv', 'swe', 'swedish',
        'de', 'ger', 'german',
        'fr', 'fre', 'french',
        'es', 'spa', 'spanish',
        'da', 'dan', 'danish',
    }
    while words and words[-1].lower() in LANG_CODES:
        words.pop()
    return ' '.join(words)


def _parse_title_author(raw: str) -> tuple[str, str | None]:
    """Extract title and author from Prowlarr result title.

    Common formats:
      'Author - Title'
      'Title by Author'
      'Title'
    """
    # Strip bracket content like [ENG / AZW3 EPUB MOBI] or (2015 Edition)
    raw = re.sub(r'\[.*?\]', '', raw).strip()
    raw = re.sub(r'\(.*?\)', '', raw).strip()

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


def _detect_format(title: str) -> str | None:
    """Detect file format from the result title."""
    title_lower = title.lower()
    for fmt in ('epub', 'mobi', 'azw3', 'pdf', 'cbz', 'cbr', 'm4b', 'mp3', 'flac'):
        if fmt in title_lower:
            return fmt
    return None


def _build_params(
    query: str,
    categories: list[int],
    indexer_ids: list[int] | None = None,
) -> list[tuple[str, str | int]]:
    """Build query params as list of tuples for ASP.NET repeated-key binding."""
    params: list[tuple[str, str | int]] = [("Query", query)]
    for cat in categories:
        params.append(("Categories", cat))
    if indexer_ids:
        for idx_id in indexer_ids:
            params.append(("IndexerIds", idx_id))
    return params


async def search_prowlarr(
    base_url: str,
    api_key: str,
    query: str,
    media_type: str | None = None,
    selected_indexers_json: str | None = None,
) -> list[SearchResult]:
    """Search Prowlarr for books/audiobooks and return SearchResult list."""
    categories = MEDIA_TYPE_CATEGORIES.get(media_type, ALL_CATEGORIES)

    query = _clean_search_query(query)

    # Parse selected indexer IDs from settings JSON
    indexer_ids: list[int] | None = None
    if selected_indexers_json:
        try:
            parsed = json.loads(selected_indexers_json)
            if isinstance(parsed, list) and parsed:
                indexer_ids = [int(i) for i in parsed]
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    url = f"{base_url.rstrip('/')}/api/v1/search"
    params = _build_params(query, categories, indexer_ids)
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
        fmt = _detect_format(raw_title)
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
        magnet_url = item.get("magnetUrl") or None
        size = item.get("size") or None
        seeders = item.get("seeders") or None
        leechers = item.get("leechers") or None
        protocol = item.get("protocol") or None
        publish_date = item.get("publishDate") or None
        grabs = item.get("grabs") or None

        results.append(
            SearchResult(
                title=title,
                raw_title=raw_title,
                author=author,
                isbn=isbn,
                source=source,
                download_url=download_url,
                magnet_url=magnet_url,
                format=fmt,
                owned=False,
                match_confidence=0.0,
                indexer=source,
                size=size,
                seeders=seeders,
                leechers=leechers,
                protocol=protocol,
                publish_date=publish_date,
                grabs=grabs,
            )
        )

    return results
