import uuid

from pydantic import BaseModel

from app.schemas.book import BookListItem


class SeriesListItem(BaseModel):
    id: uuid.UUID
    name: str
    book_count: int
    author_names: str | None = None

    model_config = {"from_attributes": True}


class SeriesBookItem(BookListItem):
    position: float = 0.0
    owned: bool = False


class SeriesAuthor(BaseModel):
    id: uuid.UUID
    name: str


class SeriesDetail(BaseModel):
    id: uuid.UUID
    name: str
    books: list[SeriesBookItem] = []
    authors: list[SeriesAuthor] = []

    model_config = {"from_attributes": True}
