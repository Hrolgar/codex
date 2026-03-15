import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Book, Author, BookAuthor, Library, LibraryItem, Series, SeriesBook
from app.metadata.openlibrary import get_cover_url
from app.services.entity_service import (
    get_or_create_author,
    get_or_create_series,
    link_book_author,
    link_book_series,
)

router = APIRouter()


def _check_dev_mode():
    if os.environ.get("CODEX_DEV_MODE", "").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/seed")
async def seed(db: AsyncSession = Depends(get_db)):
    _check_dev_mode()

    # Create demo library
    result = await db.execute(select(Library).where(Library.name == "Demo Library"))
    lib = result.scalar_one_or_none()
    if not lib:
        lib = Library(name="Demo Library", scanner_type="filesystem", config={"path": "/books"})
        db.add(lib)
        await db.flush()

    books_data = [
        ("The Pragmatic Programmer", "David Thomas", "ebook", 2019, "9780135957059"),
        ("Clean Code", "Robert C. Martin", "ebook", 2008, "9780132350884"),
        ("Designing Data-Intensive Applications", "Martin Kleppmann", "ebook", 2017, "9781449373320"),
        ("Project Hail Mary", "Andy Weir", "audiobook", 2021, "9780593135204"),
        ("Dune", "Frank Herbert", "audiobook", 2020, "9781427277060"),
        ("The Martian", "Andy Weir", "ebook", 2014, "9780553418026"),
        ("Neuromancer", "William Gibson", "ebook", 1984, "9780441569595"),
        ("Snow Crash", "Neal Stephenson", "audiobook", 1992, "9780553380958"),
        ("The Name of the Wind", "Patrick Rothfuss", "audiobook", 2007, "9780756404741"),
        ("Mistborn", "Brandon Sanderson", "ebook", 2006, "9780765311788"),
        ("The Way of Kings", "Brandon Sanderson", "audiobook", 2010, "9780765365279"),
        ("Ready Player One", "Ernest Cline", "audiobook", 2011, "9780307887443"),
    ]

    # Series definitions: (series_name, [(book_title, position)])
    series_data = [
        ("Mistborn", [("Mistborn", 1.0)]),
        ("The Stormlight Archive", [("The Way of Kings", 1.0)]),
    ]

    created = 0
    for title, author_name, media_type, year, isbn in books_data:
        # Skip if book with this ISBN already exists
        existing = await db.execute(select(Book).where(Book.isbn_13 == isbn))
        if existing.scalar_one_or_none():
            continue

        book = Book(title=title, media_type=media_type, publish_year=year, isbn_13=isbn, cover_url=get_cover_url(isbn))
        db.add(book)
        await db.flush()

        author = await get_or_create_author(db, author_name)
        author.monitored = True
        await link_book_author(db, book.id, author.id, role="author")

        db.add(LibraryItem(
            library_id=lib.id,
            book_id=book.id,
            file_path=f"/books/{title.lower().replace(' ', '-')}.epub",
            file_format="epub" if media_type == "ebook" else "m4b",
            matched=True,
        ))
        created += 1

    # Create series and link books
    for series_name, book_positions in series_data:
        series = await get_or_create_series(db, series_name)
        for book_title, position in book_positions:
            book_result = await db.execute(select(Book).where(Book.title == book_title))
            book = book_result.scalar_one_or_none()
            if book:
                await link_book_series(db, book.id, series.id, position=position)

    await db.commit()
    return {"status": "ok", "books_created": created}


@router.post("/clear")
async def clear(db: AsyncSession = Depends(get_db)):
    _check_dev_mode()

    for model in [LibraryItem, SeriesBook, BookAuthor, Book, Series, Author, Library]:
        await db.execute(model.__table__.delete())
    await db.commit()
    return {"status": "cleared"}
