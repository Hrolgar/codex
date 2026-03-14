import logging

import httpx

from app.metadata.base import MetadataResult

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.hardcover.app/v1/graphql"

SEARCH_QUERY = """
query SearchBooks($query: String!) {
  search(query: $query, query_type: "books", per_page: 10) {
    results {
      ... on Book {
        id
        title
        subtitle
        description
        image { url }
        contributions { author { name } }
        editions { isbn_13 isbn_10 pages language release_date }
        book_series { series { name } position_in_series }
      }
    }
  }
}
"""

ISBN_QUERY = """
query LookupISBN($isbn: String!) {
  books(where: {editions: {isbn_13: {_eq: $isbn}}}, limit: 1) {
    id
    title
    subtitle
    description
    image { url }
    contributions { author { name } }
    editions { isbn_13 isbn_10 pages language release_date }
    book_series { series { name } position_in_series }
  }
}
"""


def _parse_book(book: dict) -> MetadataResult:
    authors = []
    for contrib in book.get("contributions") or []:
        author = contrib.get("author") or {}
        if author.get("name"):
            authors.append(author["name"])

    isbn_13 = None
    isbn_10 = None
    page_count = None
    language = None
    publish_year = None
    for edition in book.get("editions") or []:
        if not isbn_13 and edition.get("isbn_13"):
            isbn_13 = edition["isbn_13"]
        if not isbn_10 and edition.get("isbn_10"):
            isbn_10 = edition["isbn_10"]
        if not page_count and edition.get("pages"):
            page_count = edition["pages"]
        if not language and edition.get("language"):
            language = edition["language"]
        if not publish_year and edition.get("release_date"):
            rd = str(edition["release_date"])
            if rd[:4].isdigit():
                publish_year = int(rd[:4])

    series_name = None
    series_position = None
    for bs in book.get("book_series") or []:
        series = bs.get("series") or {}
        if series.get("name"):
            series_name = series["name"]
            series_position = bs.get("position_in_series")
            break

    image = book.get("image") or {}

    return MetadataResult(
        title=book.get("title"),
        subtitle=book.get("subtitle"),
        authors=authors,
        description=book.get("description"),
        cover_url=image.get("url"),
        publish_year=publish_year,
        page_count=page_count,
        language=language,
        isbn_10=isbn_10,
        isbn_13=isbn_13,
        series_name=series_name,
        series_position=series_position,
        source="hardcover",
    )


class HardcoverProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _query(self, query: str, variables: dict) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                GRAPHQL_URL,
                json={"query": query, "variables": variables},
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def search(self, title: str, author: str | None = None) -> list[MetadataResult]:
        try:
            query_str = f"{title} {author}" if author else title
            data = await self._query(SEARCH_QUERY, {"query": query_str})
            books = data.get("data", {}).get("search", {}).get("results", [])
            return [_parse_book(b) for b in books]
        except Exception:
            logger.warning("Hardcover search failed for %r", title, exc_info=True)
            return []

    async def lookup_isbn(self, isbn: str) -> MetadataResult | None:
        try:
            data = await self._query(ISBN_QUERY, {"isbn": isbn})
            books = data.get("data", {}).get("books", [])
            if books:
                return _parse_book(books[0])
            return None
        except Exception:
            logger.warning("Hardcover ISBN lookup failed for %s", isbn, exc_info=True)
            return None
