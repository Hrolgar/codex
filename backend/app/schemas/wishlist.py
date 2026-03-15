import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.book import BookListItem


class WishlistCreate(BaseModel):
    book_id: uuid.UUID | None = None
    search_title: str | None = None
    search_author: str | None = None
    auto_download: bool = False


class WishlistUpdate(BaseModel):
    auto_download: bool | None = None
    status: str | None = None


class WishlistResponse(BaseModel):
    id: uuid.UUID
    book_id: uuid.UUID | None = None
    search_title: str | None = None
    search_author: str | None = None
    auto_download: bool
    status: str
    created_at: datetime
    updated_at: datetime
    book: BookListItem | None = None

    model_config = {"from_attributes": True}
