"""Search service — orchestrates Prowlarr search + duplicate detection."""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.search import SearchResult
from app.search.prowlarr import search_prowlarr
from app.services.duplicate_service import check_duplicate
from app.services.settings_service import get_setting

logger = logging.getLogger(__name__)


def _dedup_key(r: SearchResult) -> str:
    """Key for deduplication: ISBN if available, else normalized title+author."""
    if r.isbn:
        return f"isbn:{r.isbn}"
    title = (r.title or "").strip().lower()
    author = (r.author or "").strip().lower()
    return f"ta:{title}|{author}"


class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self,
        query: str,
        media_type: str | None = None,
    ) -> list[SearchResult]:
        """Search external sources and enrich with duplicate info."""
        results = await self._fetch_prowlarr(query, media_type)

        # Deduplicate — keep first occurrence (Prowlarr returns most relevant first)
        seen: dict[str, SearchResult] = {}
        for r in results:
            key = _dedup_key(r)
            if key not in seen:
                seen[key] = r

        deduped = list(seen.values())

        # Enrich with duplicate/ownership info
        enriched = []
        for r in deduped:
            try:
                is_dup, confidence, book_id = await check_duplicate(
                    self.db, r.title, r.author, r.isbn
                )
                r.owned = is_dup
                r.match_confidence = confidence
                if book_id:
                    r.book_id = book_id
            except Exception:
                logger.exception("Duplicate check failed for '%s'", r.title)
            enriched.append(r)

        # Sort: owned first, then by match_confidence descending
        enriched.sort(key=lambda r: (not r.owned, -r.match_confidence))
        return enriched

    async def _fetch_prowlarr(
        self, query: str, media_type: str | None
    ) -> list[SearchResult]:
        """Fetch results from Prowlarr if configured."""
        url = await get_setting(self.db, "prowlarr.url")
        api_key = await get_setting(self.db, "prowlarr.api_key")
        if not url or not api_key:
            return []

        selected_indexers = await get_setting(self.db, "prowlarr.selected_indexers")

        try:
            return await search_prowlarr(
                url, api_key, query, media_type, selected_indexers
            )
        except Exception:
            logger.exception("Prowlarr search failed")
            return []
