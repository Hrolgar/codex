import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.matching import escape_like
from app.database import get_db
from app.models import Author, Book, BookAuthor, LibraryItem, Series, SeriesBook
from app.schemas.series import SeriesAuthor, SeriesBookItem, SeriesDetail, SeriesListItem

router = APIRouter()


@router.get("", response_model=list[SeriesListItem])
async def list_series(
    search: str | None = Query(None, description="Filter series by name"),
    db: AsyncSession = Depends(get_db),
):
    # Subquery for comma-joined author names per series
    author_names_sub = (
        select(func.string_agg(func.distinct(Author.name), ", "))
        .join(BookAuthor, Author.id == BookAuthor.author_id)
        .join(SeriesBook, SeriesBook.book_id == BookAuthor.book_id)
        .where(SeriesBook.series_id == Series.id)
        .correlate(Series)
        .scalar_subquery()
        .label("author_names")
    )

    stmt = (
        select(
            Series.id,
            Series.name,
            func.count(SeriesBook.book_id).label("book_count"),
            author_names_sub,
        )
        .join(SeriesBook, Series.id == SeriesBook.series_id)
        .group_by(Series.id)
    )

    if search:
        stmt = stmt.where(Series.name.ilike(f"%{escape_like(search)}%"))

    stmt = stmt.order_by(Series.name)

    result = await db.execute(stmt)
    return [
        SeriesListItem(
            id=row.id,
            name=row.name,
            book_count=row.book_count,
            author_names=row.author_names,
        )
        for row in result
    ]


@router.get("/{series_id}", response_model=SeriesDetail)
async def get_series(series_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    series = await db.get(Series, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    # First author subquery
    first_author = (
        select(Author.name)
        .join(BookAuthor, Author.id == BookAuthor.author_id)
        .where(BookAuthor.book_id == Book.id)
        .correlate(Book)
        .limit(1)
        .scalar_subquery()
        .label("author")
    )

    # Owned subquery: does this book have any library items?
    owned_subquery = (
        select(func.count(LibraryItem.id))
        .where(LibraryItem.book_id == Book.id)
        .correlate(Book)
        .scalar_subquery()
        .label("owned_count")
    )

    # Books in this series, ordered by position
    books_stmt = (
        select(
            Book.id,
            Book.title,
            first_author,
            Book.media_type,
            Book.cover_url,
            Book.isbn_13,
            Book.publish_year,
            SeriesBook.position,
            owned_subquery,
        )
        .join(SeriesBook, Book.id == SeriesBook.book_id)
        .where(SeriesBook.series_id == series_id)
        .order_by(SeriesBook.position)
    )
    books_result = await db.execute(books_stmt)
    books = [
        SeriesBookItem(
            id=row.id,
            title=row.title,
            author=row.author,
            media_type=row.media_type,
            cover_url=row.cover_url,
            isbn_13=row.isbn_13,
            publish_year=row.publish_year,
            position=row.position,
            owned=(row.owned_count or 0) > 0,
        )
        for row in books_result
    ]

    # Unique authors across all books in series
    authors_stmt = (
        select(Author.id, Author.name)
        .join(BookAuthor, Author.id == BookAuthor.author_id)
        .join(SeriesBook, SeriesBook.book_id == BookAuthor.book_id)
        .where(SeriesBook.series_id == series_id)
        .distinct()
        .order_by(Author.name)
    )
    authors_result = await db.execute(authors_stmt)
    authors = [SeriesAuthor(id=row.id, name=row.name) for row in authors_result]

    return SeriesDetail(
        id=series.id,
        name=series.name,
        books=books,
        authors=authors,
    )
