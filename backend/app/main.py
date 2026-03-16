import asyncio
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

import logging
logging.basicConfig(level=getattr(logging, os.environ.get('LOG_LEVEL', 'WARNING').upper(), logging.WARNING))
from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.database import async_session, engine
from app.models import Base

logger = logging.getLogger(__name__)

STATIC_DIR = Path("/app/static")


def _validate_identifier(name: str) -> str:
    """Validate that a SQL identifier contains only safe characters."""
    if not re.match(r'^[a-z_][a-z0-9_]*$', name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name


async def _add_column_if_missing(conn, table: str, column: str, col_type: str, default: str | None = None):
    """Add a column to an existing table if it doesn't already exist."""
    _validate_identifier(table)
    _validate_identifier(column)
    _validate_identifier(col_type.split('(')[0].strip().lower())  # validate base type name
    from sqlalchemy import text
    result = await conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column"
    ), {"table": table, "column": column})
    if not result.first():
        default_clause = f" DEFAULT {default}" if default else ""
        await conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}'))


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add columns that may be missing from older DB schemas
        await _add_column_if_missing(conn, 'books', 'hardcover_slug', 'VARCHAR')
        await _add_column_if_missing(conn, 'root_folders', 'scan_status', 'VARCHAR(20)', "'idle'")
        await _add_column_if_missing(conn, 'root_folders', 'last_scan_at', 'TIMESTAMP')
        await _add_column_if_missing(conn, 'downloads', 'root_folder_id', 'UUID')
        await _add_column_if_missing(conn, 'downloads', 'is_upgrade', 'BOOLEAN', "'false'")

    # Store session factory on app state for WebSocket access
    app.state.db_session = async_session

    # Start background download queue processor
    from app.services.download_service import process_download_queue
    task = asyncio.create_task(process_download_queue())

    # --- Periodic background tasks ---

    async def _get_interval(key: str, default: float) -> float:
        """Read an interval setting (in hours) from the DB, fall back to default."""
        try:
            async with async_session() as db:
                from app.services.settings_service import get_setting
                val = await get_setting(db, key)
                if val:
                    return max(float(val), 0.5)  # minimum 30 minutes
        except Exception:
            pass
        return default

    async def _auto_download_loop():
        """Periodically check wishlist for auto-downloads."""
        while True:
            interval = await _get_interval("auto_download.interval_hours", 6)
            await asyncio.sleep(interval * 3600)
            try:
                async with async_session() as db:
                    from app.services.auto_download_service import check_wishlist_for_downloads
                    count = await check_wishlist_for_downloads(db)
                    if count:
                        logger.info("Auto-download: started %d downloads", count)
            except Exception:
                logger.warning("Auto-download periodic task error", exc_info=True)

    async def _catalog_refresh_loop():
        """Periodically refresh all monitored authors."""
        while True:
            interval = await _get_interval("catalog.refresh_interval_hours", 24)
            await asyncio.sleep(interval * 3600)
            try:
                async with async_session() as db:
                    from sqlalchemy import select
                    from app.models import Author
                    from app.services.catalog_service import refresh_author_catalog
                    from app.services.notification_service import notify

                    result = await db.execute(
                        select(Author).where(Author.monitored.is_(True))
                    )
                    authors = result.scalars().all()
                    total_added = 0
                    for author in authors:
                        try:
                            added = await refresh_author_catalog(db, author)
                            if added:
                                total_added += added
                                await notify(
                                    db,
                                    title="New Books Found",
                                    message=f"Found {added} new book(s) for {author.name}",
                                    notification_type="info",
                                )
                        except Exception:
                            logger.warning("Catalog refresh failed for %s", author.name, exc_info=True)
                    if total_added:
                        logger.info("Catalog refresh: added %d books total", total_added)
            except Exception:
                logger.warning("Catalog refresh periodic task error", exc_info=True)

    async def _root_folder_scan_loop():
        """Periodically rescan all root folders."""
        while True:
            interval = await _get_interval("scan.interval_hours", 24)
            await asyncio.sleep(interval * 3600)
            try:
                async with async_session() as db:
                    from sqlalchemy import select
                    from app.models.root_folder import RootFolder
                    from app.services.scanner_service import run_scan

                    result = await db.execute(select(RootFolder))
                    folders = result.scalars().all()
                    logger.info("Auto-rescan: starting scan of %d root folder(s)", len(folders))
                    for folder in folders:
                        try:
                            logger.info("Auto-rescan: scanning '%s' (%s)", folder.name, folder.id)
                            await run_scan(folder.id)
                            logger.info("Auto-rescan: completed '%s'", folder.name)
                        except Exception:
                            logger.warning("Auto-rescan: failed for '%s'", folder.name, exc_info=True)
                    logger.info("Auto-rescan: finished all folders")
            except Exception:
                logger.warning("Auto-rescan periodic task error", exc_info=True)

    auto_dl_task = asyncio.create_task(_auto_download_loop())
    catalog_task = asyncio.create_task(_catalog_refresh_loop())
    scan_task = asyncio.create_task(_root_folder_scan_loop())

    yield
    task.cancel()
    auto_dl_task.cancel()
    catalog_task.cancel()
    scan_task.cancel()
    await engine.dispose()


app = FastAPI(title="Codex", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# WebSocket endpoint for download progress
from app.api.downloads import ws_downloads  # noqa: E402


@app.websocket("/api/ws/downloads")
async def websocket_downloads(websocket: WebSocket):
    await ws_downloads(websocket)


# Serve frontend: static assets at their real paths, SPA fallback for client-side routes
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(request: Request, full_path: str):
        """Serve index.html for all non-API routes (SPA client-side routing)."""
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
