import logging

import httpx

from app.metadata.base import MetadataResult

logger = logging.getLogger(__name__)

BASE_URL = "https://www.googleapis.com/books/v1/volumes"


def _parse_volume(volume: dict) -> MetadataResult:
    info = volume.get("volumeInfo", {})

    isbn_10 = None
    isbn_13 = None
    for ident in info.get("industryIdentifiers") or []:
        if ident.get("type") == "ISBN_10":
            isbn_10 = ident.get("identifier")
        elif ident.get("type") == "ISBN_13":
            isbn_13 = ident.get("identifier")

    cover_url = None
    image_links = info.get("imageLinks") or {}
    thumbnail = image_links.get("thumbnail")
    if thumbnail:
        cover_url = thumbnail.replace("http://", "https://").replace("&edge=curl", "")

    publish_year = None
    published_date = info.get("publishedDate", "")
    if published_date[:4].isdigit():
        publish_year = int(published_date[:4])

    return MetadataResult(
        title=info.get("title"),
        subtitle=info.get("subtitle"),
        authors=info.get("authors") or [],
        description=info.get("description"),
        cover_url=cover_url,
        publish_year=publish_year,
        page_count=info.get("pageCount"),
        language=info.get("language"),
        isbn_10=isbn_10,
        isbn_13=isbn_13,
        source="google_books",
    )


class GoogleBooksProvider:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    def _params(self, q: str) -> dict:
        params: dict[str, str] = {"q": q}
        if self.api_key:
            params["key"] = self.api_key
        return params

    async def search(self, title: str, author: str | None = None) -> list[MetadataResult]:
        try:
            parts = [f"intitle:{title}"]
            if author:
                parts.append(f"inauthor:{author}")
            q = " ".join(parts)

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(BASE_URL, params=self._params(q))
                resp.raise_for_status()
                data = resp.json()

            return [_parse_volume(item) for item in data.get("items", [])]
        except Exception:
            logger.warning("Google Books search failed for %r", title, exc_info=True)
            return []

    async def lookup_isbn(self, isbn: str) -> MetadataResult | None:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(BASE_URL, params=self._params(f"isbn:{isbn}"))
                resp.raise_for_status()
                data = resp.json()

            items = data.get("items", [])
            if items:
                return _parse_volume(items[0])
            return None
        except Exception:
            logger.warning("Google Books ISBN lookup failed for %s", isbn, exc_info=True)
            return None
