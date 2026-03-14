from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.metadata.base import MetadataResult
from app.metadata.openlibrary import OpenLibraryProvider
from app.models import Author, Book, BookAuthor


class MetadataService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.providers = []
        if settings.openlibrary_enabled:
            self.providers.append(OpenLibraryProvider())

    async def enrich_book(self, book: Book) -> bool:
        """Try to fill in missing metadata from providers. Returns True if updated."""
        result = None

        for provider in self.providers:
            if book.isbn_13 or book.isbn_10:
                isbn = book.isbn_13 or book.isbn_10
                result = await provider.lookup_isbn(isbn)
            if not result and book.title:
                results = await provider.search(book.title)
                result = results[0] if results else None
            if result:
                break

        if not result:
            return False

        self._apply_metadata(book, result)
        await self._ensure_authors(book, result.authors)
        await self.db.commit()
        return True

    def _apply_metadata(self, book: Book, meta: MetadataResult) -> None:
        if not book.title and meta.title:
            book.title = meta.title
        if not book.subtitle and meta.subtitle:
            book.subtitle = meta.subtitle
        if not book.description and meta.description:
            book.description = meta.description
        if not book.cover_url and meta.cover_url:
            book.cover_url = meta.cover_url
        if not book.publish_year and meta.publish_year:
            book.publish_year = meta.publish_year
        if not book.page_count and meta.page_count:
            book.page_count = meta.page_count
        if not book.language and meta.language:
            book.language = meta.language
        if not book.isbn_10 and meta.isbn_10:
            book.isbn_10 = meta.isbn_10
        if not book.isbn_13 and meta.isbn_13:
            book.isbn_13 = meta.isbn_13
        if meta.source:
            book.metadata_source = meta.source

    async def _ensure_authors(self, book: Book, author_names: list[str]) -> None:
        from sqlalchemy import select

        for name in author_names:
            stmt = select(Author).where(Author.name == name)
            result = await self.db.execute(stmt)
            author = result.scalar_one_or_none()
            if not author:
                author = Author(name=name)
                self.db.add(author)
                await self.db.flush()

            existing = await self.db.execute(
                select(BookAuthor).where(
                    BookAuthor.book_id == book.id, BookAuthor.author_id == author.id
                )
            )
            if not existing.scalar_one_or_none():
                self.db.add(BookAuthor(book_id=book.id, author_id=author.id, role="author"))
