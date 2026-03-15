import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Book(Base):
    __tablename__ = "books"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500))
    subtitle: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    cover_url: Mapped[str | None] = mapped_column(String(1000))
    media_type: Mapped[str] = mapped_column(String(20), default="ebook")  # ebook | audiobook | comic
    language: Mapped[str | None] = mapped_column(String(10))
    publish_year: Mapped[int | None]
    page_count: Mapped[int | None]
    duration_seconds: Mapped[int | None]
    isbn_10: Mapped[str | None] = mapped_column(String(10), index=True)
    isbn_13: Mapped[str | None] = mapped_column(String(13), index=True)
    asin: Mapped[str | None] = mapped_column(String(10), index=True)
    openlibrary_key: Mapped[str | None] = mapped_column(String(50))
    hardcover_slug: Mapped[str | None] = mapped_column(String(200))
    monitored: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    metadata_source: Mapped[str | None] = mapped_column(String(50))
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
