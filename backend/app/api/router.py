from fastapi import APIRouter

from app.api import books, library, system

api_router = APIRouter()
api_router.include_router(system.router, tags=["system"])
api_router.include_router(library.router, prefix="/libraries", tags=["libraries"])
api_router.include_router(books.router, prefix="/books", tags=["books"])
