import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Book, Library, LibraryItem
from app.services import settings_service

router = APIRouter()


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    books_count = await db.scalar(select(func.count(Book.id)))
    libraries_count = await db.scalar(select(func.count(Library.id)))
    items_count = await db.scalar(select(func.count(LibraryItem.id)))
    ebooks_count = await db.scalar(
        select(func.count(Book.id)).where(Book.media_type == "ebook")
    )
    audiobooks_count = await db.scalar(
        select(func.count(Book.id)).where(Book.media_type == "audiobook")
    )
    return {
        "books": books_count or 0,
        "libraries": libraries_count or 0,
        "library_items": items_count or 0,
        "ebooks": ebooks_count or 0,
        "audiobooks": audiobooks_count or 0,
    }


@router.get("/settings")
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Get all settings with schema for the frontend to render forms."""
    values = await settings_service.get_all_settings(db)
    schema = settings_service.get_settings_schema()

    # Mask secret values
    for cat in schema:
        for s in cat["settings"]:
            key = s["key"]
            s["value"] = ""
            if key in values:
                if s["is_secret"] and values[key]:
                    s["value"] = "••••••••"
                else:
                    s["value"] = values[key]
    return schema


class SettingsUpdate(BaseModel):
    settings: dict[str, str]


@router.put("/settings")
async def update_settings(body: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    """Update settings from the UI."""
    # Don't save masked placeholder values
    clean = {k: v for k, v in body.settings.items() if v != "••••••••"}
    await settings_service.set_settings_bulk(db, clean)
    return {"status": "ok"}


@router.get("/settings/test-connection")
async def test_connection(
    provider: str = Query(..., description="Provider to test: 'hardcover' or 'prowlarr'"),
    db: AsyncSession = Depends(get_db),
):
    """Test connectivity to an external provider using stored credentials."""
    if provider == "hardcover":
        api_key = await settings_service.get_setting(db, "metadata.hardcover.api_key")
        if not api_key:
            return {"ok": False, "message": "Hardcover API key is not configured."}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.hardcover.app/v1/graphql",
                    json={"query": "{ me { username } }"},
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
            user = (data.get("data") or {}).get("me", {}).get("username")
            if user:
                return {"ok": True, "message": f"Connected as: {user}"}
            return {"ok": False, "message": "API key is invalid or unauthorized."}
        except httpx.HTTPError as exc:
            return {"ok": False, "message": f"Connection failed: {exc}"}

    elif provider == "prowlarr":
        base_url = await settings_service.get_setting(db, "prowlarr.url")
        api_key = await settings_service.get_setting(db, "prowlarr.api_key")
        if not base_url or not api_key:
            return {"ok": False, "message": "Prowlarr URL or API key is not configured."}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{base_url.rstrip('/')}/api/v1/system/status",
                    headers={"X-Api-Key": api_key},
                )
                resp.raise_for_status()
                data = resp.json()
            version = data.get("version", "unknown")
            return {"ok": True, "message": f"Connected as: Prowlarr v{version}"}
        except httpx.HTTPError as exc:
            return {"ok": False, "message": f"Connection failed: {exc}"}

    return {"ok": False, "message": f"Unknown provider: {provider}"}
