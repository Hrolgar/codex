import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Author, Book, BookAuthor, Library, LibraryItem, Series, SeriesBook
from app.schemas.book import AuthorBrief, BookResponse, LibraryItemBrief, SeriesBrief


class LibraryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Library CRUD ──────────────────────────────────────────────

    async def get_libraries(self) -> list[Library]:
        result = await self.db.execute(select(Library).order_by(Library.name))
        return list(result.scalars().all())

    async def create_library(
        self, name: str, scanner_type: str, config: dict | None = None
    ) -> Library:
        library = Library(name=name, scanner_type=scanner_type, config=config)
        self.db.add(library)
        await self.db.commit()
        await self.db.refresh(library)
        return library

    async def delete_library(self, library_id: uuid.UUID) -> bool:
        library = await self.db.get(Library, library_id)
        if not library:
            return False
        await self.db.delete(library)
        await self.db.commit()
        return True

    # ── Stats ─────────────────────────────────────────────────────

    async def get_library_stats(self) -> dict:
        book_count = await self.db.scalar(select(func.count(Book.id))) or 0
        author_count = await self.db.scalar(select(func.count(Author.id))) or 0
        library_count = await self.db.scalar(select(func.count(Library.id))) or 0
        item_count = await self.db.scalar(select(func.count(LibraryItem.id))) or 0
        return {
            "books": book_count,
            "authors": author_count,
            "libraries": library_count,
            "library_items": item_count,
        }

    # ── Book queries ──────────────────────────────────────────────

    async def get_book(self, book_id: uuid.UUID) -> BookResponse | None:
        book = await self.db.get(Book, book_id)
        if not book:
            return None
        authors = await self._get_book_authors(book_id)
        series = await self._get_book_series(book_id)
        library_items = await self._get_book_library_items(book_id)
        return BookResponse.model_validate(
            book, update={"authors": authors, "series": series, "library_items": library_items}
        )

    async def get_books(
        self,
        query: str | None = None,
        media_type: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[BookResponse], int]:
        stmt = select(Book)
        count_stmt = select(func.count(Book.id))

        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(Book.title.ilike(pattern))
            count_stmt = count_stmt.where(Book.title.ilike(pattern))

        if media_type:
            stmt = stmt.where(Book.media_type == media_type)
            count_stmt = count_stmt.where(Book.media_type == media_type)

        total = await self.db.scalar(count_stmt) or 0

        stmt = stmt.order_by(Book.title).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(stmt)
        books = result.scalars().all()

        items = []
        for book in books:
            authors = await self._get_book_authors(book.id)
            series = await self._get_book_series(book.id)
            items.append(BookResponse.model_validate(book, update={"authors": authors, "series": series}))

        return items, total

    async def _get_book_authors(self, book_id: uuid.UUID) -> list[AuthorBrief]:
        stmt = (
            select(Author.id, Author.name, BookAuthor.role)
            .join(BookAuthor, Author.id == BookAuthor.author_id)
            .where(BookAuthor.book_id == book_id)
        )
        result = await self.db.execute(stmt)
        return [AuthorBrief(id=row.id, name=row.name, role=row.role) for row in result]

    async def _get_book_series(self, book_id: uuid.UUID) -> list[SeriesBrief]:
        stmt = (
            select(Series.id, Series.name, SeriesBook.position)
            .join(SeriesBook, Series.id == SeriesBook.series_id)
            .where(SeriesBook.book_id == book_id)
        )
        result = await self.db.execute(stmt)
        return [SeriesBrief(id=row.id, name=row.name, position=row.position) for row in result]

    async def _get_book_library_items(self, book_id: uuid.UUID) -> list[LibraryItemBrief]:
        stmt = select(LibraryItem).where(LibraryItem.book_id == book_id)
        result = await self.db.execute(stmt)
        return [LibraryItemBrief.model_validate(item) for item in result.scalars().all()]
