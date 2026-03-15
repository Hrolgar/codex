"""Match author's catalog books to existing files in root folders."""
import logging
import os
from pathlib import Path

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Book, LibraryItem
from app.models.author import Author, BookAuthor
from app.models.root_folder import RootFolder

logger = logging.getLogger(__name__)

EBOOK_EXTENSIONS = {".epub", ".mobi", ".azw3", ".pdf"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".m4b", ".flac", ".ogg", ".opus"}
COMIC_EXTENSIONS = {".cbz"}


async def match_author_to_library(db: AsyncSession, author: Author) -> int:
    """Scan root folders for files by this author and link them to catalog books.

    Returns the number of new library items created.
    """
    # Get all root folders
    result = await db.execute(select(RootFolder))
    root_folders = result.scalars().all()
    if not root_folders:
        return 0

    # Get all books by this author
    book_ids_result = await db.execute(
        select(BookAuthor.book_id).where(BookAuthor.author_id == author.id)
    )
    book_ids = [row[0] for row in book_ids_result]
    if not book_ids:
        return 0

    books_result = await db.execute(select(Book).where(Book.id.in_(book_ids)))
    books = books_result.scalars().all()
    if not books:
        return 0

    matched = 0
    for root_folder in root_folders:
        folder_path = Path(root_folder.path)
        if not folder_path.is_dir():
            continue

        # Look for an author directory matching this author's name
        author_dirs = _find_author_dirs(folder_path, author.name)

        for author_dir in author_dirs:
            # Walk the author directory for media files
            for dirpath, _, filenames in os.walk(author_dir):
                for filename in filenames:
                    ext = Path(filename).suffix.lower()
                    all_exts = EBOOK_EXTENSIONS | AUDIO_EXTENSIONS | COMIC_EXTENSIONS
                    if ext not in all_exts:
                        continue

                    full_path = Path(dirpath) / filename
                    file_str = str(full_path)

                    # Check if already in library
                    existing = await db.execute(
                        select(LibraryItem).where(LibraryItem.file_path == file_str)
                    )
                    if existing.scalar_one_or_none():
                        continue

                    # Try to match file to a catalog book by title
                    book = _match_file_to_book(full_path, books)
                    if not book:
                        continue

                    # Determine format
                    if ext in AUDIO_EXTENSIONS:
                        file_format = ext.lstrip(".")
                    elif ext in COMIC_EXTENSIONS:
                        file_format = ext.lstrip(".")
                    else:
                        file_format = ext.lstrip(".")

                    lib_item = LibraryItem(
                        library_id=root_folder.id,
                        book_id=book.id,
                        file_path=file_str,
                        file_format=file_format,
                        file_size=full_path.stat().st_size,
                        raw_title=book.title,
                        raw_author=author.name,
                        matched=True,
                    )
                    db.add(lib_item)
                    matched += 1
                    logger.info(
                        "Matched file '%s' to book '%s' by %s",
                        filename, book.title, author.name,
                    )

    if matched:
        await db.commit()
        logger.info("Matched %d library files for author %s", matched, author.name)
    return matched


def _find_author_dirs(root: Path, author_name: str) -> list[Path]:
    """Find directories in root that match the author name (fuzzy)."""
    dirs = []
    try:
        for entry in os.scandir(root):
            if not entry.is_dir():
                continue
            # Fuzzy match directory name to author name
            score = fuzz.ratio(entry.name.lower(), author_name.lower())
            if score >= 80:
                dirs.append(Path(entry.path))
    except (PermissionError, OSError):
        pass
    return dirs


def _match_file_to_book(file_path: Path, books: list[Book]) -> Book | None:
    """Try to match a file to a catalog book by comparing file/directory name to title."""
    # Use the file stem and parent directory name as candidates
    candidates = [
        file_path.stem,
        file_path.parent.name,
    ]

    best_match = None
    best_score = 0

    for book in books:
        if not book.title:
            continue
        book_title = book.title.lower()
        for candidate in candidates:
            # Clean up candidate: remove series numbering like "1 - "
            clean = candidate.strip()
            if " - " in clean:
                clean = clean.split(" - ", 1)[1]

            score = fuzz.ratio(clean.lower(), book_title)
            if score > best_score:
                best_score = score
                best_match = book

    # Require at least 70% match
    if best_score >= 70:
        return best_match
    return None
