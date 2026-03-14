import uuid

from pydantic import BaseModel


class SearchQuery(BaseModel):
    query: str
    media_type: str | None = None
    page: int = 1
    page_size: int = 20


class SearchResult(BaseModel):
    book_id: uuid.UUID | None = None
    title: str
    author: str | None = None
    isbn: str | None = None
    cover_url: str | None = None
    source: str | None = None
    owned: bool = False
    match_confidence: float = 0.0
