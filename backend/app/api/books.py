import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Book, BookAuthor, Download, Edition, LibraryItem, SeriesBook
from app.schemas import BookListItem, BookListResponse, BookResponse
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
