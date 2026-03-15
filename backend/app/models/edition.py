import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.book import Base


class Edition(Base):
    __tablename__ = "editions"
    __table_args__ = (
        UniqueConstraint("book_id", "format", "language", name="uq_edition_book_format_lang"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(
        UUID(as_uuid=True),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(500))  # Edition-specific title (may differ from book)
    language = Column(String(10))  # ISO 639-1 code: en, no, de, etc.
    format = Column(String(20))  # epub, m4b, cbz, pdf, etc.
    media_type = Column(String(20))  # ebook, audiobook, comic
    isbn_10 = Column(String(13))
    isbn_13 = Column(String(17))
    asin = Column(String(20))
    publisher = Column(String(300))
    publish_year = Column(Integer)
    page_count = Column(Integer)
    duration_seconds = Column(Integer)  # For audiobooks
    cover_url = Column(String(1000))
    description = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    book = relationship("Book", backref="editions")
