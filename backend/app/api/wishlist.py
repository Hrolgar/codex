import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.book import Book
from app.models.wishlist import WishlistItem
from app.schemas.book import BookListItem
from app.schemas.wishlist import WishlistCreate, WishlistResponse, WishlistUpdate
from app.services.wishlist_service import (
    add_to_wishlist,
    delete_wishlist_item,
    get_wishlist,
    update_wishlist_item,
)

router = APIRouter()


async def _enrich_with_book(db: AsyncSession, item: WishlistItem) -> WishlistResponse:
    """Build a WishlistResponse, joining book data if book_id is set."""
    book = None
    if item.book_id:
        row = await db.get(Book, item.book_id)
        if row:
            book = BookListItem(
                id=row.id,
                title=row.title,
                media_type=row.media_type,
                cover_url=row.cover_url,
                isbn_13=row.isbn_13,
                publish_year=row.publish_year,
            )
    return WishlistResponse(
        id=item.id,
        book_id=item.book_id,
        search_title=item.search_title,
        search_author=item.search_author,
        auto_download=item.auto_download,
        status=item.status,
        created_at=item.created_at,
        updated_at=item.updated_at,
        book=book,
    )


@router.get("", response_model=list[WishlistResponse])
async def list_wishlist(db: AsyncSession = Depends(get_db)):
    items = await get_wishlist(db)
    return [await _enrich_with_book(db, item) for item in items]


@router.post("", response_model=WishlistResponse, status_code=201)
async def create_wishlist_item(data: WishlistCreate, db: AsyncSession = Depends(get_db)):
    item = await add_to_wishlist(db, data)
    return await _enrich_with_book(db, item)


@router.put("/{item_id}", response_model=WishlistResponse)
async def update_wishlist(
    item_id: uuid.UUID, data: WishlistUpdate, db: AsyncSession = Depends(get_db)
):
    item = await update_wishlist_item(db, item_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Wishlist item not found")
    return await _enrich_with_book(db, item)


@router.delete("/{item_id}", status_code=204)
async def delete_wishlist(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    deleted = await delete_wishlist_item(db, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Wishlist item not found")
