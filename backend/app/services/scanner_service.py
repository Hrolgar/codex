import asyncio
import logging
import uuid

from sqlalchemy import select

from app.database import async_session
from app.models import Book, LibraryItem, RootFolder
from app.models.author import Author, BookAuthor
from app.models.series import Series, SeriesBook
from app.scanners.base import ScannedItem
from app.scanners.filesystem import FilesystemScanner
from app.services.metadata_service import MetadataService

logger = logging.getLogger(__name__)

# Prevent GC of background catalog-fetch tasks
_background_tasks: set = set()


async def run_scan(root_folder_id: uuid.UUID) -> None:
    """Background task: scan a root folder and create/update records."""
    logger.info("Starting scan for root folder %s", root_folder_id)
    async with async_session() as db:
        root_folder = await db.get(RootFolder, root_folder_id)
        if not root_folder:
            logger.warning("Root folder %s not found, skipping scan", root_folder_id)
            return

        logger.info("Scanning path: %s", root_folder.path)
        scanner = FilesystemScanner()
        root_folder.scan_status = "scanning"
        await db.commit()

        items_found = 0
        new_author_ids: set[uuid.UUID] = set()
        try:
            config = {"path": root_folder.path}
            async for scanned in scanner.scan(config):
                items_found += 1
                logger.info("Found: %s by %s (%s)", scanned.title, scanned.author, scanned.file_path)
                new_author = await _process_item(db, root_folder, scanned)
                if new_author is not None:
                    new_author_ids.add(new_author.id)
            root_folder.scan_status = "idle"
            logger.info("Scan complete for %s: %d items found", root_folder.path, items_found)
        except Exception:
            logger.exception("Scan failed for root folder %s", root_folder_id)
            root_folder.scan_status = "error"
        finally:
            from sqlalchemy import func
            root_folder.last_scan_at = func.now()
            await db.commit()

        # Trigger catalog refresh for each newly created author (non-blocking)
        if new_author_ids:
            logger.info("Triggering catalog refresh for %d new author(s)", len(new_author_ids))
            for author_id in new_author_ids:
                task = asyncio.create_task(_fetch_catalog_for_new_author(author_id))
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)


async def _process_item(db, root_folder: RootFolder, item: ScannedItem) -> Author | None:
    """Process a scanned item. Returns the Author if a new one was created, else None."""
    # Check if we already have this file path in this root folder
    existing = await db.execute(
        select(LibraryItem).where(
            LibraryItem.library_id == root_folder.id,
            LibraryItem.file_path == item.file_path,
        )
    )
    if existing.scalar_one_or_none():
        return None

    # Try to match to existing book via duplicate service
    from app.services.duplicate_service import check_duplicate

    book = None
    is_dup, _confidence, matched_id = await check_duplicate(
        db, title=item.title or "", author=item.author, isbn=item.isbn
    )
    if is_dup and matched_id:
        book = await db.get(Book, matched_id)

    if not book:
        book = Book(
            title=item.title or item.file_path.rsplit("/", 1)[-1],
            media_type=item.media_type,
            isbn_10=None,
            isbn_13=None,
            duration_seconds=item.duration_seconds,
            cover_url=item.cover_url,
        )
        if item.isbn:
            from app.core.isbn import normalize
            book.isbn_10, book.isbn_13 = normalize(item.isbn)
        db.add(book)
        await db.flush()

        # Enrich with metadata — called once per book (not per track).
        # Audiobook grouping (Phase 1a) yields one ScannedItem per directory,
        # so each book is only enriched once here.
        try:
            svc = MetadataService(db)
            await svc.enrich_book(book)
        except Exception:
            logger.warning("Metadata enrichment failed for %s", book.title)

    # Link book to author (get-or-create)
    new_author = None
    if item.author:
        author = (await db.execute(
            select(Author).where(Author.name == item.author)
        )).scalar_one_or_none()
        if not author:
            author = Author(name=item.author)
            db.add(author)
            await db.flush()
            new_author = author
        # Link if not already linked
        existing_link = (await db.execute(
            select(BookAuthor).where(
                BookAuthor.book_id == book.id,
                BookAuthor.author_id == author.id,
            )
        )).scalar_one_or_none()
        if not existing_link:
            db.add(BookAuthor(book_id=book.id, author_id=author.id))

    # Link book to series (get-or-create)
    if item.series:
        series = (await db.execute(
            select(Series).where(Series.name == item.series)
        )).scalar_one_or_none()
        if not series:
            series = Series(name=item.series)
            db.add(series)
            await db.flush()
        existing_link = (await db.execute(
            select(SeriesBook).where(
                SeriesBook.series_id == series.id,
                SeriesBook.book_id == book.id,
            )
        )).scalar_one_or_none()
        if not existing_link:
            db.add(SeriesBook(series_id=series.id, book_id=book.id))

    lib_item = LibraryItem(
        library_id=root_folder.id,
        book_id=book.id,
        file_path=item.file_path,
        file_format=item.file_format,
        file_size=item.file_size,
        raw_title=item.title,
        raw_author=item.author,
        raw_isbn=item.isbn,
        matched=True,
    )
    db.add(lib_item)
    await db.commit()
    return new_author


async def _fetch_catalog_for_new_author(author_id: uuid.UUID) -> None:
    """Background task: search the configured provider for an author and fetch their catalog."""
    # Lazy import to avoid circular imports
    from app.services.catalog_service import create_monitored_author, refresh_author_catalog

    try:
        async with async_session() as db:
            author = await db.get(Author, author_id)
            if not author:
                logger.warning("Author %s not found for catalog fetch", author_id)
                return

            logger.info("Auto-cataloging new author: %s", author.name)
            # Search the provider and set the slug/key
            author = await create_monitored_author(db, author.name)
            # Fetch full catalog
            added = await refresh_author_catalog(db, author)
            logger.info("Auto-catalog complete for %s: %d books added", author.name, added)
    except Exception:
        logger.exception("Background catalog fetch failed for author %s", author_id)
