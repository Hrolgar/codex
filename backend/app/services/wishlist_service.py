"""Wishlist service — CRUD operations for wishlist items."""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.wishlist import WishlistItem
from app.schemas.wishlist import WishlistCreate, WishlistUpdate


async def get_wishlist(db: AsyncSession) -> list[WishlistItem]:
    """Return all wishlist items ordered by creation date."""
    result = await db.execute(
        select(WishlistItem).order_by(WishlistItem.created_at.desc())
    )
    return list(result.scalars().all())


async def add_to_wishlist(db: AsyncSession, data: WishlistCreate) -> WishlistItem:
    """Add a new wishlist item by book_id or by search_title+search_author."""
    if not data.book_id and not data.search_title:
        raise HTTPException(
            status_code=400,
            detail="Either book_id or search_title is required",
        )

    # If book_id provided, verify it exists
    if data.book_id:
        book = await db.get(Book, data.book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

    item = WishlistItem(
        book_id=data.book_id,
        search_title=data.search_title,
        search_author=data.search_author,
        auto_download=data.auto_download,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_wishlist_item(
    db: AsyncSession, item_id: uuid.UUID, data: WishlistUpdate
) -> WishlistItem | None:
    """Update a wishlist item (toggle auto_download, change status)."""
    item = await db.get(WishlistItem, item_id)
    if not item:
        return None

    if data.auto_download is not None:
        item.auto_download = data.auto_download
    if data.status is not None:
        item.status = data.status

    await db.commit()
    await db.refresh(item)
    return item


async def delete_wishlist_item(db: AsyncSession, item_id: uuid.UUID) -> bool:
    """Delete a wishlist item. Returns True if deleted."""
    item = await db.get(WishlistItem, item_id)
    if not item:
        return False
    await db.delete(item)
    await db.commit()
    return True
