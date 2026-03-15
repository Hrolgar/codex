# Metadata providers — import from specific modules to avoid circular imports
# e.g. from app.metadata.hardcover import HardcoverProvider
from app.metadata.base import MetadataProvider, MetadataResult

__all__ = ["MetadataProvider", "MetadataResult"]
