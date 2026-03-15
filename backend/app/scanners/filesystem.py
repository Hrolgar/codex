import os
from collections.abc import AsyncIterator
from pathlib import Path

from app.scanners.base import ScannedItem

EBOOK_EXTENSIONS = {".epub", ".mobi", ".azw3", ".pdf", ".cbz", ".cbr"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".m4b", ".flac", ".ogg", ".opus"}


class FilesystemScanner:
    async def validate_config(self, config: dict) -> bool:
        path = config.get("path", "")
        return bool(path) and os.path.isdir(path)

    async def scan(self, config: dict) -> AsyncIterator[ScannedItem]:
        root = Path(config["path"])
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                ext = Path(filename).suffix.lower()
                if ext not in EBOOK_EXTENSIONS and ext not in AUDIO_EXTENSIONS:
                    continue

                full_path = Path(dirpath) / filename
                file_size = full_path.stat().st_size
                media_type = "audiobook" if ext in AUDIO_EXTENSIONS else "ebook"

                item = ScannedItem(
                    file_path=str(full_path),
                    file_format=ext.lstrip("."),
                    file_size=file_size,
                    media_type=media_type,
                )

                if ext == ".epub":
                    _extract_epub_metadata(full_path, item)
                elif ext in AUDIO_EXTENSIONS:
                    _extract_audio_metadata(full_path, item)

                # Infer author/series from directory structure
                _infer_from_directory(root, full_path, item)

                yield item


def _infer_from_directory(root: Path, full_path: Path, item: ScannedItem) -> None:
    """Infer author and series from directory structure relative to library root."""
    try:
        relative = full_path.relative_to(root)
    except ValueError:
        return
    parts = relative.parent.parts  # directory parts, excluding filename
    if len(parts) >= 1 and not item.author:
        item.author = parts[0]
    if len(parts) >= 2 and not item.series:
        item.series = parts[1]
    # Use filename as title fallback if no embedded metadata
    if not item.title:
        item.title = full_path.stem


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


def _extract_audio_metadata(path: Path, item: ScannedItem) -> None:
    try:
        import mutagen

        audio = mutagen.File(str(path))
        if audio is None:
            return
        item.duration_seconds = int(audio.info.length) if audio.info else None
        if hasattr(audio, "tags") and audio.tags:
            item.title = str(audio.tags.get("TIT2", [None])[0]) if audio.tags.get("TIT2") else item.title
            item.author = str(audio.tags.get("TPE1", [None])[0]) if audio.tags.get("TPE1") else item.author
    except Exception:
        pass
