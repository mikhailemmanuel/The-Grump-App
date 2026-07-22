"""Tests for venue API endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import get_db
from app.models.venue import Venue, VenueSummary


def _make_venue(name: str = "Test Restaurant", entity_type: str = "restaurant") -> Venue:
    v = MagicMock(spec=Venue)
    v.id = uuid.uuid4()
    v.entity_type = entity_type
    v.name = name
    v.address = "123 Main St"
    v.city = "bangkok"
    v.country = "Thailand"
    v.location = None
    v.tags = ["thai"]
    v.price_level = 2
    v.cuisine_tags = ["thai"]
    v.star_rating = None
    v.hotel_brand = None
    v.google_place_id = None
    return v


@pytest_asyncio.fixture
async def venues_client(mock_redis):
    venue = _make_venue()

    async def _db():
        from unittest.mock import AsyncMock
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = venue
        result.scalars.return_value.all.return_value = [venue]
        result.scalar.return_value = 1
        session.execute.return_value = result
        yield session

    app.dependency_overrides[get_db] = _db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, venue
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_list_venues(venues_client):
    client, _ = venues_client
    resp = await client.get("/venues")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_venue(venues_client):
    client, venue = venues_client
    resp = await client.get(f"/venues/{venue.id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == venue.name


@pytest.mark.asyncio
async def test_get_venue_summary_empty_returns_ok(venues_client):
    """Summary endpoint returns 200 with empty object when no summary exists."""
    client, venue = venues_client

    async def _db_no_summary():
        from unittest.mock import AsyncMock
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute.return_value = result
        yield session

    app.dependency_overrides[get_db] = _db_no_summary
    resp = await client.get(f"/venues/{venue.id}/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["photo_count"] == 0
    assert data["review_count"] == 0
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_list_restaurants(venues_client):
    client, _ = venues_client
    resp = await client.get("/restaurants")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_hotels(venues_client):
    client, _ = venues_client
    resp = await client.get("/hotels")
    assert resp.status_code == 200
