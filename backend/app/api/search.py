"""External search API routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.search import SearchResult
from app.services.search_service import SearchService

router = APIRouter()


@router.get("", response_model=list[SearchResult])
async def search(
    q: str = Query(..., description="Search query"),
    media_type: str | None = Query(None, description="Filter: ebook or audiobook"),
    db: AsyncSession = Depends(get_db),
):
    svc = SearchService(db)
    return await svc.search(q, media_type)
