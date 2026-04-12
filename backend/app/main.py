"""FoodGrump FastAPI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

logger = logging.getLogger(__name__)

# Rate limiter — gracefully falls back to in-memory if Redis is unavailable
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address, storage_uri=settings.get_redis_url())
    _has_limiter = True
except Exception as e:
    logger.warning("Rate limiter disabled (Redis unavailable): %s", e)
    limiter = None
    _has_limiter = False

# Import engine lazily to avoid connection at module load
from app.database import engine  # noqa: E402

# Security headers middleware
try:
    from app.middleware.security_headers import SecurityHeadersMiddleware
    _has_security_headers = True
except Exception:
    _has_security_headers = False

from app.routers import auth_routes, cities, search, users, uploads, venues  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    lifespan=lifespan,
    title="FoodGrump",
    description="Curated restaurant & hotel recommendation engine",
    version="0.1.0",
)

if _has_limiter:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

if _has_security_headers:
    app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(venues.router)
app.include_router(cities.router)
app.include_router(search.router)
app.include_router(users.router)
app.include_router(uploads.router)


@app.get("/", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "foodgrump"}
