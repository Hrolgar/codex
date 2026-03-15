"""Auto-download service — periodically checks wishlist items and enqueues downloads."""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wishlist import WishlistItem
from app.services.settings_service import get_setting

logger = logging.getLogger(__name__)


async def check_wishlist_for_downloads(db: AsyncSession) -> int:
    """Check wishlist items with auto_download=True and search for them via Prowlarr.

    For each matching item:
    1. Search Prowlarr for the title/author
    2. Pick the best result
    3. Update status to 'found', then enqueue download and set 'downloading'

    Returns the number of downloads started.
    """
    result = await db.execute(
        select(WishlistItem).where(
            WishlistItem.auto_download.is_(True),
            WishlistItem.status == "waiting",
        )
    )
    items = result.scalars().all()
    if not items:
        return 0

    prowlarr_url = await get_setting(db, "prowlarr.url")
    prowlarr_key = await get_setting(db, "prowlarr.api_key")
    if not prowlarr_url or not prowlarr_key:
        logger.info("Prowlarr not configured, skipping auto-download check")
        return 0

    from app.services.search_service import SearchService
    from app.services.download_service import DownloadService

    search_svc = SearchService(db)
    dl_svc = DownloadService(db)

    downloaded = 0
    for item in items:
        try:
            query = item.search_title or ""
            if item.search_author:
                query = f"{query} {item.search_author}".strip()
            if not query:
                continue

            results = await search_svc.search(query)
            if not results:
                continue

            # Pick best result (first non-owned match with a download URL)
            best = None
            for r in results:
                if r.download_url:
                    best = r
                    break
            if not best:
                continue

            # Update status to 'found'
            item.status = "found"
            await db.commit()

            # Enqueue download
            await dl_svc.enqueue(
                source_url=best.download_url,
                source_type=best.source or "prowlarr",
                book_id=item.book_id,
            )

            # Update status to 'downloading'
            item.status = "downloading"
            await db.commit()
            downloaded += 1
            logger.info("Auto-download started for wishlist item: %s", item.search_title)

            # Send notification
            try:
                from app.services.notification_service import notify
                await notify(
                    db,
                    title="Wishlist Item Found",
                    message=f"Found and started download for: {item.search_title}",
                    notification_type="success",
                )
            except Exception:
                logger.debug("Could not send notification for wishlist auto-download")

        except Exception as e:
            logger.warning("Auto-download failed for %s: %s", item.search_title, e)

    return downloaded
