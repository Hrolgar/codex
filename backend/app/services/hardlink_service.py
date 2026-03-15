import logging
import os
import shutil
from pathlib import Path
from app.services.path_template_service import render_path, PathContext

logger = logging.getLogger(__name__)


class HardlinkError(Exception):
    pass


async def process_completed_download(
    source_path: str,
    destination_root: str,
    path_template: str,
    context: PathContext,
    use_hardlink: bool = True,
) -> str:
    """Process a completed download: hardlink (or copy) to library path.

    Args:
        source_path: Path to the downloaded file
        destination_root: Root directory of the library (e.g. /mnt/nas/data/media/ebooks)
        path_template: Template string (e.g. '{Author}/{Series?{Series}/}{Title}')
        context: PathContext with book metadata for template rendering
        use_hardlink: If True, create hardlink. If False, copy file.

    Returns:
        The full destination path
    """
    source = Path(source_path)
    if not source.exists():
        raise HardlinkError(f"Source file not found: {source_path}")

    # Render the destination path from template
    relative_path = render_path(path_template, context)

    # Add the file extension
    ext = source.suffix
    dest_dir = Path(destination_root) / relative_path
    dest_file = dest_dir / f"{context.title}{ext}"

    # Create destination directory
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Remove existing file at destination if present
    if dest_file.exists():
        dest_file.unlink()

    if use_hardlink:
        try:
            os.link(str(source), str(dest_file))
            logger.info("Hardlinked %s -> %s", source, dest_file)
        except OSError as e:
            # Cross-device link not supported, fall back to copy
            logger.warning("Hardlink failed (%s), falling back to copy", e)
            shutil.copy2(str(source), str(dest_file))
            logger.info("Copied %s -> %s", source, dest_file)
    else:
        shutil.copy2(str(source), str(dest_file))
        logger.info("Copied %s -> %s", source, dest_file)

    return str(dest_file)
