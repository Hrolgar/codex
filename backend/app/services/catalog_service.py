"""Catalog service for managing monitored authors and their bibliographies via OpenLibrary."""

import asyncio
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Author, Book
from app.metadata.openlibrary import get_cover_url
from app.services.duplicate_service import check_duplicate
from app.services.entity_service import (
    get_or_create_author,
    get_or_create_series,
    link_book_author,
    link_book_series,
)
from app.services.metadata_service import MetadataService
from app.services.settings_service import get_setting

logger = logging.getLogger(__name__)

# Map common 2-letter language codes to OpenLibrary 3-letter codes
_LANG_CODE_MAP: dict[str, str] = {
    "en": "eng", "no": "nor", "de": "ger", "fr": "fre", "es": "spa",
    "it": "ita", "pt": "por", "nl": "dut", "sv": "swe", "da": "dan",
    "fi": "fin", "ru": "rus", "pl": "pol", "ja": "jpn", "zh": "chi",
    "ko": "kor", "ar": "ara", "he": "heb", "hi": "hin", "cs": "cze",
}


def _parse_language_codes(raw: str | None) -> set[str] | None:
    """Parse the general.languages setting into a set of OL 3-letter codes.

    Returns None if no filtering should be applied.
    """
    if not raw or not raw.strip():
        return None
    codes: set[str] = set()
    for part in raw.split(","):
        part = part.strip().lower()
        if not part:
            continue
        # Map 2-letter to 3-letter, or keep as-is if already 3-letter / unknown
        codes.add(_LANG_CODE_MAP.get(part, part))
    return codes if codes else None


def _work_matches_language(entry: dict, editions: list[dict], allowed: set[str]) -> bool:
    """Check if a work or any of its editions match the allowed languages."""
    # Check work-level language field
    work_langs = entry.get("language", [])
    if isinstance(work_langs, list):
        for lang in work_langs:
            code = lang.split("/")[-1] if isinstance(lang, str) else ""
            if code in allowed:
                return True

    # Check edition languages
    for ed in editions:
        ed_langs = ed.get("languages", [])
        for lang in ed_langs:
            key = lang.get("key", "") if isinstance(lang, dict) else str(lang)
            code = key.split("/")[-1]
            if code in allowed:
                return True

    # If no language info at all, include the work (don't filter unknowns)
    if not work_langs and not any(ed.get("languages") for ed in editions):
        return True

    return False

OL_BASE = "https://openlibrary.org"
OL_COVERS = "https://covers.openlibrary.org"
RATE_LIMIT_DELAY = 0.5


async def _ol_get(client: httpx.AsyncClient, path: str, params: dict | None = None) -> dict | None:
    """Make a rate-limited GET request to OpenLibrary."""
    await asyncio.sleep(RATE_LIMIT_DELAY)
    try:
        resp = await client.get(f"{OL_BASE}{path}", params=params)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError:
        logger.warning("OpenLibrary request failed: %s", path)
        return None


def _extract_bio(data: dict) -> str | None:
    """Extract bio text from author data (can be string or dict with 'value' key)."""
    bio = data.get("bio")
    if isinstance(bio, dict):
        return bio.get("value")
    return bio


def _author_photo_url(ol_key: str) -> str:
    """Build OpenLibrary author photo URL."""
    # OL author IDs like OL23919A — photo endpoint uses the numeric ID
    return f"{OL_COVERS}/a/olid/{ol_key}-L.jpg"


def _pick_best_edition(editions: list[dict]) -> dict | None:
    """Pick the best edition from a list — prefer English editions with ISBNs."""
    if not editions:
        return None

    scored = []
    for ed in editions:
        score = 0
        langs = ed.get("languages", [])
        lang_keys = [lang.get("key", "") for lang in langs] if langs else []
        if any("/eng" in k for k in lang_keys) or not langs:
            score += 10
        if ed.get("isbn_13") or ed.get("isbn_10"):
            score += 5
        if ed.get("number_of_pages"):
            score += 1
        scored.append((score, ed))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


async def create_monitored_author(db: AsyncSession, name: str) -> Author:
    """Search OpenLibrary for an author and create/update them as monitored.

    This is the synchronous part — does NOT fetch the full catalog.
    Use refresh_author_catalog() separately for that.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        # Step 1: Search for the author on OpenLibrary
        data = await _ol_get(client, "/search/authors.json", params={"q": name})
        if not data or not data.get("docs"):
            # Fall back to just creating the author without OL data
            author = await get_or_create_author(db, name)
            author.monitored = True
            await db.commit()
            return author

        top = data["docs"][0]
        ol_key = top.get("key", "")  # e.g. 'OL23919A'
        author_name = top.get("name", name)

        # Step 2: Get or create the author using OL canonical name
        author = await get_or_create_author(db, author_name)
        author.monitored = True
        author.openlibrary_key = ol_key

        # Step 3: Fetch author details for bio and photo
        author_data = await _ol_get(client, f"/authors/{ol_key}.json")
        if author_data:
            author.bio = _extract_bio(author_data)
            author.photo_url = _author_photo_url(ol_key)

    await db.commit()
    return author


async def add_author(db: AsyncSession, name: str) -> Author:
    """Search OpenLibrary for an author, add them as monitored, and fetch their catalog.

    Convenience wrapper that calls create_monitored_author + refresh_author_catalog.
    """
    author = await create_monitored_author(db, name)
    await refresh_author_catalog(db, author)
    return author


async def _find_by_openlibrary_key(db: AsyncSession, work_key: str) -> Book | None:
    """Find an existing book by its OpenLibrary work key."""
    if not work_key:
        return None
    result = await db.execute(select(Book).where(Book.openlibrary_key == work_key))
    return result.scalars().first()


async def refresh_author_catalog(db: AsyncSession, author: Author) -> int:
    """Fetch all works for a monitored author from OpenLibrary and create/update books."""
    if not author.openlibrary_key:
        return 0

    author.catalog_status = "fetching"
    await db.commit()

    # Read language filter setting
    lang_raw = await get_setting(db, "general.languages")
    allowed_languages = _parse_language_codes(lang_raw)

    added = 0
    async with httpx.AsyncClient(timeout=15) as client:
        # Fetch all works
        works_data = await _ol_get(
            client,
            f"/authors/{author.openlibrary_key}/works.json",
            params={"limit": 500},
        )
        if not works_data:
            return 0

        entries = works_data.get("entries", [])
        logger.info("Found %d works for author %s", len(entries), author.name)

        for entry in entries:
            try:
                work_key = entry.get("key", "")  # e.g. '/works/OL123W'
                work_title = entry.get("title", "")
                if not work_title:
                    continue

                work_key_short = work_key.replace("/works/", "")

                # Check for existing book by OpenLibrary work key first (cheap DB lookup)
                existing_by_key = await _find_by_openlibrary_key(db, work_key_short)
                if existing_by_key:
                    existing_by_key.monitored = True
                    await link_book_author(db, existing_by_key.id, author.id)
                    continue

                # Fetch editions (needed for language filter and metadata)
                editions_data = await _ol_get(
                    client, f"/works/{work_key_short}/editions.json", params={"limit": 50}
                )
                edition_entries = editions_data.get("entries", []) if editions_data else []

                # Apply language filter BEFORE dedup checks
                if allowed_languages:
                    work_langs = entry.get("language", [])
                    logger.debug(
                        "Language data for %r: work_level=%r, edition_count=%d, edition_langs=%r",
                        work_title,
                        work_langs,
                        len(edition_entries),
                        [ed.get("languages") for ed in edition_entries[:5]],
                    )
                    if not _work_matches_language(entry, edition_entries, allowed_languages):
                        logger.debug("Skipping work %r — language not in allowed list %s", work_title, allowed_languages)
                        continue

                # Check for duplicates by title + author
                is_dup, confidence, matched_id = await check_duplicate(
                    db, work_title, author=author.name
                )

                if is_dup and matched_id:
                    # Mark existing book as monitored and store OL key
                    existing = await db.get(Book, matched_id)
                    if existing:
                        existing.monitored = True
                        if not existing.openlibrary_key:
                            existing.openlibrary_key = work_key_short
                        await link_book_author(db, existing.id, author.id)
                    continue

                isbn_13 = None
                isbn_10 = None
                page_count = None
                publish_year = None
                cover_url = None
                language = None

                if editions_data:
                    edition = _pick_best_edition(editions_data.get("entries", []))
                    if edition:
                        isbn_13_list = edition.get("isbn_13", [])
                        isbn_10_list = edition.get("isbn_10", [])
                        isbn_13 = isbn_13_list[0] if isbn_13_list else None
                        isbn_10 = isbn_10_list[0] if isbn_10_list else None
                        page_count = edition.get("number_of_pages")
                        pub_date = edition.get("publish_date", "")
                        if pub_date and pub_date[:4].isdigit():
                            publish_year = int(pub_date[:4])
                        cover_ids = edition.get("covers", [])
                        if cover_ids:
                            cover_url = f"{OL_COVERS}/b/id/{cover_ids[0]}-L.jpg"
                        langs = edition.get("languages", [])
                        if langs:
                            lang_key = langs[0].get("key", "")
                            language = lang_key.split("/")[-1] if lang_key else None

                # If we got an ISBN, check duplicate again by ISBN
                if isbn_13 or isbn_10:
                    is_dup2, _, matched_id2 = await check_duplicate(
                        db, work_title, isbn=isbn_13 or isbn_10
                    )
                    if is_dup2 and matched_id2:
                        existing = await db.get(Book, matched_id2)
                        if existing:
                            existing.monitored = True
                            if not existing.openlibrary_key:
                                existing.openlibrary_key = work_key_short
                            await link_book_author(db, existing.id, author.id)
                        continue

                # Use ISBN cover if we don't have a cover from editions
                if not cover_url and isbn_13:
                    cover_url = get_cover_url(isbn_13)

                # Extract description
                description = None
                desc_raw = entry.get("description")
                if isinstance(desc_raw, dict):
                    description = desc_raw.get("value")
                elif isinstance(desc_raw, str):
                    description = desc_raw

                # Create the book
                book = Book(
                    title=work_title,
                    description=description,
                    isbn_13=isbn_13,
                    isbn_10=isbn_10,
                    page_count=page_count,
                    publish_year=publish_year,
                    cover_url=cover_url,
                    language=language,
                    openlibrary_key=work_key_short,
                    monitored=True,
                )
                db.add(book)
                await db.flush()

                await link_book_author(db, book.id, author.id)
                added += 1

            except Exception:
                logger.warning("Failed to process work: %s", entry.get("title", "unknown"), exc_info=True)
                continue

    author.catalog_status = "complete"
    await db.commit()

    # Try to enrich newly added books with full metadata
    try:
        meta_svc = MetadataService(db)
        await meta_svc.enrich_unmatched()
    except Exception:
        logger.warning("Metadata enrichment failed for author %s", author.name)

    return added
