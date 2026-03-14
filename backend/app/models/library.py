import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.book import Base


class Library(Base):
    __tablename__ = "libraries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    scanner_type: Mapped[str] = mapped_column(String(50))  # filesystem | audiobookshelf
    config: Mapped[dict | None] = mapped_column(JSONB)
    scan_status: Mapped[str] = mapped_column(String(20), default="idle")  # idle | scanning | error
    last_scan_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class LibraryItem(Base):
    __tablename__ = "library_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    library_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("libraries.id", ondelete="CASCADE"), index=True)
    book_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="SET NULL"), index=True)
    file_path: Mapped[str] = mapped_column(Text)
    file_format: Mapped[str | None] = mapped_column(String(20))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    raw_title: Mapped[str | None] = mapped_column(String(500))
    raw_author: Mapped[str | None] = mapped_column(String(300))
    raw_isbn: Mapped[str | None] = mapped_column(String(20))
    matched: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
