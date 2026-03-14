import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Library
from app.schemas import LibraryCreate, LibraryResponse
from app.services.scanner_service import run_scan

router = APIRouter()


@router.get("/", response_model=list[LibraryResponse])
async def list_libraries(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Library).order_by(Library.name))
    return result.scalars().all()


@router.post("/", response_model=LibraryResponse, status_code=201)
async def create_library(data: LibraryCreate, db: AsyncSession = Depends(get_db)):
    library = Library(name=data.name, scanner_type=data.scanner_type, config=data.config)
    db.add(library)
    await db.commit()
    await db.refresh(library)
    return library


@router.get("/{library_id}", response_model=LibraryResponse)
async def get_library(library_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    library = await db.get(Library, library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    return library


@router.delete("/{library_id}", status_code=204)
async def delete_library(library_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    library = await db.get(Library, library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    await db.delete(library)
    await db.commit()


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
