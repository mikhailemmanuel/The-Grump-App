"""Search endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.venue import Venue
from app.schemas import VenueList, VenueOut

router = APIRouter(tags=["search"])


@router.get("/search", response_model=VenueList)
async def search_venues(
    q: str = Query(..., min_length=1),
    entity_type: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    pattern = f"%{q.lower()}%"
    stmt = select(Venue).where(func.lower(Venue.name).like(pattern))
    count_stmt = select(func.count()).select_from(Venue).where(func.lower(Venue.name).like(pattern))

    if entity_type:
        stmt = stmt.where(Venue.entity_type == entity_type)
        count_stmt = count_stmt.where(Venue.entity_type == entity_type)

    total = (await db.execute(count_stmt)).scalar() or 0
    rows = (await db.execute(stmt.order_by(Venue.name).offset(offset).limit(limit))).scalars().all()

    return VenueList(
        items=[VenueOut.model_validate(v) for v in rows],
        total=total,
    )
