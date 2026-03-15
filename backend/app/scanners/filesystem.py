import os
import re
import zipfile
from collections import defaultdict
from collections.abc import AsyncIterator
from pathlib import Path

from app.scanners.base import ScannedItem

EBOOK_EXTENSIONS = {".epub", ".mobi", ".azw3", ".pdf"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".m4b", ".flac", ".ogg", ".opus"}
COMIC_EXTENSIONS = {".cbz"}  # CBR (RAR) not supported without rarfile


class FilesystemScanner:
    async def validate_config(self, config: dict) -> bool:
        path = config.get("path", "")
        return bool(path) and os.path.isdir(path)

    async def scan(self, config: dict) -> AsyncIterator[ScannedItem]:
        root = Path(config["path"])

        # Group files by parent directory and type category
        dir_files: dict[str, dict[str, list[Path]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                ext = Path(filename).suffix.lower()
                if ext in AUDIO_EXTENSIONS:
                    category = "audio"
                elif ext in EBOOK_EXTENSIONS:
                    category = "ebook"
                elif ext in COMIC_EXTENSIONS:
                    category = "comic"
                else:
                    continue
                full_path = Path(dirpath) / filename
                dir_files[dirpath][category].append(full_path)

        for dirpath, categories in dir_files.items():
            # Audio files: group entire directory into ONE ScannedItem
            if "audio" in categories:
                audio_files = sorted(categories["audio"])
                yield _build_audiobook_item(root, Path(dirpath), audio_files)

            # Ebooks: one ScannedItem per file
            for ebook_path in categories.get("ebook", []):
                yield _build_single_file_item(root, ebook_path, "ebook")

            # Comics: one ScannedItem per file
            for comic_path in categories.get("comic", []):
                yield _build_single_file_item(root, comic_path, "comic")


def _build_audiobook_item(root: Path, dirpath: Path, audio_files: list[Path]) -> ScannedItem:
    """Build a single ScannedItem for an audiobook directory."""
    total_size = sum(f.stat().st_size for f in audio_files)

    # Determine dominant format
    from collections import Counter
    ext_counts = Counter(f.suffix.lower().lstrip(".") for f in audio_files)
    dominant_format = ext_counts.most_common(1)[0][0]

    item = ScannedItem(
        file_path=str(dirpath),
        file_format=dominant_format,
        file_size=total_size,
        media_type="audiobook",
        file_count=len(audio_files),
        is_directory=True,
    )

    # Extract metadata from first file only (for author tag, etc.)
    _extract_audio_metadata(audio_files[0], item)

    # Sum duration across all audio files
    total_duration = _sum_audio_durations(audio_files)
    if total_duration:
        item.duration_seconds = total_duration

    # Directory name is the title — always override track metadata
    _infer_from_directory(root, dirpath, item, is_directory=True)

    return item


def _build_single_file_item(root: Path, full_path: Path, media_type: str) -> ScannedItem:
    """Build a ScannedItem for a single ebook or comic file."""
    ext = full_path.suffix.lower()
    item = ScannedItem(
        file_path=str(full_path),
        file_format=ext.lstrip("."),
        file_size=full_path.stat().st_size,
        media_type=media_type,
    )

    if ext == ".epub":
        _extract_epub_metadata(full_path, item)
    elif ext in COMIC_EXTENSIONS:
        _extract_comic_metadata(full_path, item)

    _infer_from_directory(root, full_path, item, is_directory=False)
    return item


def _infer_from_directory(root: Path, path: Path, item: ScannedItem, *, is_directory: bool) -> None:
    """Infer author, series, and title from directory structure relative to library root.

    Supported layouts (relative to root):
        1 level  — Author/Book.epub         → author=Author, title from filename
        2 levels — Author/Book/files        → author=Author, title=Book
        3 levels — Author/Series/Book/files → author=Author, series=Series, title=Book
    """
    try:
        relative = path.relative_to(root)
    except ValueError:
        return

    if is_directory:
        parts = relative.parts
    else:
        parts = relative.parent.parts

    if len(parts) >= 1:
        item.author = parts[0]

    if len(parts) >= 3:
        # Author / Series / Book
        if not item.series:
            item.series = parts[1]
        title_part = parts[2]
        pos, clean_title = _parse_series_position(title_part)
        if is_directory:
            item.title = clean_title
        elif not item.title:
            item.title = path.stem
        if pos is not None and item.series_position is None:
            item.series_position = pos
    elif len(parts) >= 2:
        # Author / Book  (no series at this level)
        if is_directory:
            item.title = parts[-1]
        elif not item.title:
            item.title = path.stem
    else:
        # Author only — title from filename
        if is_directory:
            item.title = relative.parts[-1] if relative.parts else item.title
        elif not item.title:
            item.title = path.stem


def _parse_series_position(name: str) -> tuple[float | None, str]:
    """Extract a series position number from a directory/title name.

    Returns (position, cleaned_title). If no position is found, returns (None, name).

    Supported patterns:
        '1 - Dune'        → (1.0, 'Dune')
        '01 - Dune'       → (1.0, 'Dune')
        '2.5 - Interlude' → (2.5, 'Interlude')
        'Dune (Book 1)'   → (1.0, 'Dune')
        'Dune (Book 02)'  → (2.0, 'Dune')
    """
    # Pattern: leading number — "01 - Title" or "1 - Title"
    m = re.match(r"^(\d+(?:\.\d+)?)\s*[-–—]\s*(.+)$", name)
    if m:
        return float(m.group(1)), m.group(2).strip()

    # Pattern: trailing "(Book N)" or "(Book N)"
    m = re.search(r"\(Book\s+(\d+(?:\.\d+)?)\)\s*$", name, re.IGNORECASE)
    if m:
        title = name[: m.start()].strip()
        return float(m.group(1)), title

    return None, name


def _sum_audio_durations(audio_files: list[Path]) -> int | None:
    """Sum the duration of all audio files in a directory."""
    try:
        import mutagen
    except ImportError:
        return None

    total = 0
    for f in audio_files:
        try:
            audio = mutagen.File(str(f))
            if audio and audio.info:
                total += int(audio.info.length)
        except Exception:
            continue
    return total if total > 0 else None


def _extract_epub_metadata(path: Path, item: ScannedItem) -> None:
    try:
        import ebooklib
        from ebooklib import epub

        book = epub.read_epub(str(path), options={"ignore_ncx": True})
        title = book.get_metadata("DC", "title")
        if title:
            item.title = title[0][0]
        creator = book.get_metadata("DC", "creator")
        if creator:
            item.author = creator[0][0]
        identifiers = book.get_metadata("DC", "identifier")
        for ident in identifiers:
            val = ident[0]
            if val and len(val) in (10, 13) and val.replace("-", "").isdigit():
                item.isbn = val.replace("-", "")
                break
    except Exception:
        pass


def _extract_comic_metadata(path: Path, item: ScannedItem) -> None:
    try:
        with zipfile.ZipFile(str(path)) as zf:
            if 'ComicInfo.xml' in zf.namelist():
                raw = zf.read('ComicInfo.xml')
                # Safe XML parsing — defusedxml blocks XXE attacks
                try:
                    from defusedxml.ElementTree import fromstring
                except ImportError:
                    from xml.etree.ElementTree import fromstring
                info = fromstring(raw)
                item.title = info.findtext('Title') or item.title
                item.author = info.findtext('Writer') or item.author
                series_name = info.findtext('Series')
                if series_name:
                    item.series = series_name
    except Exception:
        pass


def _extract_audio_metadata(path: Path, item: ScannedItem) -> None:
    """Extract metadata from a single audio file. For audiobook directories,
    this is called on the first file only."""
    try:
        import mutagen

        audio = mutagen.File(str(path))
        if audio is None:
            return
        item.duration_seconds = int(audio.info.length) if audio.info else None
        if hasattr(audio, "tags") and audio.tags:
            # Don't set title from track metadata — directory name is used instead
            item.author = str(audio.tags.get("TPE1", [None])[0]) if audio.tags.get("TPE1") else item.author
    except Exception:
        pass
