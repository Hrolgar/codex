import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, model_validator


class LibraryCreate(BaseModel):
    name: str
    scanner_type: Literal["filesystem", "audiobookshelf"]
    # Flat fields instead of raw config dict
    path: str | None = None
    url: str | None = None
    api_key: str | None = None

    @model_validator(mode="after")
    def validate_fields(self):
        if self.scanner_type == "filesystem":
            if not self.path:
                raise ValueError("'path' is required for filesystem libraries")
        elif self.scanner_type == "audiobookshelf":
            if not self.url:
                raise ValueError("'url' is required for audiobookshelf libraries")
            if not self.api_key:
                raise ValueError("'api_key' is required for audiobookshelf libraries")
        return self

    def to_config(self) -> dict:
        """Convert flat fields to the internal config dict."""
        if self.scanner_type == "filesystem":
            return {"path": self.path}
        elif self.scanner_type == "audiobookshelf":
            return {"url": self.url, "api_key": self.api_key}
        return {}


class LibraryResponse(BaseModel):
    id: uuid.UUID
    name: str
    scanner_type: str
    scan_status: str
    last_scan_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    # Flat fields extracted from config
    path: str | None = None
    url: str | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def extract_config_fields(cls, data):
        """Extract flat fields from the config dict for the response."""
        # Handle both ORM objects and dicts
        if hasattr(data, "__dict__"):
            config = getattr(data, "config", None) or {}
            # Convert ORM object to dict so we can add extra fields
            values = {
                "id": data.id,
                "name": data.name,
                "scanner_type": data.scanner_type,
                "scan_status": data.scan_status,
                "last_scan_at": data.last_scan_at,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
                "path": config.get("path"),
                "url": config.get("url"),
            }
            return values
        else:
            config = data.get("config") or {}
            data["path"] = config.get("path")
            data["url"] = config.get("url")
            return data


class ScanStatus(BaseModel):
    library_id: uuid.UUID
    status: str
    items_found: int = 0
    items_matched: int = 0
