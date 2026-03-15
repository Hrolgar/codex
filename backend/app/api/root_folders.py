import logging
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.root_folder import RootFolder

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed path prefixes for root folders
_ALLOWED_PREFIXES = ('/books', '/downloads', '/data', '/mnt', '/media', '/library', '/storage')
_BLOCKED_PREFIXES = ('/app', '/proc', '/sys', '/etc', '/dev', '/usr', '/var', '/bin', '/sbin', '/root', '/tmp')


def _validate_root_folder_path(path: str) -> None:
    """Validate that a root folder path doesn't point to sensitive directories."""
    real = os.path.realpath(path)
    for blocked in _BLOCKED_PREFIXES:
        if real == blocked or real.startswith(blocked + '/'):
            raise HTTPException(
                status_code=400,
                detail=f"Path '{path}' resolves to a restricted system directory.",
            )
    if not any(real == allowed or real.startswith(allowed + '/') for allowed in _ALLOWED_PREFIXES):
        raise HTTPException(
            status_code=400,
            detail=f"Path must start with one of: {', '.join(_ALLOWED_PREFIXES)}",
        )


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


def _is_blocked_path(real_path: str) -> bool:
    """Check if a resolved path falls under a blocked prefix."""
    for blocked in _BLOCKED_PREFIXES:
        if real_path == blocked or real_path.startswith(blocked + '/'):
            return True
    return False


# --- Endpoints ---

@router.get("/browse", response_model=BrowseResponse)
async def browse_directories(path: str = "/"):
    """List directories at the given path for the folder browser UI."""
    real = os.path.realpath(path)

    if _is_blocked_path(real):
        raise HTTPException(status_code=403, detail="Access to this path is restricted.")

    if not os.path.isdir(real):
        raise HTTPException(status_code=404, detail="Path does not exist or is not a directory.")

    parent = os.path.dirname(real) if real != "/" else None
    if parent is not None and _is_blocked_path(parent):
        parent = None

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

    total, free = _get_disk_usage(folder.path)
    return RootFolderResponse(
        id=folder.id,
        name=folder.name,
        path=folder.path,
        media_type=folder.media_type,
        default=folder.default,
        free_space=free,
        total_space=total,
    )


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
