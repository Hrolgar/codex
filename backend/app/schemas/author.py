import uuid

from pydantic import BaseModel

from app.schemas.book import BookListItem


class AuthorListItem(BaseModel):
    id: uuid.UUID
    name: str
    sort_name: str | None = None
    book_count: int

    model_config = {"from_attributes": True}


class AuthorSeriesBrief(BaseModel):
    id: uuid.UUID
    name: str
    book_count: int


class AuthorDetail(BaseModel):
    id: uuid.UUID
    name: str
    sort_name: str | None = None
    series: list[AuthorSeriesBrief] = []
    standalone_books: list[BookListItem] = []

    model_config = {"from_attributes": True}
