"""JWT authentication utilities for FoodGrump."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import redis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_redis: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(settings.redis_url)
    return _redis


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    jti = str(uuid.uuid4())
    payload = {"sub": str(user_id), "exp": expire, "jti": jti, "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(user_id: uuid.UUID) -> str:
    token = str(uuid.uuid4())
    ttl = settings.refresh_token_expire_days * 86400
    _get_redis().setex(f"refresh:{token}", ttl, str(user_id))
    return token


def verify_refresh_token(token: str) -> str | None:
    value = _get_redis().get(f"refresh:{token}")
    if value is None:
        return None
    return value.decode() if isinstance(value, bytes) else str(value)


def revoke_refresh_token(token: str) -> None:
    _get_redis().delete(f"refresh:{token}")


def revoke_all_user_tokens(user_id: str) -> None:
    r = _get_redis()
    cursor = 0
    while True:
        cursor, keys = r.scan(cursor=cursor, match="refresh:*", count=100)
        for key in keys:
            val = r.get(key)
            if val is not None:
                val_str = val.decode() if isinstance(val, bytes) else str(val)
                if val_str == user_id:
                    r.delete(key)
        if cursor == 0:
            break


def blacklist_access_token(token: str, ttl: int) -> None:
    _get_redis().setex(f"blacklist:{token}", ttl, "1")


def is_token_blacklisted(token: str) -> bool:
    return _get_redis().exists(f"blacklist:{token}") > 0


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if is_token_blacklisted(token):
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    if getattr(user, "is_active", True) is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated",
        )

    return user
