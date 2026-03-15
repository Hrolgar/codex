import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.matching import escape_like, fuzzy_match, normalize_author, normalize_title
from app.models import Author, Book, BookAuthor

FUZZY_THRESHOLD = 85.0


async def check_duplicate(
    db: AsyncSession,
    title: str,
    author: str | None = None,
    isbn: str | None = None,
    media_type: str | None = None,
) -> tuple[bool, float, uuid.UUID | None]:
    """Check if a book already exists. Returns (is_duplicate, confidence, matched_book_id).

    When media_type is provided, only matches against books with the same media_type.
    This allows 'The Martian (ebook)' and 'The Martian (audiobook)' to coexist.
    """

    # Tier 1: ISBN exact match
    if isbn:
        isbn = isbn.strip()
        for col in (Book.isbn_13, Book.isbn_10):
            stmt = select(Book).where(col == isbn)
            if media_type:
                stmt = stmt.where(Book.media_type == media_type)
            result = await db.execute(stmt)
            book = result.scalar_one_or_none()
            if book:
                return True, 1.0, book.id

    # Tier 2: Fuzzy title + author matching
    if not title:
        return False, 0.0, None

    norm_title = normalize_title(title)
    norm_author = normalize_author(author) if author else None

    # Fetch candidate books (limit to reasonable set via ILIKE prefix)
    first_word = norm_title.split()[0] if norm_title else ""
    if first_word:
        stmt = select(Book).where(Book.title.ilike(f"%{escape_like(first_word)}%"))
        if media_type:
            stmt = stmt.where(Book.media_type == media_type)
    else:
        return False, 0.0, None

    result = await db.execute(stmt)
    candidates = result.scalars().all()

    best_score = 0.0
    best_book: Book | None = None

    for candidate in candidates:
        title_score = fuzzy_match(norm_title, normalize_title(candidate.title))

        if norm_author:
            # Get the candidate's authors
            author_result = await db.execute(
                select(Author.name)
                .join(BookAuthor, Author.id == BookAuthor.author_id)
                .where(BookAuthor.book_id == candidate.id)
            )
            author_names = [row[0] for row in author_result]
            if author_names:
                author_scores = [
                    fuzzy_match(norm_author, normalize_author(a)) for a in author_names
                ]
                author_score = max(author_scores)
            else:
                author_score = 50.0  # neutral when no author data
            combined = (title_score * 0.6) + (author_score * 0.4)
        else:
            combined = title_score

        if combined > best_score:
            best_score = combined
            best_book = candidate

    if best_score >= FUZZY_THRESHOLD and best_book:
        return True, best_score / 100.0, best_book.id

    return False, best_score / 100.0, None
