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
    "prowlarr.enabled": ("Prowlarr Enabled", "Enable Prowlarr as an indexer", "prowlarr", False),
    "prowlarr.url": ("Prowlarr URL", "Base URL of your Prowlarr instance", "prowlarr", False),
    "prowlarr.api_key": ("API Key", "Prowlarr API key", "prowlarr", True),
    "prowlarr.indexers": ("Prowlarr Indexers", "Cached indexer list from Prowlarr (JSON)", "prowlarr", False),
    "prowlarr.selected_indexers": ("Prowlarr Selected Indexers", "Selected indexer IDs (JSON array)", "prowlarr", False),

    # Download clients – qBittorrent
    "downloadclient.qbittorrent.enabled": ("qBittorrent Enabled", "Enable qBittorrent as a download client", "downloadclient", False),
    "downloadclient.qbittorrent.url": ("qBittorrent URL", "Base URL of your qBittorrent instance", "downloadclient", False),
    "downloadclient.qbittorrent.username": ("qBittorrent Username", "Username for qBittorrent", "downloadclient", False),
    "downloadclient.qbittorrent.password": ("qBittorrent Password", "Password for qBittorrent", "downloadclient", True),
    "downloadclient.qbittorrent.category.ebook": ("qBittorrent Ebook Category", "qBittorrent category for ebook downloads", "downloadclient", False),
    "downloadclient.qbittorrent.category.audiobook": ("qBittorrent Audiobook Category", "qBittorrent category for audiobook downloads", "downloadclient", False),
    "downloadclient.qbittorrent.category.comic": ("qBittorrent Comic Category", "qBittorrent category for comic downloads", "downloadclient", False),

    # Download clients – SABnzbd
    "downloadclient.sabnzbd.enabled": ("SABnzbd Enabled", "Enable SABnzbd as a download client", "downloadclient", False),
    "downloadclient.sabnzbd.url": ("SABnzbd URL", "Base URL of your SABnzbd instance", "downloadclient", False),
    "downloadclient.sabnzbd.api_key": ("SABnzbd API Key", "API key for SABnzbd", "downloadclient", True),
    "downloadclient.sabnzbd.category.ebook": ("SABnzbd Ebook Category", "SABnzbd category for ebook downloads", "downloadclient", False),
    "downloadclient.sabnzbd.category.audiobook": ("SABnzbd Audiobook Category", "SABnzbd category for audiobook downloads", "downloadclient", False),
    "downloadclient.sabnzbd.category.comic": ("SABnzbd Comic Category", "SABnzbd category for comic downloads", "downloadclient", False),

    # Legacy download dirs
    "download.dir": ("Download Directory", "Where to save downloaded files", "downloads", False),
    "download.temp_dir": ("Temp Directory", "Temporary directory for in-progress downloads", "downloads", False),

    # General
    "general.languages": ("Languages", "Comma-separated language codes to include (e.g. en,no). Leave empty for all.", "general", False),
    "general.theme": ("Theme", "UI color theme", "general", False),
    "general.library_url": ("Library URL", "URL to your ebook library (e.g. Calibre-Web)", "general", False),
    "general.audiobook_library_url": ("Audiobook Library URL", "URL to your audiobook library (e.g. Audiobookshelf)", "general", False),
    "general.supported_book_formats": ("Supported Book Formats", "Comma-separated list of supported ebook file formats", "general", False),
    "general.supported_audiobook_formats": ("Supported Audiobook Formats", "Comma-separated list of supported audiobook file formats", "general", False),

    # Downloads – Books
    "downloads.books.destination": ("Books Destination", "Directory where downloaded books are saved", "downloads", False),
    "downloads.books.file_organization": ("Books File Organization", "How to organize downloaded book files (rename, copy, move)", "downloads", False),
    "downloads.books.path_template": ("Books Path Template", "Path template for organizing book files", "downloads", False),
    "downloads.books.hardlink": ("Books Hardlink", "Use hardlinks instead of copying book files", "downloads", False),
    "downloads.audiobooks.destination": ("Audiobooks Destination", "Directory where downloaded audiobooks are saved", "downloads", False),
    "downloads.audiobooks.file_organization": ("Audiobooks File Organization", "How to organize downloaded audiobook files (rename, copy, move)", "downloads", False),
    "downloads.audiobooks.path_template": ("Audiobooks Path Template", "Path template for organizing audiobook files", "downloads", False),
    "downloads.audiobooks.hardlink": ("Audiobooks Hardlink", "Use hardlinks instead of copying audiobook files", "downloads", False),

    # Downloads – Comics
    "downloads.comics.destination": ("Comics Destination", "Directory where downloaded comics are saved", "downloads", False),
    "downloads.comics.template": ("Comics Path Template", "Path template for organizing comic files", "downloads", False),
    "downloads.comics.hardlink": ("Comics Hardlink", "Use hardlinks instead of copying comic files", "downloads", False),

    # Metadata Providers
    "metadata.hardcover.enabled": ("Hardcover Enabled", "Enable Hardcover as a metadata provider", "metadata", False),
    "metadata.hardcover.api_key": ("Hardcover API Key", "API key for Hardcover metadata provider", "metadata", True),
    "metadata.openlibrary.enabled": ("Open Library Enabled", "Enable Open Library as a metadata provider", "metadata", False),
    "metadata.openlibrary.api_key": ("Open Library API Key", "API key for Open Library metadata provider", "metadata", True),
    "metadata.google.enabled": ("Google Books Enabled", "Enable Google Books as a metadata provider", "metadata", False),
    "metadata.google.api_key": ("Google Books API Key", "API key for Google Books metadata provider", "metadata", True),
    "metadata.google_books.enabled": ("Google Books (Legacy) Enabled", "Enable Google Books as a metadata provider (legacy key)", "metadata", False),
    "metadata.google_books.api_key": ("Google Books (Legacy) API Key", "API key for Google Books (legacy key)", "metadata", True),

    # Search
    "search.mode": ("Search Mode", "Universal or Direct search mode", "search", False),
    "search.book_provider": ("Book Metadata Provider", "Primary metadata provider for books", "search", False),
    "search.audiobook_provider": ("Audiobook Metadata Provider", "Metadata provider for audiobooks", "search", False),
    "search.default_source": ("Default Release Source", "Default release source in search modal", "search", False),

    # Auto-download
    "auto_download.interval_hours": ("Check Interval (hours)", "How often to check wishlist for auto-downloads (default: 6)", "auto_download", False),

    # Catalog
    "catalog.refresh_interval_hours": ("Refresh Interval (hours)", "How often to refresh monitored author catalogs (default: 24)", "catalog", False),

    # Notifications
    "notifications.discord_webhook_url": ("Discord Webhook URL", "Discord webhook URL for sending notifications", "notifications", False),
}

# Default values for settings that should have non-empty defaults.
SETTINGS_DEFAULTS: dict[str, str] = {
    "general.languages": "en,no",
    "general.theme": "dark",
    "general.library_url": "",
    "general.audiobook_library_url": "",
    "general.supported_book_formats": "epub,mobi,azw3,pdf,cbz,cbr",
    "general.supported_audiobook_formats": "m4b,mp3,m4a",
    # Prowlarr
    "prowlarr.enabled": "false",
    "prowlarr.url": "",
    "prowlarr.api_key": "",
    "prowlarr.indexers": "",
    "prowlarr.selected_indexers": "",
    # Download clients – qBittorrent
    "downloadclient.qbittorrent.enabled": "false",
    "downloadclient.qbittorrent.url": "",
    "downloadclient.qbittorrent.username": "",
    "downloadclient.qbittorrent.password": "",
    "downloadclient.qbittorrent.category.ebook": "codex-books",
    "downloadclient.qbittorrent.category.audiobook": "codex-audiobooks",
    "downloadclient.qbittorrent.category.comic": "codex-comics",
    # Download clients – SABnzbd
    "downloadclient.sabnzbd.enabled": "false",
    "downloadclient.sabnzbd.url": "",
    "downloadclient.sabnzbd.api_key": "",
    "downloadclient.sabnzbd.category.ebook": "codex-books",
    "downloadclient.sabnzbd.category.audiobook": "codex-audiobooks",
    "downloadclient.sabnzbd.category.comic": "codex-comics",
    # Downloads – Books
    "downloads.books.destination": "/downloads/books",
    "downloads.books.file_organization": "rename",
    "downloads.books.path_template": "{Author}/{Series}/{SeriesPosition} - {Title}",
    "downloads.books.hardlink": "true",
    # Downloads – Audiobooks
    "downloads.audiobooks.destination": "/downloads/audiobooks",
    "downloads.audiobooks.file_organization": "rename",
    "downloads.audiobooks.path_template": "{Author}/{Series}/{SeriesPosition} - {Title}",
    "downloads.audiobooks.hardlink": "true",
    # Downloads – Comics
    "downloads.comics.destination": "/downloads/comics",
    "downloads.comics.template": "{Author}/{Series}/{Title}",
    "downloads.comics.hardlink": "true",
    # Metadata providers
    "metadata.hardcover.enabled": "false",
    "metadata.hardcover.api_key": "",
    "metadata.openlibrary.enabled": "true",
    "metadata.openlibrary.api_key": "",
    "metadata.google.enabled": "false",
    "metadata.google.api_key": "",
    "metadata.google_books.enabled": "false",
    "metadata.google_books.api_key": "",
    # Search
    "search.mode": "universal",
    "search.book_provider": "openlibrary",
    "search.audiobook_provider": "book",
    "search.default_source": "prowlarr",
}


async def get_all_settings(db: AsyncSession) -> dict[str, str]:
    """Get all settings as a flat dict, with defaults applied."""
    merged = dict(SETTINGS_DEFAULTS)
    result = await db.execute(select(AppSetting))
    rows = result.scalars().all()
    for row in rows:
        merged[row.key] = row.value
    return merged


async def get_setting(db: AsyncSession, key: str) -> str | None:
    """Get a single setting value, falling back to default."""
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    if row is not None:
        return row.value
    return SETTINGS_DEFAULTS.get(key)


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
