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


async def run_scan(root_folder_id: uuid.UUID) -> None:
    """Background task: scan a root folder and create/update records."""
    async with async_session() as db:
        root_folder = await db.get(RootFolder, root_folder_id)
        if not root_folder:
            return

        scanner = FilesystemScanner()
        root_folder.scan_status = "scanning"
        await db.commit()

        try:
            config = {"path": root_folder.path}
            async for scanned in scanner.scan(config):
                await _process_item(db, root_folder, scanned)
            root_folder.scan_status = "idle"
        except Exception:
            logger.exception("Scan failed for root folder %s", root_folder_id)
            root_folder.scan_status = "error"
        finally:
            from sqlalchemy import func
            root_folder.last_scan_at = func.now()
            await db.commit()


async def _process_item(db, root_folder: RootFolder, item: ScannedItem) -> None:
    # Check if we already have this file path in this root folder
    existing = await db.execute(
        select(LibraryItem).where(
            LibraryItem.library_id == root_folder.id,
            LibraryItem.file_path == item.file_path,
        )
    )
    if existing.scalar_one_or_none():
        return

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

        # Try to enrich with metadata
        try:
            svc = MetadataService(db)
            await svc.enrich_book(book)
        except Exception:
            logger.warning("Metadata enrichment failed for %s", book.title)

    # Link book to author (get-or-create)
    if item.author:
        author = (await db.execute(
            select(Author).where(Author.name == item.author)
        )).scalar_one_or_none()
        if not author:
            author = Author(name=item.author)
            db.add(author)
            await db.flush()
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
