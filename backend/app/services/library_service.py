import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.matching import escape_like
from app.models import Author, Book, BookAuthor, Library, LibraryItem, Series, SeriesBook
from app.schemas.book import AuthorBrief, BookListItem, BookResponse, LibraryItemBrief, SeriesBrief


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
        data = {
            "id": book.id,
            "title": book.title,
            "subtitle": book.subtitle,
            "description": book.description,
            "cover_url": book.cover_url,
            "media_type": book.media_type,
            "language": book.language,
            "publish_year": book.publish_year,
            "page_count": book.page_count,
            "duration_seconds": book.duration_seconds,
            "isbn_10": book.isbn_10,
            "isbn_13": book.isbn_13,
            "asin": book.asin,
            "openlibrary_key": book.openlibrary_key,
            "metadata_source": book.metadata_source,
            "created_at": book.created_at,
            "updated_at": book.updated_at,
            "authors": authors,
            "series": series,
            "library_items": library_items,
        }
        return BookResponse.model_validate(data)

    async def get_books(
        self,
        query: str | None = None,
        media_type: str | None = None,
        author_id: uuid.UUID | None = None,
        series_id: uuid.UUID | None = None,
        page: int = 1,
        per_page: int = 24,
    ) -> tuple[list[BookListItem], int]:
        # Build filter conditions
        conditions = []
        if query:
            conditions.append(Book.title.ilike(f"%{escape_like(query)}%"))
        if media_type:
            conditions.append(Book.media_type == media_type)
        if author_id:
            author_book_ids = select(BookAuthor.book_id).where(BookAuthor.author_id == author_id)
            conditions.append(Book.id.in_(author_book_ids))
        if series_id:
            series_book_ids = select(SeriesBook.book_id).where(SeriesBook.series_id == series_id)
            conditions.append(Book.id.in_(series_book_ids))

        # Count query
        count_stmt = select(func.count(Book.id))
        for cond in conditions:
            count_stmt = count_stmt.where(cond)
        total = await self.db.scalar(count_stmt) or 0

        # Main query with author join
        first_author = (
            select(Author.name)
            .join(BookAuthor, Author.id == BookAuthor.author_id)
            .where(BookAuthor.book_id == Book.id)
            .correlate(Book)
            .limit(1)
            .scalar_subquery()
            .label("author")
        )

        # Owned subquery: has any LibraryItem
        owned_subquery = (
            select(func.count(LibraryItem.id))
            .where(LibraryItem.book_id == Book.id)
            .correlate(Book)
            .scalar_subquery()
            .label("owned_count")
        )

        stmt = select(
            Book.id,
            Book.title,
            first_author,
            Book.media_type,
            Book.cover_url,
            Book.isbn_13,
            Book.publish_year,
            Book.monitored,
            owned_subquery,
        )
        for cond in conditions:
            stmt = stmt.where(cond)

        offset = (page - 1) * per_page
        stmt = stmt.order_by(Book.title).offset(offset).limit(per_page)
        result = await self.db.execute(stmt)
        rows = result.all()

        items = [
            BookListItem(
                id=row.id,
                title=row.title,
                author=row.author,
                media_type=row.media_type,
                cover_url=row.cover_url,
                isbn_13=row.isbn_13,
                publish_year=row.publish_year,
                owned=(row.owned_count or 0) > 0,
                monitored=row.monitored,
            )
            for row in rows
        ]

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
