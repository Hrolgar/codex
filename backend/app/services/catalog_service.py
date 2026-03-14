"""Catalog service for managing monitored authors and their bibliographies via OpenLibrary."""

import asyncio
import logging

import httpx
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

logger = logging.getLogger(__name__)

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


async def add_author(db: AsyncSession, name: str) -> Author:
    """Search OpenLibrary for an author, add them as monitored, and fetch their catalog."""
    async with httpx.AsyncClient(timeout=15) as client:
        # Step 1: Search for the author
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

        # Step 2: Get or create the author
        author = await get_or_create_author(db, author_name)
        author.monitored = True
        author.openlibrary_key = ol_key

        # Step 3: Fetch author details for bio and photo
        author_data = await _ol_get(client, f"/authors/{ol_key}.json")
        if author_data:
            author.bio = _extract_bio(author_data)
            author.photo_url = _author_photo_url(ol_key)

    await db.commit()

    # Step 4: Fetch catalog (works) — done outside the httpx client context
    await refresh_author_catalog(db, author)
    return author


async def refresh_author_catalog(db: AsyncSession, author: Author) -> int:
    """Fetch all works for a monitored author from OpenLibrary and create/update books."""
    if not author.openlibrary_key:
        return 0

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

                # Extract series info if present from subjects
                series_name = None
                series_pos = None
                subjects = entry.get("subjects", [])
                # OpenLibrary doesn't have structured series data in works,
                # but we can check the work description or subjects

                # Check for duplicates by title + author
                is_dup, confidence, matched_id = await check_duplicate(
                    db, work_title, author=author.name
                )

                if is_dup and matched_id:
                    # Mark existing book as monitored
                    existing = await db.get(Book, matched_id)
                    if existing:
                        existing.monitored = True
                        await link_book_author(db, existing.id, author.id)
                    continue

                # Fetch editions to get ISBNs and other metadata
                work_key_short = work_key.replace("/works/", "")
                editions_data = await _ol_get(
                    client, f"/works/{work_key_short}/editions.json", params={"limit": 50}
                )

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

    await db.commit()

    # Try to enrich newly added books with full metadata
    try:
        meta_svc = MetadataService(db)
        await meta_svc.enrich_unmatched()
    except Exception:
        logger.warning("Metadata enrichment failed for author %s", author.name)

    return added
