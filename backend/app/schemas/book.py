import uuid
from datetime import datetime

from pydantic import BaseModel


class AuthorBrief(BaseModel):
    id: uuid.UUID
    name: str
    role: str = "author"


class SeriesBrief(BaseModel):
    id: uuid.UUID
    name: str
    position: float


class BookCreate(BaseModel):
    title: str
    subtitle: str | None = None
    description: str | None = None
    cover_url: str | None = None
    media_type: str = "ebook"
    language: str | None = None
    publish_year: int | None = None
    page_count: int | None = None
    duration_seconds: int | None = None
    isbn_10: str | None = None
    isbn_13: str | None = None
    asin: str | None = None


class LibraryItemBrief(BaseModel):
    id: uuid.UUID
    library_id: uuid.UUID
    file_path: str
    file_format: str | None = None
    file_size: int | None = None

    model_config = {"from_attributes": True}


class BookResponse(BaseModel):
    id: uuid.UUID
    title: str
    subtitle: str | None = None
    description: str | None = None
    cover_url: str | None = None
    media_type: str
    language: str | None = None
    publish_year: int | None = None
    page_count: int | None = None
    duration_seconds: int | None = None
    isbn_10: str | None = None
    isbn_13: str | None = None
    asin: str | None = None
    openlibrary_key: str | None = None
    hardcover_slug: str | None = None
    metadata_source: str | None = None
    authors: list[AuthorBrief] = []
    series: list[SeriesBrief] = []
    library_items: list[LibraryItemBrief] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookListItem(BaseModel):
    id: uuid.UUID
    title: str
    author: str | None = None
    media_type: str
    cover_url: str | None = None
    isbn_13: str | None = None
    publish_year: int | None = None
    owned: bool = False
    monitored: bool = True

    model_config = {"from_attributes": True}


class BookListResponse(BaseModel):
    items: list[BookListItem]
    total: int
    page: int
    per_page: int
