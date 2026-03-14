from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.database import get_db
from app.models import Book, Author, BookAuthor, Library, LibraryItem

router = APIRouter()


@router.post("/seed")
async def seed(db: AsyncSession = Depends(get_db)):
    # Create demo library
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

    for title, author_name, media_type, year, isbn in books_data:
        book = Book(title=title, media_type=media_type, publish_year=year, isbn_13=isbn)
        db.add(book)
        await db.flush()

        author = Author(name=author_name)
        db.add(author)
        await db.flush()

        db.add(BookAuthor(book_id=book.id, author_id=author.id, role="author"))
        db.add(LibraryItem(
            library_id=lib.id,
            book_id=book.id,
            file_path=f"/books/{title.lower().replace(' ', '-')}.epub",
            file_format="epub" if media_type == "ebook" else "m4b",
            matched=True,
        ))

    await db.commit()
    return {"status": "ok", "books_created": len(books_data)}


@router.post("/clear")
async def clear(db: AsyncSession = Depends(get_db)):
    for model in [LibraryItem, BookAuthor, Book, Author, Library]:
        await db.execute(model.__table__.delete())
    await db.commit()
    return {"status": "cleared"}
