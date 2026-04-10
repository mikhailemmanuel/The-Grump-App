"""Venue endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User, UserReview
from app.models.venue import CityRanking, Recommendation, ReservationLink, Venue, VenueSummary
from app.schemas import (
    RecommendationOut,
    ReservationLinkOut,
    ReviewCreate,
    ReviewOut,
    VenueList,
    VenueOut,
    VenueSummaryOut,
)

router = APIRouter(tags=["venues"])


# ── Helpers ───────────────────────────────────────────────────────────


def _venue_to_out(v: Venue, ranking: CityRanking | None = None) -> VenueOut:
    return VenueOut(
        id=v.id,
        entity_type=v.entity_type,
        name=v.name,
        address=v.address,
        city=v.city,
        country=v.country,
        lat=None,  # extract from PostGIS if needed
        lng=None,
        tags=v.tags,
        price_level=v.price_level,
        cuisine_tags=v.cuisine_tags,
        star_rating=v.star_rating,
        hotel_brand=v.hotel_brand,
        composite_score=ranking.composite_score if ranking else None,
        rank=ranking.rank if ranking else None,
        google_place_id=v.google_place_id,
    )


async def _list_venues(
    db: AsyncSession,
    entity_type: str | None = None,
    city: str | None = None,
    tags: list[str] | None = None,
    sort_by: str = "name",
    limit: int = 20,
    offset: int = 0,
) -> VenueList:
    q = select(Venue)
    count_q = select(func.count()).select_from(Venue)

    if entity_type:
        q = q.where(Venue.entity_type == entity_type)
        count_q = count_q.where(Venue.entity_type == entity_type)
    if city:
        q = q.where(func.lower(Venue.city) == city.lower())
        count_q = count_q.where(func.lower(Venue.city) == city.lower())
    if tags:
        q = q.where(Venue.tags.overlap(tags))
        count_q = count_q.where(Venue.tags.overlap(tags))

    order_col = getattr(Venue, sort_by, Venue.name)
    q = q.order_by(order_col).offset(offset).limit(limit)

    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(q)).scalars().all()
    return VenueList(items=[_venue_to_out(v) for v in rows], total=total)


# ── Routes ────────────────────────────────────────────────────────────


@router.get("/venues", response_model=VenueList)
async def list_venues(
    entity_type: str | None = None,
    city: str | None = None,
    tags: str | None = Query(None, description="Comma-separated tags"),
    sort_by: str = "name",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    return await _list_venues(db, entity_type=entity_type, city=city, tags=tag_list, sort_by=sort_by, limit=limit, offset=offset)


@router.get("/restaurants", response_model=VenueList)
async def list_restaurants(
    city: str | None = None,
    tags: str | None = Query(None),
    sort_by: str = "name",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    return await _list_venues(db, entity_type="restaurant", city=city, tags=tag_list, sort_by=sort_by, limit=limit, offset=offset)


@router.get("/hotels", response_model=VenueList)
async def list_hotels(
    city: str | None = None,
    tags: str | None = Query(None),
    sort_by: str = "name",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    return await _list_venues(db, entity_type="hotel", city=city, tags=tag_list, sort_by=sort_by, limit=limit, offset=offset)


@router.get("/venues/{venue_id}", response_model=VenueOut)
async def get_venue(venue_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Venue).where(Venue.id == venue_id))
    venue = result.scalar_one_or_none()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return _venue_to_out(venue)


@router.get("/venues/{venue_id}/recommendations", response_model=list[RecommendationOut])
async def get_venue_recommendations(venue_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Recommendation).where(Recommendation.venue_id == venue_id).order_by(Recommendation.published_at.desc())
    )
    return result.scalars().all()


@router.get("/venues/{venue_id}/reservations", response_model=list[ReservationLinkOut])
async def get_venue_reservations(venue_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ReservationLink).where(ReservationLink.venue_id == venue_id)
    )
    return result.scalars().all()


@router.get("/venues/{venue_id}/summary", response_model=VenueSummaryOut)
async def get_venue_summary(venue_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VenueSummary).where(VenueSummary.venue_id == venue_id)
    )
    summary = result.scalar_one_or_none()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return summary


@router.get("/venues/{venue_id}/reviews", response_model=list[ReviewOut])
async def get_venue_reviews(
    venue_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserReview)
        .options(selectinload(UserReview.photos))
        .where(UserReview.venue_id == venue_id, UserReview.is_public.is_(True))
        .order_by(UserReview.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/venues/{venue_id}/review", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def create_venue_review(
    venue_id: uuid.UUID,
    body: ReviewCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify venue exists
    venue = (await db.execute(select(Venue).where(Venue.id == venue_id))).scalar_one_or_none()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    review = UserReview(
        user_id=user.id,
        venue_id=venue_id,
        verdict=body.verdict,
        comment=body.comment,
        visited_at=body.visited_at,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review, attribute_names=["photos"])
    return review
