import logging
import uuid

from sqlalchemy import select

from app.database import async_session
from app.models import Book, Library, LibraryItem
from app.scanners.audiobookshelf import AudiobookshelfScanner
from app.scanners.base import ScannedItem
from app.scanners.filesystem import FilesystemScanner
from app.services.metadata_service import MetadataService

logger = logging.getLogger(__name__)

SCANNERS = {
    "audiobookshelf": AudiobookshelfScanner,
    "filesystem": FilesystemScanner,
}


async def run_scan(library_id: uuid.UUID) -> None:
    """Background task: scan a library and create/update records."""
    async with async_session() as db:
        library = await db.get(Library, library_id)
        if not library:
            return

        scanner_cls = SCANNERS.get(library.scanner_type)
        if not scanner_cls:
            logger.error("Unknown scanner type: %s", library.scanner_type)
            return

        scanner = scanner_cls()
        library.scan_status = "scanning"
        await db.commit()

        try:
            config = library.config or {}
            async for scanned in scanner.scan(config):
                await _process_item(db, library, scanned)
            library.scan_status = "idle"
        except Exception:
            logger.exception("Scan failed for library %s", library_id)
            library.scan_status = "error"
        finally:
            from sqlalchemy import func
            library.last_scan_at = func.now()
            await db.commit()


async def _process_item(db, library: Library, item: ScannedItem) -> None:
    # Check if we already have this file path in this library
    existing = await db.execute(
        select(LibraryItem).where(
            LibraryItem.library_id == library.id,
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

    lib_item = LibraryItem(
        library_id=library.id,
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
