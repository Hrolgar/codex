import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import BookListResponse, BookResponse
from app.services.library_service import LibraryService

router = APIRouter()


@router.get("/", response_model=BookListResponse)
async def list_books(
    q: str | None = Query(None, description="Search query"),
    media_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    svc = LibraryService(db)
    items, total = await svc.search_books(
        query=q, media_type=media_type, page=page, page_size=page_size
    )
    return BookListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    svc = LibraryService(db)
    book = await svc.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book
