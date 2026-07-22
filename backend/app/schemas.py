"""Pydantic schemas for FoodGrump API request/response types."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.validation import (
    MAX_PHOTO_CAPTION_LENGTH,
    validate_password_strength,
)


# ── Venues ────────────────────────────────────────────────────────────


class VenueOut(BaseModel):
    id: uuid.UUID
    entity_type: str
    name: str
    address: str | None = None
    city: str
    country: str | None = None
    lat: float | None = None
    lng: float | None = None
    tags: list[str] | None = None
    price_level: int | None = None
    cuisine_tags: list[str] | None = None
    star_rating: int | None = None
    hotel_brand: str | None = None
    composite_score: float | None = None
    rank: int | None = None
    google_place_id: str | None = None

    model_config = {"from_attributes": True}


class VenueList(BaseModel):
    items: list[VenueOut]
    total: int


class RecommendationOut(BaseModel):
    id: uuid.UUID
    source: str
    source_url: str | None = None
    title: str | None = None
    snippet: str | None = None
    rating: float | None = None
    awards: list[str] | None = None
    published_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReservationLinkOut(BaseModel):
    id: uuid.UUID
    platform: str
    booking_url: str

    model_config = {"from_attributes": True}


class VenueSummaryOut(BaseModel):
    ai_summary: str | None = None
    highlights: list[str] | None = None
    sentiment_breakdown: dict[str, Any] | None = None
    photo_count: int = 0
    review_count: int = 0

    model_config = {"from_attributes": True}


# ── Reviews ───────────────────────────────────────────────────────────


class ReviewPhotoOut(BaseModel):
    id: uuid.UUID
    image_url: str
    caption: str | None = None

    model_config = {"from_attributes": True}


class ReviewCreate(BaseModel):
    verdict: Literal["go_back", "iffy", "would_not_go_back"]
    comment: str | None = Field(None, max_length=2000)
    visited_at: date | None = None


class PhotoAttach(BaseModel):
    object_key: str
    caption: str | None = Field(None, max_length=MAX_PHOTO_CAPTION_LENGTH)


class ReviewOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    venue_id: uuid.UUID
    verdict: str
    comment: str | None = None
    is_public: bool = True
    visited_at: date | None = None
    created_at: datetime
    photos: list[ReviewPhotoOut] = []

    model_config = {"from_attributes": True}


# ── City Rankings ─────────────────────────────────────────────────────


class CityRankingOut(BaseModel):
    venue: VenueOut
    composite_score: float
    rank: int
    source_scores: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


# ── Users / Auth ──────────────────────────────────────────────────────


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, v: str) -> str:
        validate_password_strength(v)
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    avatar_url: str | None = None
    reviews_public: bool = True

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    reviews_public: bool


# ── Lists ─────────────────────────────────────────────────────────────


class CustomListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    entity_type: Literal["restaurant", "hotel", "mixed"] = "mixed"
    description: str | None = Field(None, max_length=500)


class CustomListItemOut(BaseModel):
    venue_id: uuid.UUID
    position: int

    model_config = {"from_attributes": True}


class CustomListOut(BaseModel):
    id: uuid.UUID
    name: str
    entity_type: str
    description: str | None = None
    is_public: bool = False
    items: list[CustomListItemOut] = []

    model_config = {"from_attributes": True}


# ── Want-to-go / Saved ────────────────────────────────────────────────


class WantToGoOut(BaseModel):
    venue_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class SavedVenueOut(BaseModel):
    venue_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Token / Auth Schemas ─────────────────────────────────────────────


class RefreshTokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class SearchQuery(BaseModel):
    q: str = Field(max_length=200)
