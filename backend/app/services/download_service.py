"""Download queue service with progress tracking."""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import socket
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import re
import unicodedata

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Author, Book, BookAuthor
from app.models.download import Download
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


def _sanitize_for_path(name: str, max_length: int = 100) -> str:
    """Sanitize a string for use in file/directory names."""
    # Normalize unicode
    name = unicodedata.normalize("NFKD", name)
    # Remove characters that are problematic in filenames
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    # Collapse whitespace
    name = " ".join(name.split())
    # Trim to max length
    return name[:max_length].strip(". ")


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
    ) -> Download:
        dl = Download(
            source_type=source_type,
            source_url=source_url,
            book_id=book_id,
            status="pending",
            progress=0.0,
            target_path=target_filename,
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


async def _process_single(dl: Download, db: AsyncSession) -> None:
    """Download a single file with chunked streaming and progress updates."""
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

        # Post-download: rename and organize by author/title
        organized_path = await _organize_file(db, dl, final_path, download_dir)

        dl.status = "complete"
        dl.progress = 1.0
        dl.target_path = str(organized_path)
        await db.commit()
        await _broadcast_progress(dl)
        logger.info("Download complete: %s -> %s", dl.id, organized_path)

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
    """Rename and move downloaded file into Author/Title structure."""
    if not dl.book_id:
        return current_path

    book = await db.get(Book, dl.book_id)
    if not book:
        return current_path

    # Get first author name
    author_result = await db.execute(
        select(Author.name)
        .join(BookAuthor, Author.id == BookAuthor.author_id)
        .where(BookAuthor.book_id == dl.book_id)
        .limit(1)
    )
    author_row = author_result.first()
    author_name = _sanitize_for_path(author_row[0]) if author_row else "Unknown"
    title = _sanitize_for_path(book.title)

    ext = current_path.suffix
    new_filename = f"{author_name} - {title}{ext}"
    organized_dir = download_dir / author_name
    organized_dir.mkdir(parents=True, exist_ok=True)
    organized_path = organized_dir / new_filename

    # Verify the organized path stays inside download_dir
    if not str(organized_path.resolve()).startswith(str(download_dir.resolve())):
        logger.warning("Path traversal detected during organization, keeping original path")
        return current_path

    try:
        current_path.rename(organized_path)
        return organized_path
    except OSError:
        logger.warning("Failed to organize file, keeping at %s", current_path)
        return current_path


async def _broadcast_progress(dl: Download) -> None:
    await manager.broadcast({
        "type": "download_progress",
        "id": str(dl.id),
        "status": dl.status,
        "progress": dl.progress,
        "error": dl.error,
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
