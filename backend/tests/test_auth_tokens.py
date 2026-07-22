"""Tests for JWT access/refresh token creation and verification."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from jose import jwt

from app.auth import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    revoke_refresh_token,
    is_token_blacklisted,
    blacklist_access_token,
    hash_password,
    verify_password,
)
from app.config import settings


# ── Password hashing ──────────────────────────────────────────────────────────

def test_hash_and_verify_password():
    from unittest.mock import patch
    # Mock pwd_context to avoid bcrypt version issues in CI without libssl
    with patch("app.auth.pwd_context") as mock_ctx:
        mock_ctx.hash.return_value = "hashed"
        mock_ctx.verify.side_effect = lambda plain, hashed: plain == "Secure1!"
        result = hash_password("Secure1!")
        assert verify_password("Secure1!", result)
        assert not verify_password("Wrong1!", result)


# ── Access tokens ─────────────────────────────────────────────────────────────

def test_access_token_contains_subject():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"


def test_access_token_has_jti():
    token = create_access_token(uuid.uuid4())
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert "jti" in payload


# ── Refresh tokens ────────────────────────────────────────────────────────────

def _redis_mock():
    r = MagicMock()
    store: dict = {}
    r.setex.side_effect = lambda key, ttl, val: store.update({key: val})
    r.get.side_effect = lambda key: store.get(key)
    r.delete.side_effect = lambda key: store.pop(key, None)
    r.exists.side_effect = lambda key: int(key in store)
    return r


def test_refresh_token_roundtrip():
    user_id = uuid.uuid4()
    with patch("app.auth._get_redis", return_value=_redis_mock()):
        token = create_refresh_token(user_id)
        result = verify_refresh_token(token)
    assert result == str(user_id)


def test_revoke_refresh_token():
    user_id = uuid.uuid4()
    r = _redis_mock()
    with patch("app.auth._get_redis", return_value=r):
        token = create_refresh_token(user_id)
        revoke_refresh_token(token)
        assert verify_refresh_token(token) is None


def test_blacklist_access_token():
    token = create_access_token(uuid.uuid4())
    r = _redis_mock()
    with patch("app.auth._get_redis", return_value=r):
        assert not is_token_blacklisted(token)
        blacklist_access_token(token, ttl=900)
        assert is_token_blacklisted(token)
