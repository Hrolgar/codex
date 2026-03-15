"""External search API routes."""
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.search import SearchResult
from app.services.search_service import SearchService
from app.services.settings_service import get_setting

router = APIRouter()


@router.get("/indexers")
async def get_prowlarr_indexers(db: AsyncSession = Depends(get_db)):
    """Fetch configured indexers from Prowlarr."""
    url = await get_setting(db, "prowlarr.url")
    key = await get_setting(db, "prowlarr.api_key")
    if not url or not key:
        raise HTTPException(status_code=400, detail="Prowlarr not configured")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{url.rstrip('/')}/api/v1/indexer",
            headers={"X-Api-Key": key},
        )
        resp.raise_for_status()
        return [
            {"id": i["id"], "name": i["name"], "protocol": i["protocol"]}
            for i in resp.json()
        ]


@router.get("", response_model=list[SearchResult])
async def search(
    q: str = Query(..., description="Search query"),
    media_type: str | None = Query(None, description="Filter: ebook or audiobook"),
    db: AsyncSession = Depends(get_db),
):
    svc = SearchService(db)
    return await svc.search(q, media_type)
