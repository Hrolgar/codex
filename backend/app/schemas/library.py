import uuid
from datetime import datetime

from pydantic import BaseModel


class LibraryCreate(BaseModel):
    name: str
    scanner_type: str
    config: dict | None = None


class LibraryResponse(BaseModel):
    id: uuid.UUID
    name: str
    scanner_type: str
    config: dict | None = None
    scan_status: str
    last_scan_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScanStatus(BaseModel):
    library_id: uuid.UUID
    status: str
    items_found: int = 0
    items_matched: int = 0
