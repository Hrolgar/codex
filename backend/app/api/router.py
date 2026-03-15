from fastapi import APIRouter

from app.api import authors, books, dev, downloads, library, notifications, search, series, system, wishlist

api_router = APIRouter()
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(library.router, prefix="/libraries", tags=["libraries"])
api_router.include_router(books.router, prefix="/books", tags=["books"])
api_router.include_router(authors.router, prefix="/authors", tags=["authors"])
api_router.include_router(series.router, prefix="/series", tags=["series"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(downloads.router, prefix="/downloads", tags=["downloads"])
api_router.include_router(wishlist.router, prefix="/wishlist", tags=["wishlist"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(dev.router, prefix="/dev", tags=["dev"])
