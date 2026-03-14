import httpx

from app.metadata.base import MetadataResult

BASE_URL = "https://openlibrary.org"


class OpenLibraryProvider:
    async def search(self, title: str, author: str | None = None) -> list[MetadataResult]:
        params = {"title": title, "limit": 10}
        if author:
            params["author"] = author

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{BASE_URL}/search.json", params=params)
            resp.raise_for_status()
            data = resp.json()

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
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{BASE_URL}/isbn/{isbn}.json")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()

        authors = []
        for author_ref in data.get("authors", []):
            key = author_ref.get("key")
            if key:
                async with httpx.AsyncClient(timeout=10) as client:
                    a_resp = await client.get(f"{BASE_URL}{key}.json")
                    if a_resp.status_code == 200:
                        authors.append(a_resp.json().get("name", ""))

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
