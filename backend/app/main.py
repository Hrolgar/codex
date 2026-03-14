import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.database import async_session, engine
from app.models import Base

STATIC_DIR = Path("/app/static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Store session factory on app state for WebSocket access
    app.state.db_session = async_session

    # Start background download queue processor
    from app.services.download_service import process_download_queue
    task = asyncio.create_task(process_download_queue())
    yield
    task.cancel()
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
