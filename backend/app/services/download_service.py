"""Download queue service with progress tracking."""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import re
import socket
import time
import unicodedata
import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Author, Book, BookAuthor, Series, SeriesBook
from app.models.download import Download
from app.models.library import LibraryItem
from app.schemas.download import DownloadResponse
from app.services.settings_service import get_setting
from app.ws.manager import manager

logger = logging.getLogger(__name__)

# Throttle progress broadcasts to max once per 0.5s per download
_PROGRESS_INTERVAL = 0.5

# Private/internal IP networks that must be blocked for SSRF protection
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fd00::/8"),
]


def validate_download_url(url: str) -> None:
    """Validate a download URL to prevent SSRF attacks."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http and https URLs are allowed")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid URL: no hostname")
    try:
        addrinfo = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Cannot resolve hostname")
    for _family, _type, _proto, _canonname, sockaddr in addrinfo:
        ip = ipaddress.ip_address(sockaddr[0])
        for network in _BLOCKED_NETWORKS:
            if ip in network:
                raise HTTPException(status_code=400, detail="URLs pointing to internal/private networks are not allowed")


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal."""
    return os.path.basename(filename.replace("\x00", ""))


def _sanitize_for_path(name: str, max_length: int = 200) -> str:
    """Sanitize a string for use in file/directory names."""
    # Normalize unicode
    name = unicodedata.normalize("NFKD", name)
    # Remove characters that are problematic in filenames
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    # Replace spaces with underscores
    name = re.sub(r'\s+', '_', name)
    # Trim to max length
    return name[:max_length].strip("._")


def _is_torrent_source(source_url: str, source_type: str) -> bool:
    """Check if a download source is a torrent or magnet link."""
    return (
        source_type.lower() in ("torrent", "magnet")
        or source_url.startswith("magnet:")
        or source_url.endswith(".torrent")
    )


def _is_nzb_source(source_url: str, source_type: str) -> bool:
    """Check if a download source is an NZB."""
    return (
        source_type.lower() == "nzb"
        or source_url.endswith(".nzb")
    )


# Track active download tasks for cancellation
_active_tasks: dict[uuid.UUID, asyncio.Task] = {}


class DownloadService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def enqueue(
        self,
        source_url: str,
        source_type: str,
        book_id: uuid.UUID | None = None,
        target_filename: str | None = None,
        root_folder_id: uuid.UUID | None = None,
        is_upgrade: bool = False,
    ) -> Download:
        # Auto-detect upgrade: check if book already has a LibraryItem
        if book_id and not is_upgrade:
            existing = await self.db.execute(
                select(LibraryItem).where(LibraryItem.book_id == book_id).limit(1)
            )
            if existing.scalar_one_or_none() is not None:
                is_upgrade = True
                logger.info("Book %s already in library, flagging download as upgrade", book_id)

        dl = Download(
            source_type=source_type,
            source_url=source_url,
            book_id=book_id,
            status="pending",
            progress=0.0,
            target_path=target_filename,
            root_folder_id=root_folder_id,
            is_upgrade=is_upgrade,
        )
        self.db.add(dl)
        await self.db.commit()
        await self.db.refresh(dl)
        return dl

    async def get_downloads(self, status: str | None = None) -> list[DownloadResponse]:
        stmt = select(Download).order_by(Download.created_at.desc())
        if status:
            stmt = stmt.where(Download.status == status)
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [DownloadResponse.model_validate(r) for r in rows]

    async def cancel(self, download_id: uuid.UUID) -> bool:
        dl = await self.db.get(Download, download_id)
        if not dl:
            return False
        if dl.status == "downloading":
            # Cancel the active asyncio task if running
            task = _active_tasks.get(download_id)
            if task and not task.done():
                task.cancel()
            dl.status = "error"
            dl.error = "Cancelled by user"
        elif dl.status == "pending":
            await self.db.delete(dl)
        else:
            await self.db.delete(dl)
        await self.db.commit()
        return True

    async def retry(self, download_id: uuid.UUID) -> bool:
        dl = await self.db.get(Download, download_id)
        if not dl or dl.status not in ("error",):
            return False
        dl.status = "pending"
        dl.progress = 0.0
        dl.error = None
        await self.db.commit()
        return True

    async def delete(self, download_id: uuid.UUID) -> bool:
        dl = await self.db.get(Download, download_id)
        if not dl:
            return False
        await self.db.delete(dl)
        await self.db.commit()
        return True


async def _get_dir(db: AsyncSession, key: str, fallback: str) -> Path:
    val = await get_setting(db, key)
    return Path(val) if val else Path(fallback)


async def _get_book_context(db: AsyncSession, book_id: uuid.UUID):
    """Build a PathContext from a book's metadata."""
    from app.services.path_template_service import PathContext

    book = await db.get(Book, book_id)
    if not book:
        return None, None

    # Get first author name
    author_result = await db.execute(
        select(Author.name, Author.sort_name)
        .join(BookAuthor, Author.id == BookAuthor.author_id)
        .where(BookAuthor.book_id == book_id)
        .limit(1)
    )
    author_row = author_result.first()
    author_name = author_row[0] if author_row else "Unknown"

    # Get series info
    series_result = await db.execute(
        select(Series.name, SeriesBook.position)
        .join(SeriesBook, Series.id == SeriesBook.series_id)
        .where(SeriesBook.book_id == book_id)
        .limit(1)
    )
    series_row = series_result.first()

    ctx = PathContext(
        author=author_name,
        title=book.title,
        series=series_row[0] if series_row else "",
        series_position=str(series_row[1]) if series_row else "",
        year=str(book.publish_year) if book.publish_year else "",
        isbn=book.isbn_13 or book.isbn_10 or "",
        language=book.language or "",
    )
    return book, ctx


async def _get_media_settings(db: AsyncSession, media_type: str, root_folder_id: uuid.UUID | None = None) -> tuple[str, str, bool]:
    """Get destination, path_template, and hardlink setting for a media type.

    If *root_folder_id* is provided, that folder is used directly. Otherwise
    looks up the default RootFolder for the media type. Falls back to the
    legacy downloads.*.destination settings if no root folder is configured.
    """
    from app.models.root_folder import RootFolder
    from app.services.path_template_service import DEFAULT_TEMPLATES

    root_folder = None
    if root_folder_id:
        result = await db.execute(
            select(RootFolder).where(RootFolder.id == root_folder_id).limit(1)
        )
        root_folder = result.scalar_one_or_none()

    # Fall back to the default root folder for this media type
    if not root_folder:
        result = await db.execute(
            select(RootFolder).where(
                RootFolder.media_type == media_type,
                RootFolder.default.is_(True),
            ).limit(1)
        )
        root_folder = result.scalar_one_or_none()

    media_key_map = {
        "ebook": "books",
        "audiobook": "audiobooks",
        "comic": "comics",
    }
    key = media_key_map.get(media_type, "books")

    if root_folder:
        destination = root_folder.path
    else:
        # Legacy fallback: read from settings
        destination = await get_setting(db, f"downloads.{key}.destination") or f"/downloads/{key}"

    # Comics uses .template instead of .path_template
    if key == "comics":
        path_template = await get_setting(db, f"downloads.{key}.template") or DEFAULT_TEMPLATES.get(media_type, DEFAULT_TEMPLATES["ebook"])
    else:
        path_template = await get_setting(db, f"downloads.{key}.path_template") or DEFAULT_TEMPLATES.get(media_type, DEFAULT_TEMPLATES["ebook"])
    hardlink_val = await get_setting(db, f"downloads.{key}.hardlink") or "false"
    use_hardlink = hardlink_val.lower() == "true"

    return destination, path_template, use_hardlink


async def _create_library_item(
    db: AsyncSession, dl: Download, file_path: str,
) -> None:
    """Auto-create a LibraryItem after a download is organized.

    If the download is flagged as an upgrade, removes old LibraryItem(s)
    and their files AFTER creating the new one so a failure never leaves
    the user with neither version.
    """
    from app.models.root_folder import RootFolder

    # Refuse to create a LibraryItem pointing at a directory — this can
    # happen when a torrent/NZB client stores to a folder.  Let the
    # root-folder scanner discover the actual file(s) instead.
    p = Path(file_path)
    if p.is_dir():
        logger.warning(
            "Skipping LibraryItem for download %s: path is a directory (%s). "
            "The root-folder scanner will pick up the organised file.",
            dl.id, file_path,
        )
        return

    root_folder_id = dl.root_folder_id
    if not root_folder_id:
        book = await db.get(Book, dl.book_id) if dl.book_id else None
        media_type = book.media_type if book else "ebook"
        result = await db.execute(
            select(RootFolder).where(
                RootFolder.media_type == media_type,
                RootFolder.default.is_(True),
            ).limit(1)
        )
        rf = result.scalar_one_or_none()
        if rf:
            root_folder_id = rf.id

    if not root_folder_id:
        logger.warning(
            "No root folder for download %s, skipping LibraryItem", dl.id,
        )
        return

    try:
        file_size = p.stat().st_size if p.exists() else None
    except OSError:
        file_size = None

    # Create the NEW LibraryItem first — this ensures the user always has
    # at least one copy even if the subsequent old-file cleanup fails.
    item = LibraryItem(
        library_id=root_folder_id,
        book_id=dl.book_id,
        file_path=file_path,
        file_format=p.suffix.lstrip(".") or None,
        file_size=file_size,
        matched=dl.book_id is not None,
    )
    db.add(item)
    logger.info("Created LibraryItem for download %s at %s", dl.id, file_path)

    # Handle upgrade: remove old LibraryItems AFTER the new one exists so
    # a mid-process failure never leaves the user with zero copies.
    if dl.is_upgrade and dl.book_id:
        # Build a set of allowed root-folder real-paths for path-traversal
        # validation so we never delete files outside a known root folder.
        rf_result = await db.execute(select(RootFolder))
        root_folders = rf_result.scalars().all()
        allowed_roots = [os.path.realpath(rf.path) for rf in root_folders]

        old_items_result = await db.execute(
            select(LibraryItem).where(LibraryItem.book_id == dl.book_id)
        )
        old_items = old_items_result.scalars().all()
        removed = 0
        for old_item in old_items:
            # Skip the newly-created item
            if old_item.file_path == file_path:
                continue
            # Delete the old file if it still exists and is within a root folder
            old_path = Path(old_item.file_path)
            if old_path.exists():
                real_old = os.path.realpath(old_path)
                if not any(real_old.startswith(root + os.sep) or real_old == root for root in allowed_roots):
                    logger.warning(
                        "Upgrade: refusing to delete %s — not inside any root folder",
                        old_item.file_path,
                    )
                else:
                    try:
                        old_path.unlink()
                        logger.info(
                            "Upgrade: deleted old file %s for book %s",
                            old_item.file_path, dl.book_id,
                        )
                    except OSError:
                        logger.warning(
                            "Upgrade: failed to delete old file %s",
                            old_item.file_path, exc_info=True,
                        )
            await db.delete(old_item)
            removed += 1
        if removed:
            logger.info(
                "Upgrade: removed %d old LibraryItem(s) for book %s",
                removed, dl.book_id,
            )


async def _process_single(dl: Download, db: AsyncSession) -> None:
    """Download a single file with chunked streaming and progress updates."""
    from app.services.download_client_service import get_client_from_settings, QBittorrentClient, SABnzbdClient
    from app.services.hardlink_service import process_completed_download
    from app.services.path_template_service import PathContext

    # Check if we should delegate to a download client
    if _is_torrent_source(dl.source_url, dl.source_type):
        client = await get_client_from_settings(db)
        if isinstance(client, QBittorrentClient):
            dl.status = "downloading"
            dl.progress = 0.0
            await db.commit()
            await _broadcast_progress(dl)
            try:
                # Determine save path from settings
                book = await db.get(Book, dl.book_id) if dl.book_id else None
                media_type = book.media_type if book else "ebook"
                destination, _, _ = await _get_media_settings(db, media_type, root_folder_id=dl.root_folder_id)
                await client.add_torrent(dl.source_url, save_path=destination)
                dl.status = "complete"
                dl.progress = 1.0
                dl.target_path = destination
                await _create_library_item(db, dl, destination)
                await db.commit()
                await _broadcast_progress(dl)
                logger.info("Torrent sent to qBittorrent: %s", dl.id)
                try:
                    from app.services.notification_service import notify
                    book = await db.get(Book, dl.book_id) if dl.book_id else None
                    dl_title = book.title if book else "torrent download"
                    await notify(db, title="Download Complete", message=f"Download complete: {dl_title}", notification_type="success")
                except Exception:
                    logger.warning("Failed to send download notification")
                return
            except Exception as exc:
                logger.exception("qBittorrent failed for %s", dl.id)
                dl.status = "error"
                dl.error = f"qBittorrent error: {str(exc)[:400]}"
                await db.commit()
                await _broadcast_progress(dl)
                return

    if _is_nzb_source(dl.source_url, dl.source_type):
        client = await get_client_from_settings(db)
        if isinstance(client, SABnzbdClient):
            dl.status = "downloading"
            dl.progress = 0.0
            await db.commit()
            await _broadcast_progress(dl)
            try:
                book = await db.get(Book, dl.book_id) if dl.book_id else None
                name = book.title if book else ""
                await client.add_nzb(dl.source_url, name=name)
                dl.status = "complete"
                dl.progress = 1.0
                destination, _, _ = await _get_media_settings(db, book.media_type if book else "ebook", root_folder_id=dl.root_folder_id)
                dl.target_path = destination
                await _create_library_item(db, dl, destination)
                await db.commit()
                await _broadcast_progress(dl)
                logger.info("NZB sent to SABnzbd: %s", dl.id)
                try:
                    from app.services.notification_service import notify
                    dl_title = book.title if book else "NZB download"
                    await notify(db, title="Download Complete", message=f"Download complete: {dl_title}", notification_type="success")
                except Exception:
                    logger.warning("Failed to send download notification")
                return
            except Exception as exc:
                logger.exception("SABnzbd failed for %s", dl.id)
                dl.status = "error"
                dl.error = f"SABnzbd error: {str(exc)[:400]}"
                await db.commit()
                await _broadcast_progress(dl)
                return

    # Fall back to direct HTTP download
    download_dir = await _get_dir(db, "download.dir", "/downloads")
    temp_dir = await _get_dir(db, "download.temp_dir", "/tmp/codex")
    download_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    dl.status = "downloading"
    dl.progress = 0.0
    await db.commit()
    await _broadcast_progress(dl)

    # Determine filename — sanitize to prevent path traversal
    raw_filename = dl.target_path or dl.source_url.rsplit("/", 1)[-1] or f"{dl.id}"
    filename = sanitize_filename(raw_filename)
    if not filename:
        filename = str(dl.id)
    temp_path = temp_dir / f"{dl.id}_{filename}"
    final_path = download_dir / filename
    # Verify resolved path is within download directory
    if not str(final_path.resolve()).startswith(str(download_dir.resolve())):
        dl.status = "error"
        dl.error = "Invalid filename: path traversal detected"
        await db.commit()
        await _broadcast_progress(dl)
        return

    last_broadcast = 0.0

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=300) as client:
            async with client.stream("GET", dl.source_url) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                received = 0

                with open(temp_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
                        received += len(chunk)
                        if total > 0:
                            dl.progress = min(received / total, 1.0)
                        now = time.monotonic()
                        if now - last_broadcast >= _PROGRESS_INTERVAL:
                            await db.commit()
                            await _broadcast_progress(dl)
                            last_broadcast = now

        # Move to final location
        temp_path.rename(final_path)

        # Post-download: use path template and hardlink service if book is linked
        organized_path = await _organize_file(db, dl, final_path, download_dir)

        dl.status = "complete"
        dl.progress = 1.0
        dl.target_path = str(organized_path)
        await _create_library_item(db, dl, str(organized_path))
        await db.commit()
        await _broadcast_progress(dl)
        logger.info("Download complete: %s -> %s", dl.id, organized_path)

        # Send notification for completed download
        try:
            from app.services.notification_service import notify
            book = await db.get(Book, dl.book_id) if dl.book_id else None
            dl_title = book.title if book else organized_path.name
            await notify(
                db,
                title="Download Complete",
                message=f"Download complete: {dl_title}",
                notification_type="success",
            )
        except Exception:
            logger.warning("Failed to send download notification")

    except Exception as exc:
        logger.exception("Download failed for %s", dl.id)
        dl.status = "error"
        dl.error = str(exc)[:500]
        await db.commit()
        await _broadcast_progress(dl)
        # Clean up temp file
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass


async def _organize_file(
    db: AsyncSession, dl: Download, current_path: Path, download_dir: Path
) -> Path:
    """Organize downloaded file using path templates and hardlink service."""
    from app.services.hardlink_service import process_completed_download

    if not dl.book_id:
        return current_path

    book, ctx = await _get_book_context(db, dl.book_id)
    if not book or not ctx:
        return current_path

    # Get media-specific settings
    destination, path_template, use_hardlink = await _get_media_settings(db, book.media_type, root_folder_id=dl.root_folder_id)

    # Set file format on context
    ctx.format = current_path.suffix.lstrip(".")
    ctx.original_name = current_path.stem

    try:
        dest_path = await process_completed_download(
            source_path=str(current_path),
            destination_root=destination,
            path_template=path_template,
            context=ctx,
            use_hardlink=use_hardlink,
        )
        return Path(dest_path)
    except Exception:
        logger.warning("Failed to organize file via hardlink service, keeping at %s", current_path, exc_info=True)
        return current_path


async def _broadcast_progress(dl: Download) -> None:
    await manager.broadcast({
        "type": "download_progress",
        "id": str(dl.id),
        "status": dl.status,
        "progress": dl.progress,
        "error": dl.error,
        "is_upgrade": dl.is_upgrade,
    })


async def process_download_queue() -> None:
    """Background loop that processes pending downloads every 2 seconds."""
    while True:
        try:
            async with async_session() as db:
                stmt = select(Download).where(Download.status == "pending").order_by(Download.created_at).limit(1)
                result = await db.execute(stmt)
                dl = result.scalar_one_or_none()
                if dl:
                    task = asyncio.current_task()
                    _active_tasks[dl.id] = task
                    try:
                        await _process_single(dl, db)
                    except asyncio.CancelledError:
                        logger.info("Download %s was cancelled", dl.id)
                    finally:
                        _active_tasks.pop(dl.id, None)
        except Exception:
            logger.exception("Error in download queue processor")
        await asyncio.sleep(2)
