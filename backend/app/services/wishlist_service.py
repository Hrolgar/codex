import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wishlist import WishlistItem
from app.schemas.wishlist import WishlistCreate, WishlistUpdate


async def get_wishlist(db: AsyncSession) -> list[WishlistItem]:
    result = await db.execute(
        select(WishlistItem).order_by(WishlistItem.created_at.desc())
    )
    return list(result.scalars().all())


async def add_to_wishlist(db: AsyncSession, data: WishlistCreate) -> WishlistItem:
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
    item = await db.get(WishlistItem, item_id)
    if not item:
        return None
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


async def delete_wishlist_item(db: AsyncSession, item_id: uuid.UUID) -> bool:
    item = await db.get(WishlistItem, item_id)
    if not item:
        return False
    await db.delete(item)
    await db.commit()
    return True
