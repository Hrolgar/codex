from collections.abc import AsyncIterator

import httpx

from app.config import settings
from app.scanners.base import ScannedItem


class AudiobookshelfScanner:
    async def validate_config(self, config: dict) -> bool:
        url = config.get("url") or settings.audiobookshelf_url
        api_key = config.get("api_key") or settings.audiobookshelf_api_key
        if not url or not api_key:
            return False
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{url}/api/authorize", headers={"Authorization": f"Bearer {api_key}"})
            return resp.status_code == 200

    async def scan(self, config: dict) -> AsyncIterator[ScannedItem]:
        url = config.get("url") or settings.audiobookshelf_url
        api_key = config.get("api_key") or settings.audiobookshelf_api_key
        headers = {"Authorization": f"Bearer {api_key}"}

        async with httpx.AsyncClient(timeout=30) as client:
            libs_resp = await client.get(f"{url}/api/libraries", headers=headers)
            libs_resp.raise_for_status()
            libraries = libs_resp.json().get("libraries", [])

            for lib in libraries:
                lib_id = lib["id"]
                page = 0
                while True:
                    items_resp = await client.get(
                        f"{url}/api/libraries/{lib_id}/items",
                        headers=headers,
                        params={"limit": 100, "page": page},
                    )
                    items_resp.raise_for_status()
                    data = items_resp.json()
                    results = data.get("results", [])
                    if not results:
                        break

                    for item in results:
                        media = item.get("media", {})
                        metadata = media.get("metadata", {})
                        yield ScannedItem(
                            file_path=item.get("path", ""),
                            file_format="audiobook",
                            title=metadata.get("title"),
                            author=metadata.get("authorName"),
                            isbn=metadata.get("isbn"),
                            asin=metadata.get("asin"),
                            duration_seconds=int(media.get("duration", 0)) or None,
                            cover_url=f"{url}/api/items/{item['id']}/cover" if item.get("id") else None,
                            media_type="audiobook",
                            extra={"abs_id": item.get("id"), "abs_library": lib_id},
                        )

                    if len(results) < 100:
                        break
                    page += 1
