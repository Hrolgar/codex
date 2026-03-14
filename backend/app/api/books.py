import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import BookListItem, BookListResponse, BookResponse
from app.services.library_service import LibraryService

router = APIRouter()


@router.get("/", response_model=BookListResponse)
async def list_books(
    search: str | None = Query(None, description="Search query"),
    media_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    svc = LibraryService(db)
    items, total = await svc.get_books(
        query=search, media_type=media_type, page=page, per_page=per_page
    )
    return BookListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    svc = LibraryService(db)
    book = await svc.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book
