import uuid

from pydantic import BaseModel

from app.schemas.book import BookListItem


class AuthorListItem(BaseModel):
    id: uuid.UUID
    name: str
    sort_name: str | None = None
    monitored: bool = False
    photo_url: str | None = None
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


class AuthorDetail(BaseModel):
    id: uuid.UUID
    name: str
    sort_name: str | None = None
    monitored: bool = False
    openlibrary_key: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    series: list[AuthorSeriesBrief] = []
    standalone_books: list[AuthorBookListItem] = []

    model_config = {"from_attributes": True}


class AuthorCreate(BaseModel):
    name: str
