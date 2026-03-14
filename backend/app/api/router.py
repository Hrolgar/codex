from fastapi import APIRouter

from app.api import authors, books, dev, library, series, system

api_router = APIRouter()
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(library.router, prefix="/libraries", tags=["libraries"])
api_router.include_router(books.router, prefix="/books", tags=["books"])
api_router.include_router(authors.router, prefix="/authors", tags=["authors"])
api_router.include_router(series.router, prefix="/series", tags=["series"])
api_router.include_router(dev.router, prefix="/dev", tags=["dev"])
