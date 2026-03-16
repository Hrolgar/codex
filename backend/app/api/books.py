import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Author, Book, BookAuthor, Download, Edition, LibraryItem, Series, SeriesBook
from app.models.root_folder import RootFolder
from app.schemas import BookListItem, BookListResponse, BookResponse
from app.services.library_service import LibraryService
from app.services.path_template_service import DEFAULT_TEMPLATES, PathContext, render_path
from app.services.settings_service import get_setting

logger = logging.getLogger(__name__)

router = APIRouter()


class ManualMatchRequest(BaseModel):
    file_path: str
    rename_folder: bool = False


@router.get("/unmatched")
async def list_unmatched_items(
    db: AsyncSession = Depends(get_db),
):
    """Return all LibraryItems where matched=False (unmatched files)."""
    stmt = (
        select(LibraryItem)
        .where(LibraryItem.matched.is_(False))
        .order_by(LibraryItem.created_at.desc())
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [
        {
            "id": str(item.id),
            "library_id": str(item.library_id),
            "book_id": str(item.book_id) if item.book_id else None,
            "raw_title": item.raw_title,
            "raw_author": item.raw_author,
            "file_path": item.file_path,
            "file_size": item.file_size,
            "file_format": item.file_format,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in items
    ]


@router.get("", response_model=BookListResponse)
async def list_books(
    search: str | None = Query(None, description="Search query"),
    media_type: str | None = Query(None),
    author_id: uuid.UUID | None = Query(None, description="Filter by author"),
    series_id: uuid.UUID | None = Query(None, description="Filter by series"),
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    svc = LibraryService(db)
    items, total = await svc.get_books(
        query=search, media_type=media_type,
        author_id=author_id, series_id=series_id,
        page=page, per_page=per_page,
    )
    return BookListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    svc = LibraryService(db)
    book = await svc.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


async def _rename_to_template(
    db: AsyncSession, book: Book, library_item: LibraryItem, root_folder: RootFolder,
) -> str | None:
    """Rename/move a file to match the path template. Returns new path or None."""
    old_path = Path(library_item.file_path)
    root_path = Path(root_folder.path).resolve()

    # Build PathContext from book metadata
    author_result = await db.execute(
        select(Author.name)
        .join(BookAuthor, Author.id == BookAuthor.author_id)
        .where(BookAuthor.book_id == book.id)
        .limit(1)
    )
    author_row = author_result.first()
    author_name = author_row[0] if author_row else "Unknown"

    series_result = await db.execute(
        select(Series.name, SeriesBook.position)
        .join(SeriesBook, Series.id == SeriesBook.series_id)
        .where(SeriesBook.book_id == book.id)
        .limit(1)
    )
    series_row = series_result.first()

    ctx = PathContext(
        author=author_name,
        title=book.title,
        series=series_row[0] if series_row else "",
        series_position=str(series_row[1]) if series_row else "",
        year=str(book.publish_year) if book.publish_year else "",
        isbn=book.isbn_13 or book.isbn_10 or "",
        language=book.language or "",
        format=old_path.suffix.lstrip("."),
        original_name=old_path.stem,
    )

    # Get path template for this media type
    media_key_map = {"ebook": "books", "audiobook": "audiobooks", "comic": "comics"}
    key = media_key_map.get(book.media_type, "books")
    if key == "comics":
        template = await get_setting(db, f"downloads.{key}.template")
    else:
        template = await get_setting(db, f"downloads.{key}.path_template")
    if not template:
        template = DEFAULT_TEMPLATES.get(book.media_type, DEFAULT_TEMPLATES["ebook"])

    rendered = render_path(template, ctx)
    if not rendered:
        return None

    # New path: root_folder / rendered_template + original extension
    new_path = root_path / rendered
    # Append the file extension if it's not a directory (single-file book)
    if old_path.is_file():
        new_path = new_path.with_suffix(old_path.suffix)

    # Safety: ensure new path is still within the same root folder
    try:
        new_path.resolve().relative_to(root_path)
    except ValueError:
        logger.warning("Rename blocked: destination %s is outside root folder %s", new_path, root_path)
        return None

    # Don't rename if source and destination are the same
    if old_path.resolve() == new_path.resolve():
        return None

    # Don't rename if destination already exists
    if new_path.exists():
        logger.warning("Rename skipped: destination already exists: %s", new_path)
        return None

    # Perform the rename
    try:
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_path), str(new_path))
        logger.info("Renamed file: %s -> %s", old_path, new_path)

        # Clean up empty parent directories up to root
        old_parent = old_path.parent
        while old_parent != root_path and old_parent != old_parent.parent:
            try:
                old_parent.rmdir()  # Only removes if empty
                logger.info("Removed empty directory: %s", old_parent)
                old_parent = old_parent.parent
            except OSError:
                break

        return str(new_path)
    except OSError as exc:
        logger.error("Failed to rename %s -> %s: %s", old_path, new_path, exc)
        return None


@router.post("/{book_id}/match")
async def manual_match(
    book_id: uuid.UUID,
    body: ManualMatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually match an existing file to a book by creating a LibraryItem link.

    If rename_folder=True, also renames the file to match the configured path template.
    """
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Verify the file actually exists
    file_path = Path(body.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=400, detail="File does not exist")
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Check if this file is already linked to another book
    existing_stmt = select(LibraryItem).where(LibraryItem.file_path == body.file_path)
    existing_result = await db.execute(existing_stmt)
    existing_item = existing_result.scalar_one_or_none()

    if existing_item and existing_item.book_id and existing_item.book_id != book_id:
        raise HTTPException(
            status_code=409,
            detail=f"File is already linked to another book (book_id={existing_item.book_id})",
        )

    # Find the root folder this file belongs to
    rf_stmt = select(RootFolder).order_by(RootFolder.created_at)
    rf_result = await db.execute(rf_stmt)
    root_folders = rf_result.scalars().all()

    root_folder = None
    real_file = str(file_path.resolve())
    for rf in root_folders:
        real_root = str(Path(rf.path).resolve())
        if real_file.startswith(real_root + "/") or real_file == real_root:
            root_folder = rf
            break

    if not root_folder:
        raise HTTPException(
            status_code=400,
            detail="File is not inside any configured root folder",
        )

    renamed_path = None

    if existing_item:
        # Update the existing unmatched LibraryItem to point to this book
        existing_item.book_id = book_id
        existing_item.matched = True

        # Optionally rename the file to match the path template
        if body.rename_folder:
            renamed_path = await _rename_to_template(db, book, existing_item, root_folder)
            if renamed_path:
                existing_item.file_path = renamed_path

        await db.commit()
        return {
            "status": "matched",
            "library_item_id": str(existing_item.id),
            "book_id": str(book_id),
            "manual_match": True,
            "renamed": renamed_path is not None,
            "file_path": existing_item.file_path,
        }

    # No existing LibraryItem — create one
    try:
        file_size = file_path.stat().st_size
    except OSError:
        file_size = None

    item = LibraryItem(
        library_id=root_folder.id,
        book_id=book_id,
        file_path=body.file_path,
        file_format=file_path.suffix.lstrip(".") or None,
        file_size=file_size,
        matched=True,
    )
    db.add(item)

    # Optionally rename the file to match the path template
    if body.rename_folder:
        # Flush to get the item persisted before rename
        await db.flush()
        renamed_path = await _rename_to_template(db, book, item, root_folder)
        if renamed_path:
            item.file_path = renamed_path

    await db.commit()
    await db.refresh(item)

    return {
        "status": "matched",
        "library_item_id": str(item.id),
        "book_id": str(book_id),
        "manual_match": True,
        "renamed": renamed_path is not None,
        "file_path": item.file_path,
    }


@router.put("/{book_id}/monitored")
async def toggle_book_monitored(
    book_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    book.monitored = body.get("monitored", True)
    await db.commit()
    return {"id": str(book.id), "monitored": book.monitored}


@router.delete("/{book_id}")
async def delete_book(
    book_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a book and all its associations."""
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Delete associations in dependency order
    await db.execute(delete(BookAuthor).where(BookAuthor.book_id == book_id))
    await db.execute(delete(SeriesBook).where(SeriesBook.book_id == book_id))
    await db.execute(delete(Edition).where(Edition.book_id == book_id))
    await db.execute(delete(LibraryItem).where(LibraryItem.book_id == book_id))
    # Nullify download references instead of deleting
    result = await db.execute(select(Download).where(Download.book_id == book_id))
    for dl in result.scalars():
        dl.book_id = None
    await db.delete(book)
    await db.commit()
    return {"status": "deleted", "book_id": str(book_id)}
