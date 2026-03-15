import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.book import Base


class RootFolder(Base):
    __tablename__ = "root_folders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    path: Mapped[str] = mapped_column(String(1000))
    media_type: Mapped[str] = mapped_column(String(20))  # ebook | audiobook | comic
    default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    scan_status: Mapped[str] = mapped_column(String(20), default="idle", server_default="idle")
    last_scan_at: Mapped[datetime | None] = mapped_column(nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
