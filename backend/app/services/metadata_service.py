import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.metadata.base import MetadataResult
from app.metadata.google_books import GoogleBooksProvider
from app.metadata.hardcover import HardcoverProvider
from app.metadata.openlibrary import OpenLibraryProvider
from app.models import Book
from app.services.entity_service import get_or_create_author, link_book_author
from app.services.settings_service import get_setting

logger = logging.getLogger(__name__)


class MetadataService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._providers_built = False
        self.providers = []

    async def _build_providers(self) -> None:
        if self._providers_built:
            return
        self._providers_built = True

        hardcover_key = await get_setting(self.db, "metadata.hardcover_api_key")
        if hardcover_key:
            self.providers.append(HardcoverProvider(api_key=hardcover_key))

        self.providers.append(OpenLibraryProvider())

        google_key = await get_setting(self.db, "metadata.google_books_api_key")
        self.providers.append(GoogleBooksProvider(api_key=google_key))

    async def enrich_book(self, book: Book) -> bool:
        """Try to fill in missing metadata from providers. Returns True if updated."""
        await self._build_providers()
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
        for name in author_names:
            author = await get_or_create_author(self.db, name)
            await link_book_author(self.db, book.id, author.id, role="author")

    async def enrich_unmatched(self) -> int:
        """Find books without metadata_source and try to enrich them. Returns count of enriched."""
        stmt = select(Book).where(Book.metadata_source.is_(None))
        result = await self.db.execute(stmt)
        books = result.scalars().all()

        enriched = 0
        for book in books:
            try:
                if await self.enrich_book(book):
                    enriched += 1
            except Exception:
                logger.warning("Failed to enrich book %s (%s)", book.id, book.title)
        return enriched
