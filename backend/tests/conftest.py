"""Shared pytest fixtures for FoodGrump backend tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.database import get_db
from app.main import app

# Force a safe test secret so JWT encoding/decoding works without .env
settings.secret_key = "test-secret-key-not-for-production"
settings.redis_url = "redis://localhost:6379/0"


def make_db_session(scalars_return=None, scalar_return=None):
    """Return a mock AsyncSession suitable for dependency injection."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_return
    result.scalars.return_value.all.return_value = scalars_return or []
    result.scalar.return_value = 0
    session.execute.return_value = result
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_redis():
    with patch("app.auth._get_redis") as mock:
        r = MagicMock()
        r.exists.return_value = 0
        r.get.return_value = None
        r.setex.return_value = True
        r.delete.return_value = True
        mock.return_value = r
        yield r


@pytest_asyncio.fixture
async def client(mock_redis):
    """HTTP test client with a no-op DB session and mocked Redis."""
    session = make_db_session()

    async def _override():
        yield session

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)
