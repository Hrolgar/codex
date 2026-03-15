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
    raw_title: str | None = None
    author: str | None = None
    isbn: str | None = None
    cover_url: str | None = None
    source: str | None = None
    download_url: str | None = None
    owned: bool = False
    match_confidence: float = 0.0
    indexer: str | None = None
    size: int | None = None
    seeders: int | None = None
    leechers: int | None = None
    format: str | None = None
