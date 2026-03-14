import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Author, Book, BookAuthor, Series, SeriesBook
from app.schemas.author import AuthorDetail, AuthorListItem, AuthorSeriesBrief
from app.schemas.book import BookListItem

router = APIRouter()


@router.get("", response_model=list[AuthorListItem])
async def list_authors(
    search: str | None = Query(None, description="Filter authors by name"),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(
            Author.id,
            Author.name,
            Author.sort_name,
            func.count(BookAuthor.book_id).label("book_count"),
        )
        .join(BookAuthor, Author.id == BookAuthor.author_id)
        .group_by(Author.id)
    )

    if search:
        stmt = stmt.where(Author.name.ilike(f"%{search}%"))

    stmt = stmt.order_by(func.coalesce(Author.sort_name, Author.name))

    result = await db.execute(stmt)
    return [
        AuthorListItem(
            id=row.id,
            name=row.name,
            sort_name=row.sort_name,
            book_count=row.book_count,
        )
        for row in result
    ]


@router.get("/{author_id}", response_model=AuthorDetail)
async def get_author(author_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    author = await db.get(Author, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    # Get series this author contributes to, with book counts
    series_stmt = (
        select(
            Series.id,
            Series.name,
            func.count(SeriesBook.book_id).label("book_count"),
        )
        .join(SeriesBook, Series.id == SeriesBook.series_id)
        .join(BookAuthor, BookAuthor.book_id == SeriesBook.book_id)
        .where(BookAuthor.author_id == author_id)
        .group_by(Series.id)
        .order_by(Series.name)
    )
    series_result = await db.execute(series_stmt)
    series = [
        AuthorSeriesBrief(id=row.id, name=row.name, book_count=row.book_count)
        for row in series_result
    ]

    # Get series book IDs so we can exclude them for standalone books
    series_book_ids_stmt = (
        select(SeriesBook.book_id)
        .join(BookAuthor, BookAuthor.book_id == SeriesBook.book_id)
        .where(BookAuthor.author_id == author_id)
    )

    # First author subquery for display
    first_author = (
        select(Author.name)
        .join(BookAuthor, Author.id == BookAuthor.author_id)
        .where(BookAuthor.book_id == Book.id)
        .correlate(Book)
        .limit(1)
        .scalar_subquery()
        .label("author")
    )

    standalone_stmt = (
        select(
            Book.id,
            Book.title,
            first_author,
            Book.media_type,
            Book.cover_url,
            Book.isbn_13,
            Book.publish_year,
        )
        .join(BookAuthor, Book.id == BookAuthor.book_id)
        .where(BookAuthor.author_id == author_id)
        .where(Book.id.not_in(series_book_ids_stmt))
        .order_by(Book.title)
    )
    standalone_result = await db.execute(standalone_stmt)
    standalone_books = [
        BookListItem(
            id=row.id,
            title=row.title,
            author=row.author,
            media_type=row.media_type,
            cover_url=row.cover_url,
            isbn_13=row.isbn_13,
            publish_year=row.publish_year,
        )
        for row in standalone_result
    ]

    return AuthorDetail(
        id=author.id,
        name=author.name,
        sort_name=author.sort_name,
        series=series,
        standalone_books=standalone_books,
    )
