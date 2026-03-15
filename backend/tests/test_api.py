"""API integration tests — health, books, wishlist, notifications, system."""
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
    assert "books" in data
    assert "libraries" in data
    assert "ebooks" in data
    assert "audiobooks" in data
    for val in data.values():
        assert isinstance(val, int)
        assert val >= 0


@pytest.mark.asyncio
async def test_wishlist_create_and_list(client: AsyncClient):
    # Create a wishlist item
    resp = await client.post("/api/wishlist", json={
        "search_title": "The Hobbit",
        "search_author": "J.R.R. Tolkien",
        "auto_download": False,
    })
    assert resp.status_code == 201
    item = resp.json()
    assert item["search_title"] == "The Hobbit"
    assert item["search_author"] == "J.R.R. Tolkien"
    assert item["status"] == "waiting"
    item_id = item["id"]

    # List should contain the new item
    resp = await client.get("/api/wishlist")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == item_id


@pytest.mark.asyncio
async def test_wishlist_delete(client: AsyncClient):
    # Create then delete
    resp = await client.post("/api/wishlist", json={
        "search_title": "Dune",
        "search_author": "Frank Herbert",
    })
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    resp = await client.delete(f"/api/wishlist/{item_id}")
    assert resp.status_code == 204

    # Verify removed
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
