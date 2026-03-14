"""In-app settings stored in the database, editable via the UI."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import AppSetting

# Settings schema: key -> (label, description, category, is_secret)
SETTINGS_SCHEMA: dict[str, tuple[str, str, str, bool]] = {
    # Audiobookshelf
    "audiobookshelf.url": ("Audiobookshelf URL", "Base URL of your Audiobookshelf instance", "audiobookshelf", False),
    "audiobookshelf.api_key": ("API Key", "Audiobookshelf API key", "audiobookshelf", True),

    # Prowlarr
    "prowlarr.url": ("Prowlarr URL", "Base URL of your Prowlarr instance", "prowlarr", False),
    "prowlarr.api_key": ("API Key", "Prowlarr API key", "prowlarr", True),

    # Download clients
    "download.dir": ("Download Directory", "Where to save downloaded files", "downloads", False),
    "download.temp_dir": ("Temp Directory", "Temporary directory for in-progress downloads", "downloads", False),

    # Metadata
    "metadata.hardcover_api_key": ("Hardcover API Key", "API key for Hardcover metadata provider", "metadata", True),
    "metadata.google_books_api_key": ("Google Books API Key", "API key for Google Books metadata provider", "metadata", True),

    # General
    "general.languages": ("Languages", "Comma-separated language codes to include (e.g. en,no). Leave empty for all.", "general", False),
}


async def get_all_settings(db: AsyncSession) -> dict[str, str]:
    """Get all settings as a flat dict."""
    result = await db.execute(select(AppSetting))
    rows = result.scalars().all()
    return {row.key: row.value for row in rows}


async def get_setting(db: AsyncSession, key: str) -> str | None:
    """Get a single setting value."""
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else None


async def set_setting(db: AsyncSession, key: str, value: str) -> None:
    """Set a single setting value (upsert)."""
    if key not in SETTINGS_SCHEMA:
        raise ValueError(f"Unknown setting key: {key}")
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    existing = result.scalar_one_or_none()
    if existing:
        existing.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    await db.commit()


async def set_settings_bulk(db: AsyncSession, settings: dict[str, str]) -> None:
    """Set multiple settings at once."""
    for key, value in settings.items():
        if key not in SETTINGS_SCHEMA:
            continue
        result = await db.execute(select(AppSetting).where(AppSetting.key == key))
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = value
        else:
            db.add(AppSetting(key=key, value=value))
    await db.commit()


def get_settings_schema() -> list[dict]:
    """Return the settings schema for the frontend to render forms."""
    categories: dict[str, list[dict]] = {}
    for key, (label, description, category, is_secret) in SETTINGS_SCHEMA.items():
        if category not in categories:
            categories[category] = []
        categories[category].append({
            "key": key,
            "label": label,
            "description": description,
            "is_secret": is_secret,
        })
    return [{"category": cat, "settings": items} for cat, items in categories.items()]
