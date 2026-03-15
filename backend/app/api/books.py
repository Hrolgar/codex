import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.book import Book
from app.schemas import BookListItem, BookListResponse, BookResponse
from app.schemas.book import ReadStatusUpdate
from app.services.library_service import LibraryService

router = APIRouter()


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


_VALID_READ_STATUSES = {"unread", "reading", "read"}


@router.put("/{book_id}/status")
async def update_read_status(
    book_id: uuid.UUID,
    body: ReadStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    if body.read_status not in _VALID_READ_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid read_status. Must be one of: {', '.join(sorted(_VALID_READ_STATUSES))}",
        )

    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book.read_status = body.read_status

    if body.date_read is not None:
        book.date_read = body.date_read
    elif body.read_status == "read" and not book.date_read:
        book.date_read = datetime.now(timezone.utc)
    elif body.read_status != "read":
        book.date_read = None

    await db.commit()
    await db.refresh(book)
    return {"id": str(book.id), "read_status": book.read_status, "date_read": book.date_read}
