"""Integration-style tests for auth API endpoints using a mocked DB."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.auth import create_access_token, hash_password
from app.database import get_db
from app.main import app
from app.models.user import User


def _make_user(email: str = "test@example.com", password: str = "Secure1!") -> User:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.email = email
    u.hashed_password = hash_password(password)
    u.display_name = "Test User"
    u.avatar_url = None
    u.reviews_public = True
    u.is_active = True
    u.is_admin = False
    return u


@pytest_asyncio.fixture
async def auth_client(mock_redis):
    """Client with mocked DB that has one seeded user."""
    user = _make_user()

    async def _db():
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = user
        result.scalars.return_value.all.return_value = []
        result.scalar.return_value = 0
        session.execute.return_value = result
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        yield session

    app.dependency_overrides[get_db] = _db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, user
    app.dependency_overrides.pop(get_db, None)


# ── /auth/register ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_conflict(auth_client):
    client, _ = auth_client
    resp = await client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "Secure1!",
        "display_name": "Test",
    })
    # User already exists (mock returns a user for any lookup)
    assert resp.status_code == 409


# ── /auth/login ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(auth_client):
    client, _ = auth_client
    resp = await client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "Secure1!",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(auth_client):
    client, _ = auth_client
    resp = await client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "WrongPass1!",
    })
    assert resp.status_code == 401


# ── /auth/me ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_me_authenticated(auth_client):
    client, user = auth_client
    token = create_access_token(user.id)
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == user.email


@pytest.mark.asyncio
async def test_get_me_unauthenticated(auth_client):
    client, _ = auth_client
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


# ── /auth/logout ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout_returns_204(auth_client):
    client, user = auth_client
    token = create_access_token(user.id)
    resp = await client.post(
        "/auth/logout",
        json={"refresh_token": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204
