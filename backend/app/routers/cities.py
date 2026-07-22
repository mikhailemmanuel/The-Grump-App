"""City endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.venue import CityRanking, Venue
from app.schemas import CityRankingOut, VenueOut

router = APIRouter(tags=["cities"])


@router.get("/cities", response_model=list[str])
async def list_cities(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(distinct(func.lower(Venue.city))).order_by(func.lower(Venue.city))
    )
    return result.scalars().all()


@router.get("/cities/{city}/rankings", response_model=list[CityRankingOut])
async def get_city_rankings(
    city: str,
    entity_type: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(CityRanking)
        .options(selectinload(CityRanking.venue))
        .where(func.lower(CityRanking.city) == city.lower())
    )
    if entity_type:
        q = q.where(CityRanking.entity_type == entity_type)
    q = q.order_by(CityRanking.rank).offset(offset).limit(limit)

    rows = (await db.execute(q)).scalars().all()
    return [
        CityRankingOut(
            venue=VenueOut.model_validate(r.venue),
            composite_score=r.composite_score,
            rank=r.rank,
            source_scores=r.source_scores,
        )
        for r in rows
    ]
