"""API integration tests — health, books, wishlist, notifications."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_books_empty(client: AsyncClient):
    resp = await client.get("/api/books")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_system_stats(client: AsyncClient):
    resp = await client.get("/api/system/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_books" in data
    assert "total_authors" in data


@pytest.mark.asyncio
async def test_wishlist_crud(client: AsyncClient):
    # Create
    resp = await client.post("/api/wishlist", json={
        "search_title": "The Hobbit",
        "search_author": "J.R.R. Tolkien",
        "auto_download": False,
    })
    assert resp.status_code == 200
    item = resp.json()
    assert item["search_title"] == "The Hobbit"
    assert item["search_author"] == "J.R.R. Tolkien"
    assert item["status"] == "waiting"
    item_id = item["id"]

    # List
    resp = await client.get("/api/wishlist")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == item_id

    # Update
    resp = await client.put(f"/api/wishlist/{item_id}", json={
        "auto_download": True,
    })
    assert resp.status_code == 200
    assert resp.json()["auto_download"] is True

    # Delete
    resp = await client.delete(f"/api/wishlist/{item_id}")
    assert resp.status_code == 200

    # Verify deleted
    resp = await client.get("/api/wishlist")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_notifications_empty(client: AsyncClient):
    resp = await client.get("/api/notifications")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_notifications_count(client: AsyncClient):
    resp = await client.get("/api/notifications/count")
    assert resp.status_code == 200
    data = resp.json()
    assert data["unread"] == 0


@pytest.mark.asyncio
async def test_authors_empty(client: AsyncClient):
    resp = await client.get("/api/authors")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_series_empty(client: AsyncClient):
    resp = await client.get("/api/series")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_libraries_empty(client: AsyncClient):
    resp = await client.get("/api/libraries")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0
