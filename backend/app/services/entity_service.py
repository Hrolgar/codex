"""Get-or-create helpers for authors and series to prevent duplicates."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Author, BookAuthor, Series, SeriesBook


async def get_or_create_author(db: AsyncSession, name: str) -> Author:
    """Return existing author by exact name match, or create a new one."""
    result = await db.execute(select(Author).where(Author.name == name))
    author = result.scalar_one_or_none()
    if not author:
        author = Author(name=name)
        db.add(author)
        await db.flush()
    return author


async def link_book_author(
    db: AsyncSession, book_id: uuid.UUID, author_id: uuid.UUID, role: str = "author"
) -> None:
    """Link a book to an author if not already linked."""
    result = await db.execute(
        select(BookAuthor).where(
            BookAuthor.book_id == book_id, BookAuthor.author_id == author_id
        )
    )
    if not result.scalar_one_or_none():
        db.add(BookAuthor(book_id=book_id, author_id=author_id, role=role))


async def get_or_create_series(db: AsyncSession, name: str) -> Series:
    """Return existing series by exact name match, or create a new one."""
    result = await db.execute(select(Series).where(Series.name == name))
    series = result.scalar_one_or_none()
    if not series:
        series = Series(name=name)
        db.add(series)
        await db.flush()
    return series


async def link_book_series(
    db: AsyncSession, book_id: uuid.UUID, series_id: uuid.UUID, position: float = 0.0
) -> None:
    """Link a book to a series if not already linked."""
    result = await db.execute(
        select(SeriesBook).where(
            SeriesBook.book_id == book_id, SeriesBook.series_id == series_id
        )
    )
    if not result.scalar_one_or_none():
        db.add(SeriesBook(book_id=book_id, series_id=series_id, position=position))
