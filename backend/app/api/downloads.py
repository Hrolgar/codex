"""Download queue API routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.download import DownloadCreate, DownloadResponse
from app.services.download_service import DownloadService, validate_download_url
from app.ws.manager import manager

router = APIRouter()


@router.get("", response_model=list[DownloadResponse])
async def list_downloads(status: str | None = None, db: AsyncSession = Depends(get_db)):
    svc = DownloadService(db)
    return await svc.get_downloads(status=status)


@router.post("", response_model=DownloadResponse, status_code=201)
async def enqueue_download(body: DownloadCreate, db: AsyncSession = Depends(get_db)):
    validate_download_url(body.source_url)
    svc = DownloadService(db)
    dl = await svc.enqueue(
        source_url=body.source_url,
        source_type=body.source_type,
        book_id=body.book_id,
        target_filename=body.filename,
        root_folder_id=body.root_folder_id,
        is_upgrade=body.is_upgrade,
    )
    return DownloadResponse.model_validate(dl)


@router.delete("/{download_id}")
async def delete_download(download_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    svc = DownloadService(db)
    ok = await svc.cancel(download_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Download not found")
    return {"ok": True}


@router.post("/{download_id}/retry", response_model=DownloadResponse)
async def retry_download(download_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    svc = DownloadService(db)
    ok = await svc.retry(download_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Download not found or not retryable")
    dl = await svc.get_downloads()
    match = next((d for d in dl if d.id == download_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Download not found")
    return match


# WebSocket endpoint — mounted separately in main.py
async def ws_downloads(websocket: WebSocket):
    """WebSocket endpoint for real-time download progress."""
    await manager.connect(websocket)
    try:
        # Send current queue state on connect
        async with websocket.app.state.db_session() as db:
            svc = DownloadService(db)
            downloads = await svc.get_downloads()
            await websocket.send_json({
                "type": "queue_state",
                "downloads": [d.model_dump(mode="json") for d in downloads],
            })
        # Keep alive — wait for disconnect
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
