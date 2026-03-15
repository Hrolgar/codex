import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.book import Base


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(300), unique=True)
    sort_name: Mapped[str | None] = mapped_column(String(300))
    monitored: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    openlibrary_key: Mapped[str | None] = mapped_column(String(50))
    bio: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(String(1000))
    catalog_status: Mapped[str] = mapped_column(String(20), default="idle", server_default="idle")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class BookAuthor(Base):
    __tablename__ = "book_authors"

    book_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), primary_key=True)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(50), default="author")  # author | narrator | editor
