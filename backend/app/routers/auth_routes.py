"""Auth endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    blacklist_access_token,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    revoke_all_user_tokens,
    revoke_refresh_token,
    verify_password,
    verify_refresh_token,
)
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas import (
    LogoutRequest,
    RefreshTokenOut,
    RefreshTokenRequest,
    TokenOut,
    UserCreate,
    UserLogin,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        display_name=body.display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=RefreshTokenOut)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    return RefreshTokenOut(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=RefreshTokenOut)
async def refresh(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    user_id = verify_refresh_token(body.refresh_token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    revoke_refresh_token(body.refresh_token)

    import uuid as _uuid

    uid = _uuid.UUID(user_id)
    access_token = create_access_token(uid)
    new_refresh_token = create_refresh_token(uid)
    return RefreshTokenOut(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    body: LogoutRequest,
    current_user: User = Depends(get_current_user),
):
    # Blacklist current access token
    auth_header = request.headers.get("authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
    if token:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            import time

            exp = payload.get("exp", 0)
            ttl = max(int(exp - time.time()), 1)
            blacklist_access_token(token, ttl)
        except Exception:
            pass

    if body.refresh_token:
        revoke_refresh_token(body.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    # Blacklist current access token
    auth_header = request.headers.get("authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
    if token:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            import time

            exp = payload.get("exp", 0)
            ttl = max(int(exp - time.time()), 1)
            blacklist_access_token(token, ttl)
        except Exception:
            pass

    revoke_all_user_tokens(str(current_user.id))
