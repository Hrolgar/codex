"""Download queue service with progress tracking."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.download import Download
from app.schemas.download import DownloadResponse
from app.services.settings_service import get_setting
from app.ws.manager import manager

logger = logging.getLogger(__name__)

# Throttle progress broadcasts to max once per 0.5s per download
_PROGRESS_INTERVAL = 0.5


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

    # Determine filename
    filename = dl.target_path or dl.source_url.rsplit("/", 1)[-1] or f"{dl.id}"
    temp_path = temp_dir / f"{dl.id}_{filename}"
    final_path = download_dir / filename

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
        dl.status = "complete"
        dl.progress = 1.0
        dl.target_path = str(final_path)
        await db.commit()
        await _broadcast_progress(dl)

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
                    await _process_single(dl, db)
        except Exception:
            logger.exception("Error in download queue processor")
        await asyncio.sleep(2)
