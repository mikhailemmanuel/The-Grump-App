"""FoodGrump FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.routers import auth_routes, cities, search, users, venues


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(venues.router)
app.include_router(cities.router)
app.include_router(search.router)
app.include_router(users.router)


@app.get("/", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "foodgrump"}
