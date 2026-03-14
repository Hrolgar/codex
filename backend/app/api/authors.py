import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.matching import escape_like
from app.database import async_session, get_db
from app.models import Author, Book, BookAuthor, LibraryItem, Series, SeriesBook
from app.schemas.author import (
    AuthorBookListItem,
    AuthorCreate,
    AuthorDetail,
    AuthorListItem,
    AuthorSeriesBrief,
)

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
            Author.monitored,
            func.count(BookAuthor.book_id).label("book_count"),
        )
        .join(BookAuthor, Author.id == BookAuthor.author_id)
        .group_by(Author.id)
    )

    if search:
        stmt = stmt.where(Author.name.ilike(f"%{escape_like(search)}%"))

    stmt = stmt.order_by(func.coalesce(Author.sort_name, Author.name))

    result = await db.execute(stmt)
    return [
        AuthorListItem(
            id=row.id,
            name=row.name,
            sort_name=row.sort_name,
            monitored=row.monitored,
            book_count=row.book_count,
        )
        for row in result
    ]


@router.get("/{author_id}", response_model=AuthorDetail)
async def get_author(author_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    author = await db.get(Author, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    # Get series this author contributes to, with book counts and owned counts
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
    series_rows = list(series_result)

    # For each series, count how many books are "owned" (have at least one LibraryItem)
    series_list = []
    for row in series_rows:
        owned_stmt = (
            select(func.count(func.distinct(SeriesBook.book_id)))
            .join(BookAuthor, BookAuthor.book_id == SeriesBook.book_id)
            .join(LibraryItem, LibraryItem.book_id == SeriesBook.book_id)
            .where(
                SeriesBook.series_id == row.id,
                BookAuthor.author_id == author_id,
            )
        )
        owned_result = await db.execute(owned_stmt)
        owned_count = owned_result.scalar() or 0

        series_list.append(
            AuthorSeriesBrief(
                id=row.id,
                name=row.name,
                book_count=row.book_count,
                owned_count=owned_count,
            )
        )

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

    # Owned subquery: does this book have any library items?
    owned_subquery = (
        select(func.count(LibraryItem.id))
        .where(LibraryItem.book_id == Book.id)
        .correlate(Book)
        .scalar_subquery()
        .label("owned_count")
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
            owned_subquery,
        )
        .join(BookAuthor, Book.id == BookAuthor.book_id)
        .where(BookAuthor.author_id == author_id)
        .where(Book.id.not_in(series_book_ids_stmt))
        .order_by(Book.title)
    )
    standalone_result = await db.execute(standalone_stmt)
    standalone_books = [
        AuthorBookListItem(
            id=row.id,
            title=row.title,
            author=row.author,
            media_type=row.media_type,
            cover_url=row.cover_url,
            isbn_13=row.isbn_13,
            publish_year=row.publish_year,
            owned=(row.owned_count or 0) > 0,
        )
        for row in standalone_result
    ]

    return AuthorDetail(
        id=author.id,
        name=author.name,
        sort_name=author.sort_name,
        monitored=author.monitored,
        openlibrary_key=author.openlibrary_key,
        bio=author.bio,
        photo_url=author.photo_url,
        series=series_list,
        standalone_books=standalone_books,
    )


@router.post("", response_model=AuthorDetail)
async def create_monitored_author(
    body: AuthorCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Add a monitored author by name. Triggers catalog fetch as background task."""
    from app.services.entity_service import get_or_create_author

    author = await get_or_create_author(db, body.name)
    author.monitored = True
    await db.commit()

    # Kick off catalog fetch in background
    async def _fetch_catalog(author_id: uuid.UUID, author_name: str):
        from app.services.catalog_service import add_author

        async with async_session() as bg_db:
            # Re-fetch author in this session
            a = await bg_db.get(Author, author_id)
            if not a:
                return
            try:
                await add_author(bg_db, author_name)
            except Exception:
                import logging
                logging.getLogger(__name__).warning(
                    "Background catalog fetch failed for %s", author_name, exc_info=True
                )

    background_tasks.add_task(_fetch_catalog, author.id, body.name)

    return AuthorDetail(
        id=author.id,
        name=author.name,
        sort_name=author.sort_name,
        monitored=author.monitored,
        openlibrary_key=author.openlibrary_key,
        bio=author.bio,
        photo_url=author.photo_url,
        series=[],
        standalone_books=[],
    )


@router.post("/{author_id}/refresh")
async def refresh_author(
    author_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Re-fetch catalog for an author (get new books). Runs as background task."""
    author = await db.get(Author, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    async def _refresh(aid: uuid.UUID):
        from app.services.catalog_service import refresh_author_catalog

        async with async_session() as bg_db:
            a = await bg_db.get(Author, aid)
            if not a:
                return
            try:
                count = await refresh_author_catalog(bg_db, a)
                import logging
                logging.getLogger(__name__).info("Refreshed author %s: %d new books", a.name, count)
            except Exception:
                import logging
                logging.getLogger(__name__).warning("Refresh failed for author %s", aid, exc_info=True)

    background_tasks.add_task(_refresh, author_id)
    return {"status": "refreshing", "author_id": str(author_id)}


@router.delete("/{author_id}")
async def delete_monitored_author(
    author_id: uuid.UUID,
    remove_books: bool = Query(False, description="Also remove unowned books by this author"),
    db: AsyncSession = Depends(get_db),
):
    """Remove a monitored author. Optionally remove their unowned books too."""
    author = await db.get(Author, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    if remove_books:
        # Find books by this author that have no LibraryItems (unowned)
        books_stmt = (
            select(Book.id)
            .join(BookAuthor, Book.id == BookAuthor.book_id)
            .outerjoin(LibraryItem, LibraryItem.book_id == Book.id)
            .where(BookAuthor.author_id == author_id)
            .group_by(Book.id)
            .having(func.count(LibraryItem.id) == 0)
        )
        result = await db.execute(books_stmt)
        unowned_ids = [row[0] for row in result]

        if unowned_ids:
            # Delete book_authors links for these books
            await db.execute(
                BookAuthor.__table__.delete().where(BookAuthor.book_id.in_(unowned_ids))
            )
            # Delete series_books links
            await db.execute(
                SeriesBook.__table__.delete().where(SeriesBook.book_id.in_(unowned_ids))
            )
            # Delete the books
            await db.execute(
                Book.__table__.delete().where(Book.id.in_(unowned_ids))
            )

    # Unmonitor the author (or delete if they have no remaining books)
    remaining_stmt = select(func.count(BookAuthor.book_id)).where(BookAuthor.author_id == author_id)
    remaining = (await db.execute(remaining_stmt)).scalar() or 0

    if remaining == 0:
        await db.delete(author)
    else:
        author.monitored = False

    await db.commit()
    return {"status": "removed", "author_id": str(author_id)}
