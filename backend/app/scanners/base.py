from dataclasses import dataclass, field
from typing import AsyncIterator, Protocol, runtime_checkable


@dataclass
class ScannedItem:
    file_path: str
    file_format: str | None = None
    file_size: int | None = None
    title: str | None = None
    author: str | None = None
    isbn: str | None = None
    asin: str | None = None
    duration_seconds: int | None = None
    cover_url: str | None = None
    series: str | None = None
    series_position: float | None = None
    media_type: str = "ebook"
    file_count: int | None = None
    is_directory: bool = False
    extra: dict = field(default_factory=dict)


@runtime_checkable
class Scanner(Protocol):
    async def validate_config(self, config: dict) -> bool: ...

    async def scan(self, config: dict) -> AsyncIterator[ScannedItem]: ...
