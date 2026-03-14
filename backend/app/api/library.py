import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Library
from app.schemas import LibraryCreate, LibraryResponse
from app.services.library_service import LibraryService
from app.services.scanner_service import run_scan

router = APIRouter()


@router.get("/", response_model=list[LibraryResponse])
async def list_libraries(db: AsyncSession = Depends(get_db)):
    svc = LibraryService(db)
    return await svc.get_libraries()


@router.post("/", response_model=LibraryResponse, status_code=201)
async def create_library(data: LibraryCreate, db: AsyncSession = Depends(get_db)):
    svc = LibraryService(db)
    return await svc.create_library(
        name=data.name, scanner_type=data.scanner_type, config=data.config
    )


@router.get("/stats")
async def library_stats(db: AsyncSession = Depends(get_db)):
    svc = LibraryService(db)
    return await svc.get_library_stats()


@router.get("/{library_id}", response_model=LibraryResponse)
async def get_library(library_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    library = await db.get(Library, library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    return library


@router.delete("/{library_id}", status_code=204)
async def delete_library(library_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    svc = LibraryService(db)
    if not await svc.delete_library(library_id):
        raise HTTPException(status_code=404, detail="Library not found")


@router.post("/{library_id}/scan", status_code=202)
async def trigger_scan(
    library_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    library = await db.get(Library, library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    if library.scan_status == "scanning":
        raise HTTPException(status_code=409, detail="Scan already in progress")
    background_tasks.add_task(run_scan, library_id)
    return {"status": "scan_started", "library_id": str(library_id)}
