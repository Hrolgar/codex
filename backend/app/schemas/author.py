import uuid

from pydantic import BaseModel

from app.schemas.book import BookListItem


class AuthorListItem(BaseModel):
    id: uuid.UUID
    name: str
    sort_name: str | None = None
    monitored: bool = False
    photo_url: str | None = None
    catalog_status: str = "idle"
    book_count: int
    owned_count: int = 0

    model_config = {"from_attributes": True}


class AuthorSeriesBrief(BaseModel):
    id: uuid.UUID
    name: str
    book_count: int
    owned_count: int = 0


class AuthorBookListItem(BookListItem):
    owned: bool = False
    monitored: bool = True
    editions: list[dict] = []


class AuthorMediaGroup(BaseModel):
    media_type: str  # ebook, audiobook, comic
    books: list[AuthorBookListItem] = []
    total: int = 0
    owned: int = 0
    missing: int = 0
    not_monitored: int = 0


class AuthorDetail(BaseModel):
    id: uuid.UUID
    name: str
    sort_name: str | None = None
    monitored: bool = False
    openlibrary_key: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    catalog_status: str = "idle"
    series: list[AuthorSeriesBrief] = []
    standalone_books: list[AuthorBookListItem] = []  # deprecated, use media_groups
    media_groups: list[AuthorMediaGroup] = []

    model_config = {"from_attributes": True}


class AuthorCreate(BaseModel):
    name: str
