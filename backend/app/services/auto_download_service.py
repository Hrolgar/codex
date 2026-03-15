import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.wishlist import WishlistItem
from app.services.settings_service import get_setting

logger = logging.getLogger(__name__)

async def check_wishlist_for_downloads(db: AsyncSession) -> int:
    """Check wishlist items with auto_download=True and search for them via Prowlarr."""
    result = await db.execute(
        select(WishlistItem).where(
            WishlistItem.auto_download == True,
            WishlistItem.status == 'waiting'
        )
    )
    items = result.scalars().all()
    if not items:
        return 0

    prowlarr_url = await get_setting(db, 'prowlarr.url')
    prowlarr_key = await get_setting(db, 'prowlarr.api_key')
    if not prowlarr_url or not prowlarr_key:
        logger.info('Prowlarr not configured, skipping auto-download check')
        return 0

    from app.services.search_service import SearchService
    search_svc = SearchService(db)

    downloaded = 0
    for item in items:
        try:
            query = item.search_title
            if item.search_author:
                query = f'{item.search_title} {item.search_author}'

            results = await search_svc.search(query)
            if results:
                # Pick best result (first match)
                best = results[0]
                from app.services.download_service import DownloadService
                dl_svc = DownloadService(db)
                await dl_svc.enqueue(
                    url=best.get('download_url', best.get('guid', '')),
                    book_id=item.book_id
                )
                item.status = 'downloading'
                await db.commit()
                downloaded += 1
                logger.info(f'Auto-download started for wishlist item: {item.search_title}')
        except Exception as e:
            logger.warning(f'Auto-download failed for {item.search_title}: {e}')

    return downloaded
