from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class MetadataResult:
    title: str | None = None
    subtitle: str | None = None
    authors: list[str] = field(default_factory=list)
    description: str | None = None
    cover_url: str | None = None
    publish_year: int | None = None
    page_count: int | None = None
    language: str | None = None
    isbn_10: str | None = None
    isbn_13: str | None = None
    series_name: str | None = None
    series_position: float | None = None
    hardcover_slug: str | None = None
    source: str = ""


@runtime_checkable
class MetadataProvider(Protocol):
    async def search(self, title: str, author: str | None = None) -> list[MetadataResult]: ...

    async def lookup_isbn(self, isbn: str) -> MetadataResult | None: ...
