from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Book, Library, LibraryItem

router = APIRouter()


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    books_count = await db.scalar(select(func.count(Book.id)))
    libraries_count = await db.scalar(select(func.count(Library.id)))
    items_count = await db.scalar(select(func.count(LibraryItem.id)))
    return {
        "books": books_count or 0,
        "libraries": libraries_count or 0,
        "library_items": items_count or 0,
    }
