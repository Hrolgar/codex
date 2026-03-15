import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import logging
from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.database import async_session, engine
from app.models import Base

logger = logging.getLogger(__name__)

STATIC_DIR = Path("/app/static")


async def _add_column_if_missing(conn, table: str, column: str, col_type: str, default: str | None = None):
    """Add a column to an existing table if it doesn't already exist."""
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
        # Migrate existing databases: add new columns
        await _add_column_if_missing(conn, "books", "read_status", "VARCHAR(20)", "'unread'")
        await _add_column_if_missing(conn, "books", "date_read", "TIMESTAMPTZ")

    # Store session factory on app state for WebSocket access
    app.state.db_session = async_session

    # Start background download queue processor
    from app.services.download_service import process_download_queue
    task = asyncio.create_task(process_download_queue())

    # Periodic auto-download check (every 6 hours)
    async def _periodic_tasks():
        while True:
            await asyncio.sleep(6 * 3600)  # 6 hours
            try:
                async with async_session() as db:
                    from app.services.auto_download_service import check_wishlist_for_downloads
                    count = await check_wishlist_for_downloads(db)
                    if count:
                        logger.info(f'Auto-download: started {count} downloads')
            except Exception as e:
                logger.warning(f'Periodic task error: {e}')

    periodic_task = asyncio.create_task(_periodic_tasks())
    yield
    task.cancel()
    periodic_task.cancel()
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
