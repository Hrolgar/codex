import asyncio
import logging

import httpx

from app.metadata.base import MetadataResult
from app.services.rate_limiter import get_limiter

logger = logging.getLogger(__name__)

BASE_URL = "https://openlibrary.org"
COVERS_BASE_URL = "https://covers.openlibrary.org"


def get_cover_url(isbn: str) -> str | None:
    """Return the OpenLibrary large-cover URL for an ISBN, or None if blank."""
    if not isbn:
        return None
    return f"{COVERS_BASE_URL}/b/isbn/{isbn}-L.jpg"


class OpenLibraryProvider:
    async def search(self, title: str, author: str | None = None) -> list[MetadataResult]:
        params = {"title": title, "limit": 10}
        if author:
            params["author"] = author

        limiter = get_limiter('openlibrary')
        await limiter.acquire()
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{BASE_URL}/search.json", params=params)
                if resp.status_code == 429:
                    logger.warning("OpenLibrary: rate limited (429), retrying after %.1fs", limiter.min_interval_seconds)
                    await asyncio.sleep(limiter.min_interval_seconds)
                    await limiter.acquire()
                    resp = await client.get(f"{BASE_URL}/search.json", params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            logger.warning("OpenLibrary: search request timed out")
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning("OpenLibrary: search HTTP %d error", exc.response.status_code)
            return []

        results = []
        for doc in data.get("docs", []):
            isbn_list = doc.get("isbn", [])
            isbn_13 = next((i for i in isbn_list if len(i) == 13), None)
            isbn_10 = next((i for i in isbn_list if len(i) == 10), None)
            cover_id = doc.get("cover_i")

            results.append(MetadataResult(
                title=doc.get("title"),
                authors=doc.get("author_name", []),
                publish_year=doc.get("first_publish_year"),
                page_count=doc.get("number_of_pages_median"),
                language=(doc.get("language", [None]) or [None])[0],
                isbn_10=isbn_10,
                isbn_13=isbn_13,
                cover_url=f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None,
                source="openlibrary",
            ))
        return results

    async def lookup_isbn(self, isbn: str) -> MetadataResult | None:
        limiter = get_limiter('openlibrary')
        await limiter.acquire()
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{BASE_URL}/isbn/{isbn}.json")
                if resp.status_code == 404:
                    return None
                if resp.status_code == 429:
                    logger.warning("OpenLibrary: rate limited (429), retrying after %.1fs", limiter.min_interval_seconds)
                    await asyncio.sleep(limiter.min_interval_seconds)
                    await limiter.acquire()
                    resp = await client.get(f"{BASE_URL}/isbn/{isbn}.json")
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            logger.warning("OpenLibrary: ISBN lookup timed out for %s", isbn)
            return None
        except httpx.HTTPStatusError as exc:
            logger.warning("OpenLibrary: ISBN lookup HTTP %d error for %s", exc.response.status_code, isbn)
            return None

        authors = []
        for author_ref in data.get("authors", []):
            key = author_ref.get("key")
            if key:
                await limiter.acquire()
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        a_resp = await client.get(f"{BASE_URL}{key}.json")
                        if a_resp.status_code == 200:
                            authors.append(a_resp.json().get("name", ""))
                except (httpx.TimeoutException, httpx.HTTPStatusError):
                    logger.warning("OpenLibrary: author fetch failed for %s", key)

        isbn_10 = None
        isbn_13 = None
        for ident in data.get("isbn_10", []):
            isbn_10 = ident
            break
        for ident in data.get("isbn_13", []):
            isbn_13 = ident
            break

        cover_id = (data.get("covers") or [None])[0]

        return MetadataResult(
            title=data.get("title"),
            subtitle=data.get("subtitle"),
            authors=authors,
            description=data.get("description", {}).get("value") if isinstance(data.get("description"), dict) else data.get("description"),
            publish_year=int(data["publish_date"][:4]) if data.get("publish_date", "")[:4].isdigit() else None,
            page_count=data.get("number_of_pages"),
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            cover_url=f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None,
            source="openlibrary",
        )
