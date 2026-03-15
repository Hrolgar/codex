import asyncio
import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.root_folder import RootFolder
from app.services.scanner_service import run_scan

logger = logging.getLogger(__name__)

router = APIRouter()

# Keep references to background tasks to prevent garbage collection
_background_tasks: set = set()

def _validate_root_folder_path(path: str) -> None:
    """Validate that a root folder path is absolute and exists."""
    pass  # Path existence is checked separately in the create endpoint


# --- Schemas ---

class RootFolderCreate(BaseModel):
    name: str
    path: str
    media_type: str
    default: bool = False


class RootFolderUpdate(BaseModel):
    name: str | None = None
    default: bool | None = None


class RootFolderResponse(BaseModel):
    id: uuid.UUID
    name: str
    path: str
    media_type: str
    default: bool
    scan_status: str = "idle"
    last_scan_at: datetime | None = None
    free_space: int | None = None
    total_space: int | None = None

    model_config = {"from_attributes": True}


def _get_disk_usage(path: str) -> tuple[int | None, int | None]:
    """Return (total, free) bytes for a path, or (None, None) if unavailable."""
    try:
        usage = shutil.disk_usage(path)
        return usage.total, usage.free
    except (OSError, FileNotFoundError):
        return None, None


class BrowseDirectoryEntry(BaseModel):
    name: str
    path: str


class BrowseResponse(BaseModel):
    current_path: str
    parent: str | None
    directories: list[BrowseDirectoryEntry]


_HIDDEN_PATHS = frozenset({
    "/proc", "/sys", "/dev", "/usr", "/var", "/bin", "/sbin",
    "/root", "/tmp", "/etc", "/lib", "/lib64", "/opt", "/run",
    "/srv", "/boot", "/app",
})


def _is_blocked_path(real_path: str) -> bool:
    """Hide system directories from the browse listing."""
    # Check if the path itself or its top-level directory is in the blocklist
    if real_path in _HIDDEN_PATHS:
        return True
    # Check if path is under a hidden top-level directory
    parts = real_path.split("/")
    if len(parts) >= 2 and f"/{parts[1]}" in _HIDDEN_PATHS:
        return True
    return False


# --- Endpoints ---

@router.get("/browse", response_model=BrowseResponse)
async def browse_directories(path: str = "/"):
    """List directories at the given path for the folder browser UI."""
    real = os.path.realpath(path)

    if not os.path.isdir(real):
        raise HTTPException(status_code=404, detail="Path does not exist or is not a directory.")

    parent = os.path.dirname(real) if real != "/" else None

    directories: list[BrowseDirectoryEntry] = []
    try:
        with os.scandir(real) as entries:
            for entry in entries:
                try:
                    if not entry.is_dir(follow_symlinks=True):
                        continue
                    entry_real = os.path.realpath(entry.path)
                    if _is_blocked_path(entry_real):
                        continue
                    directories.append(BrowseDirectoryEntry(name=entry.name, path=entry_real))
                except (PermissionError, OSError):
                    continue
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied reading this directory.")

    directories.sort(key=lambda d: d.name.lower())

    return BrowseResponse(
        current_path=real,
        parent=parent,
        directories=directories,
    )


@router.get("", response_model=list[RootFolderResponse])
async def list_root_folders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RootFolder).order_by(RootFolder.media_type, RootFolder.name))
    folders = result.scalars().all()
    out = []
    for f in folders:
        total, free = _get_disk_usage(f.path)
        out.append(RootFolderResponse(
            id=f.id,
            name=f.name,
            path=f.path,
            media_type=f.media_type,
            default=f.default,
            scan_status=f.scan_status,
            last_scan_at=f.last_scan_at,
            free_space=free,
            total_space=total,
        ))
    return out


@router.post("", response_model=RootFolderResponse, status_code=201)
async def create_root_folder(data: RootFolderCreate, db: AsyncSession = Depends(get_db)):
    if data.media_type not in ("ebook", "audiobook", "comic"):
        raise HTTPException(status_code=400, detail="media_type must be ebook, audiobook, or comic")

    p = Path(data.path)
    if not p.is_absolute():
        raise HTTPException(status_code=400, detail="Path must be absolute")
    _validate_root_folder_path(data.path)
    if not p.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Path does not exist or is not a directory: {data.path}. "
                   "Mount it as a Docker volume first.",
        )

    # If this is set as default, unset any other defaults for this media type
    if data.default:
        existing = await db.execute(
            select(RootFolder).where(RootFolder.media_type == data.media_type, RootFolder.default.is_(True))
        )
        for row in existing.scalars().all():
            row.default = False

    folder = RootFolder(
        name=data.name,
        path=data.path,
        media_type=data.media_type,
        default=data.default,
    )
    db.add(folder)
    await db.commit()
    await db.refresh(folder)

    # Auto-trigger a scan in the background
    task = asyncio.create_task(run_scan(folder.id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    total, free = _get_disk_usage(folder.path)
    return RootFolderResponse(
        id=folder.id,
        name=folder.name,
        path=folder.path,
        media_type=folder.media_type,
        default=folder.default,
        scan_status=folder.scan_status,
        last_scan_at=folder.last_scan_at,
        free_space=free,
        total_space=total,
    )


@router.post("/scan-all", status_code=202)
async def trigger_scan_all(db: AsyncSession = Depends(get_db)):
    """Trigger an immediate rescan of ALL root folders (sequential)."""
    result = await db.execute(select(RootFolder))
    folders = result.scalars().all()
    if not folders:
        raise HTTPException(status_code=404, detail="No root folders configured")

    async def _scan_all_sequential(folder_ids: list):
        for fid in folder_ids:
            try:
                await run_scan(fid)
            except Exception:
                logger.warning("scan-all: failed for folder %s", fid, exc_info=True)

    folder_ids = [f.id for f in folders]
    task = asyncio.create_task(_scan_all_sequential(folder_ids))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"status": "scanning", "folder_count": len(folder_ids)}


@router.post("/{folder_id}/scan", status_code=202)
async def trigger_scan(folder_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Manually trigger a re-scan of a root folder."""
    folder = await db.get(RootFolder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Root folder not found")
    if folder.scan_status == "scanning":
        raise HTTPException(status_code=409, detail="Scan already in progress")
    task = asyncio.create_task(run_scan(folder.id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"status": "scanning"}


@router.put("/{folder_id}", response_model=RootFolderResponse)
async def update_root_folder(
    folder_id: uuid.UUID, data: RootFolderUpdate, db: AsyncSession = Depends(get_db)
):
    folder = await db.get(RootFolder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Root folder not found")

    if data.name is not None:
        folder.name = data.name

    if data.default is not None:
        if data.default:
            # Unset other defaults for this media type
            existing = await db.execute(
                select(RootFolder).where(
                    RootFolder.media_type == folder.media_type,
                    RootFolder.default.is_(True),
                    RootFolder.id != folder.id,
                )
            )
            for row in existing.scalars().all():
                row.default = False
        folder.default = data.default

    await db.commit()
    await db.refresh(folder)

    total, free = _get_disk_usage(folder.path)
    return RootFolderResponse(
        id=folder.id,
        name=folder.name,
        path=folder.path,
        media_type=folder.media_type,
        default=folder.default,
        scan_status=folder.scan_status,
        last_scan_at=folder.last_scan_at,
        free_space=free,
        total_space=total,
    )


@router.delete("/{folder_id}", status_code=204)
async def delete_root_folder(folder_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    folder = await db.get(RootFolder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Root folder not found")
    # Warn if this is the last root folder for its media type
    count_result = await db.execute(
        select(func.count()).select_from(RootFolder).where(RootFolder.media_type == folder.media_type)
    )
    if count_result.scalar() == 1:
        logger.warning(
            "Deleting the only root folder '%s' for media type '%s'",
            folder.name, folder.media_type,
        )
    await db.delete(folder)
    await db.commit()
