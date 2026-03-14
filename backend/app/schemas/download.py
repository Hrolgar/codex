"""Pydantic schemas for download endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class DownloadCreate(BaseModel):
    source_url: str
    source_type: str
    book_id: uuid.UUID | None = None
    filename: str | None = None


class DownloadResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    book_id: uuid.UUID | None
    source_type: str
    source_url: str | None
    status: str
    progress: float
    error: str | None
    target_path: str | None
    created_at: datetime
    updated_at: datetime


class DownloadProgress(BaseModel):
    id: uuid.UUID
    status: str
    progress: float
