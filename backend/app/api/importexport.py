"""Import/Export endpoints for Calibre, Audiobookshelf, and CSV/JSON export."""

import csv
import io
import json
import os
import sqlite3
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.author import Author, BookAuthor
from app.models.book import Book
from app.models.library import LibraryItem

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CalibreImportRequest(BaseModel):
    path: str  # path to Calibre library root (contains metadata.db)


class AudiobookshelfImportRequest(BaseModel):
    url: str
    api_key: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_or_create_author(db: AsyncSession, name: str, sort_name: str | None = None) -> Author:
    """Return existing author by name, or create a new one."""
    result = await db.execute(select(Author).where(Author.name == name))
    author = result.scalar_one_or_none()
    if author:
        return author
    author = Author(name=name, sort_name=sort_name or name)
    db.add(author)
    await db.flush()
    return author


async def _book_exists(db: AsyncSession, title: str, author_name: str) -> bool:
    """Check if a book with the given title+author already exists."""
    stmt = (
        select(Book.id)
        .join(BookAuthor, Book.id == BookAuthor.book_id)
        .join(Author, Author.id == BookAuthor.author_id)
        .where(Book.title == title, Author.name == author_name)
    )
    result = await db.execute(stmt)
    return result.first() is not None


# ---------------------------------------------------------------------------
# 7a — Calibre Import
# ---------------------------------------------------------------------------

@router.post("/import/calibre", tags=["import"])
async def import_calibre(body: CalibreImportRequest, db: AsyncSession = Depends(get_db)):
    library_path = Path(body.path).resolve()
    db_path = library_path / "metadata.db"

    # Security: only allow reading from paths under known root folders
    from app.models.root_folder import RootFolder
    result = await db.execute(select(RootFolder))
    root_folders = result.scalars().all()
    allowed_roots = [Path(rf.path).resolve() for rf in root_folders]
    if not any(library_path == root or root in library_path.parents for root in allowed_roots):
        raise HTTPException(
            status_code=403,
            detail="Calibre library path must be under a configured root folder",
        )

    if not db_path.is_file():
        raise HTTPException(status_code=400, detail=f"metadata.db not found at {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT b.id, b.title, b.author_sort, b.isbn, b.pubdate,
                   b.path AS book_path
            FROM books b
            """
        ).fetchall()

        # Build author lookup: book_id -> list of author names
        author_rows = conn.execute(
            """
            SELECT bal.book AS book_id, a.name
            FROM books_authors_link bal
            JOIN authors a ON a.id = bal.author
            """
        ).fetchall()

        authors_by_book: dict[int, list[str]] = {}
        for ar in author_rows:
            authors_by_book.setdefault(ar["book_id"], []).append(ar["name"])

        # Build format lookup: book_id -> list of (format, file_name)
        format_rows = conn.execute(
            """
            SELECT book, format, name FROM data
            """
        ).fetchall()

        formats_by_book: dict[int, list[tuple[str, str]]] = {}
        for fr in format_rows:
            formats_by_book.setdefault(fr["book"], []).append(
                (fr["format"].lower(), fr["name"])
            )
    finally:
        conn.close()

    # Find the root folder that contains this library path
    containing_folder = None
    for rf in root_folders:
        if library_path == Path(rf.path).resolve() or Path(rf.path).resolve() in library_path.parents:
            containing_folder = rf
            break

    imported = 0
    skipped = 0

    for row in rows:
        title = row["title"]
        author_names = authors_by_book.get(row["id"], [])
        primary_author = author_names[0] if author_names else "Unknown"

        if await _book_exists(db, title, primary_author):
            skipped += 1
            continue

        # Parse publish year from pubdate string
        publish_year = None
        pubdate = row["pubdate"]
        if pubdate and len(pubdate) >= 4:
            try:
                publish_year = int(pubdate[:4])
                if publish_year <= 0 or publish_year > 2100:
                    publish_year = None
            except ValueError:
                pass

        # Normalize ISBN
        isbn_raw = row["isbn"] or ""
        isbn_10 = isbn_raw if len(isbn_raw) == 10 else None
        isbn_13 = isbn_raw if len(isbn_raw) == 13 else None

        book = Book(
            title=title,
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            publish_year=publish_year,
            media_type="ebook",
            metadata_source="calibre",
        )
        db.add(book)
        await db.flush()

        # Link authors
        for aname in author_names:
            author = await _get_or_create_author(db, aname, sort_name=row["author_sort"] if aname == primary_author else None)
            db.add(BookAuthor(book_id=book.id, author_id=author.id, role="author"))

        # Create LibraryItems for each format file found on disk
        book_dir = row["book_path"]  # relative path inside library, e.g. "Author Name/Title (123)"
        for fmt, file_name in formats_by_book.get(row["id"], []):
            file_path = str(library_path / book_dir / f"{file_name}.{fmt}")
            if os.path.isfile(file_path):
                db.add(LibraryItem(
                    library_id=containing_folder.id if containing_folder else root_folders[0].id,
                    book_id=book.id,
                    file_path=file_path,
                    file_format=fmt,
                    file_size=os.path.getsize(file_path),
                    matched=True,
                ))

        imported += 1

    await db.commit()
    return {"imported": imported, "skipped": skipped}


# ---------------------------------------------------------------------------
# 7b — Audiobookshelf Import
# ---------------------------------------------------------------------------

@router.post("/import/audiobookshelf", tags=["import"])
async def import_audiobookshelf(body: AudiobookshelfImportRequest, db: AsyncSession = Depends(get_db)):
    from urllib.parse import urlparse
    parsed = urlparse(body.url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="URL must use http or https")

    headers = {"Authorization": f"Bearer {body.api_key}"}
    base = body.url.rstrip("/")

    async with httpx.AsyncClient(timeout=30) as client:
        # Fetch libraries
        resp = await client.get(f"{base}/api/libraries", headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Audiobookshelf /api/libraries returned {resp.status_code}")
        libraries = resp.json().get("libraries", [])

        imported = 0
        skipped = 0

        for lib in libraries:
            lib_id = lib["id"]
            # Fetch items for this library
            resp = await client.get(f"{base}/api/libraries/{lib_id}/items", headers=headers)
            if resp.status_code != 200:
                continue
            items = resp.json().get("results", [])

            for item in items:
                media = item.get("media", {})
                metadata = media.get("metadata", {})
                title = metadata.get("title")
                if not title:
                    continue

                author_name = metadata.get("authorName", "Unknown")

                if await _book_exists(db, title, author_name):
                    skipped += 1
                    continue

                # Parse publish year
                publish_year = None
                pub = metadata.get("publishedYear")
                if pub:
                    try:
                        publish_year = int(pub)
                    except (ValueError, TypeError):
                        pass

                isbn = metadata.get("isbn") or ""
                duration = None
                if media.get("duration"):
                    try:
                        duration = int(float(media["duration"]))
                    except (ValueError, TypeError):
                        pass

                book = Book(
                    title=title,
                    subtitle=metadata.get("subtitle"),
                    description=metadata.get("description"),
                    isbn_10=isbn if len(isbn) == 10 else None,
                    isbn_13=isbn if len(isbn) == 13 else None,
                    asin=metadata.get("asin"),
                    publish_year=publish_year,
                    media_type="audiobook",
                    duration_seconds=duration,
                    language=metadata.get("language"),
                    metadata_source="audiobookshelf",
                )
                db.add(book)
                await db.flush()

                # Handle authors (may be comma-separated or a list)
                author_names = []
                if metadata.get("authors"):
                    for a in metadata["authors"]:
                        n = a.get("name") if isinstance(a, dict) else str(a)
                        if n:
                            author_names.append(n)
                if not author_names:
                    author_names = [author_name]

                for aname in author_names:
                    author = await _get_or_create_author(db, aname)
                    db.add(BookAuthor(book_id=book.id, author_id=author.id, role="author"))

                # Handle narrators
                narrators = metadata.get("narrators", [])
                for narrator in narrators:
                    n = narrator.get("name") if isinstance(narrator, dict) else str(narrator)
                    if n:
                        narrator_author = await _get_or_create_author(db, n)
                        db.add(BookAuthor(book_id=book.id, author_id=narrator_author.id, role="narrator"))

                imported += 1

    await db.commit()
    return {"imported": imported, "skipped": skipped}


# ---------------------------------------------------------------------------
# 7c — Export
# ---------------------------------------------------------------------------

@router.get("/export/books", tags=["export"])
async def export_books(
    format: str = Query("json", pattern="^(csv|json)$"),
    db: AsyncSession = Depends(get_db),
):
    # Fetch all books with their primary author
    stmt = (
        select(
            Book.title,
            Author.name.label("author"),
            Book.isbn_13,
            Book.isbn_10,
            Book.media_type,
        )
        .outerjoin(BookAuthor, Book.id == BookAuthor.book_id)
        .outerjoin(Author, Author.id == BookAuthor.author_id)
        .order_by(Book.title)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # Collapse multiple authors per book into one row
    books_map: dict[str, dict] = {}
    for row in rows:
        key = row.title
        if key not in books_map:
            books_map[key] = {
                "title": row.title,
                "author": row.author or "",
                "isbn": row.isbn_13 or row.isbn_10 or "",
                "media_type": row.media_type,
            }

    book_list = list(books_map.values())

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["title", "author", "isbn", "media_type"])
        writer.writeheader()
        writer.writerows(book_list)
        csv_bytes = output.getvalue().encode("utf-8")
        return StreamingResponse(
            iter([csv_bytes]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=books.csv"},
        )

    # JSON
    json_bytes = json.dumps(book_list, ensure_ascii=False, indent=2).encode("utf-8")
    return StreamingResponse(
        iter([json_bytes]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=books.json"},
    )
