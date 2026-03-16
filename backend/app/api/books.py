import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Book, BookAuthor, Download, Edition, LibraryItem, SeriesBook
from app.models.root_folder import RootFolder
from app.schemas import BookListItem, BookListResponse, BookResponse
from app.services.library_service import LibraryService

router = APIRouter()


class ManualMatchRequest(BaseModel):
    file_path: str


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


@router.post("/{book_id}/match")
async def manual_match(
    book_id: uuid.UUID,
    body: ManualMatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually match an existing file to a book by creating a LibraryItem link."""
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

    if existing_item:
        # Update the existing unmatched LibraryItem to point to this book
        existing_item.book_id = book_id
        existing_item.matched = True
        await db.commit()
        return {
            "status": "matched",
            "library_item_id": str(existing_item.id),
            "book_id": str(book_id),
            "manual_match": True,
        }

    # No existing LibraryItem — find the root folder this file belongs to
    rf_stmt = select(RootFolder).order_by(RootFolder.created_at)
    rf_result = await db.execute(rf_stmt)
    root_folders = rf_result.scalars().all()

    library_id = None
    real_file = str(file_path.resolve())
    for rf in root_folders:
        real_root = str(Path(rf.path).resolve())
        if real_file.startswith(real_root + "/") or real_file == real_root:
            library_id = rf.id
            break

    if not library_id:
        raise HTTPException(
            status_code=400,
            detail="File is not inside any configured root folder",
        )

    try:
        file_size = file_path.stat().st_size
    except OSError:
        file_size = None

    item = LibraryItem(
        library_id=library_id,
        book_id=book_id,
        file_path=body.file_path,
        file_format=file_path.suffix.lstrip(".") or None,
        file_size=file_size,
        matched=True,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return {
        "status": "matched",
        "library_item_id": str(item.id),
        "book_id": str(book_id),
        "manual_match": True,
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
