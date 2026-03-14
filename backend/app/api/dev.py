from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Author, Book, BookAuthor, Library, LibraryItem

router = APIRouter()

DEMO_BOOKS = [
    {"title": "The Pragmatic Programmer", "author": "David Thomas", "media_type": "ebook", "isbn_13": "9780135957059", "publish_year": 2019, "page_count": 352},
    {"title": "Clean Code", "author": "Robert C. Martin", "media_type": "ebook", "isbn_13": "9780132350884", "publish_year": 2008, "page_count": 464},
    {"title": "Designing Data-Intensive Applications", "author": "Martin Kleppmann", "media_type": "ebook", "isbn_13": "9781449373320", "publish_year": 2017, "page_count": 616},
    {"title": "Project Hail Mary", "author": "Andy Weir", "media_type": "audiobook", "isbn_13": "9780593135204", "publish_year": 2021, "page_count": 496, "duration_seconds": 58140},
    {"title": "Dune", "author": "Frank Herbert", "media_type": "ebook", "isbn_13": "9780441013593", "publish_year": 1965, "page_count": 688},
    {"title": "The Martian", "author": "Andy Weir", "media_type": "audiobook", "isbn_13": "9780553418026", "publish_year": 2014, "page_count": 369, "duration_seconds": 40680},
    {"title": "Neuromancer", "author": "William Gibson", "media_type": "ebook", "isbn_13": "9780441569595", "publish_year": 1984, "page_count": 271},
    {"title": "Snow Crash", "author": "Neal Stephenson", "media_type": "ebook", "isbn_13": "9780553380958", "publish_year": 1992, "page_count": 480},
    {"title": "Ready Player One", "author": "Ernest Cline", "media_type": "audiobook", "isbn_13": "9780307887443", "publish_year": 2011, "page_count": 374, "duration_seconds": 55800},
    {"title": "The Name of the Wind", "author": "Patrick Rothfuss", "media_type": "ebook", "isbn_13": "9780756404741", "publish_year": 2007, "page_count": 662},
    {"title": "Mistborn", "author": "Brandon Sanderson", "media_type": "ebook", "isbn_13": "9780765350381", "publish_year": 2006, "page_count": 541},
    {"title": "The Way of Kings", "author": "Brandon Sanderson", "media_type": "audiobook", "isbn_13": "9780765365279", "publish_year": 2010, "page_count": 1007, "duration_seconds": 186480},
]


@router.post("/seed")
async def seed_demo_data(db: AsyncSession = Depends(get_db)):
    # Check if demo library already exists
    existing = await db.execute(select(Library).where(Library.name == "Demo Library"))
    if existing.scalar_one_or_none():
        return {"status": "already_seeded", "message": "Demo data already exists"}

    # Create demo library
    library = Library(name="Demo Library", scanner_type="filesystem", config={})
    db.add(library)
    await db.flush()

    # Track authors by name to reuse (e.g. Andy Weir, Brandon Sanderson)
    author_cache: dict[str, Author] = {}
    books_created = 0

    for entry in DEMO_BOOKS:
        author_name = entry["author"]

        # Get or create author
        if author_name not in author_cache:
            author = Author(name=author_name, sort_name=", ".join(reversed(author_name.rsplit(" ", 1))))
            db.add(author)
            await db.flush()
            author_cache[author_name] = author

        author = author_cache[author_name]

        # Create book
        book = Book(
            title=entry["title"],
            media_type=entry["media_type"],
            isbn_13=entry["isbn_13"],
            publish_year=entry["publish_year"],
            page_count=entry["page_count"],
            duration_seconds=entry.get("duration_seconds"),
        )
        db.add(book)
        await db.flush()

        # Link book to author
        book_author = BookAuthor(book_id=book.id, author_id=author.id, role="author")
        db.add(book_author)

        # Link book to library
        lib_item = LibraryItem(
            library_id=library.id,
            book_id=book.id,
            file_path=f"/demo/{entry['title'].lower().replace(' ', '_')}.{'m4b' if entry['media_type'] == 'audiobook' else 'epub'}",
            file_format="m4b" if entry["media_type"] == "audiobook" else "epub",
            file_size=1024 * 1024 * 5,
            raw_title=entry["title"],
            raw_author=author_name,
            matched=True,
        )
        db.add(lib_item)
        books_created += 1

    await db.commit()
    return {"status": "seeded", "books": books_created, "authors": len(author_cache)}


@router.post("/clear")
async def clear_demo_data(db: AsyncSession = Depends(get_db)):
    # Find demo library
    result = await db.execute(select(Library).where(Library.name == "Demo Library"))
    library = result.scalar_one_or_none()
    if not library:
        return {"status": "nothing_to_clear"}

    # Get book IDs linked to this library
    items_result = await db.execute(
        select(LibraryItem.book_id).where(LibraryItem.library_id == library.id)
    )
    book_ids = [row[0] for row in items_result.all() if row[0] is not None]

    # Get author IDs linked to these books
    if book_ids:
        author_result = await db.execute(
            select(BookAuthor.author_id).where(BookAuthor.book_id.in_(book_ids))
        )
        author_ids = [row[0] for row in author_result.all()]

        # Delete book_authors, library_items, books
        await db.execute(delete(BookAuthor).where(BookAuthor.book_id.in_(book_ids)))
        await db.execute(delete(LibraryItem).where(LibraryItem.library_id == library.id))
        await db.execute(delete(Book).where(Book.id.in_(book_ids)))

        # Delete authors only if they have no other books
        if author_ids:
            for aid in author_ids:
                remaining = await db.execute(
                    select(BookAuthor).where(BookAuthor.author_id == aid)
                )
                if not remaining.scalar_one_or_none():
                    await db.execute(delete(Author).where(Author.id == aid))
    else:
        await db.execute(delete(LibraryItem).where(LibraryItem.library_id == library.id))

    # Delete library
    await db.delete(library)
    await db.commit()
    return {"status": "cleared"}
