"""User endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models.user import CustomList, CustomListItem, SavedVenue, User, UserReview, WantToGo
from app.schemas import (
    CustomListCreate,
    CustomListOut,
    ReviewOut,
    SavedVenueOut,
    UserOut,
    UserSettingsUpdate,
    WantToGoOut,
)

router = APIRouter(prefix="/users", tags=["users"])


def _check_owner(user_id: uuid.UUID, current_user: User) -> None:
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised")


# ── Reviews ───────────────────────────────────────────────────────────


@router.get("/{user_id}/reviews", response_model=list[ReviewOut])
async def get_user_reviews(
    user_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserReview)
        .options(selectinload(UserReview.photos))
        .where(UserReview.user_id == user_id, UserReview.is_public.is_(True))
        .order_by(UserReview.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


# ── Want-to-go ────────────────────────────────────────────────────────


@router.get("/{user_id}/want-to-go", response_model=list[WantToGoOut])
async def get_want_to_go(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_owner(user_id, current_user)
    result = await db.execute(
        select(WantToGo).where(WantToGo.user_id == user_id).order_by(WantToGo.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{user_id}/want-to-go/{venue_id}", response_model=WantToGoOut, status_code=status.HTTP_201_CREATED)
async def add_want_to_go(
    user_id: uuid.UUID,
    venue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _check_owner(user_id, current_user)
    obj = WantToGo(user_id=user_id, venue_id=venue_id)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{user_id}/want-to-go/{venue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_want_to_go(
    user_id: uuid.UUID,
    venue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _check_owner(user_id, current_user)
    obj = (await db.execute(
        select(WantToGo).where(WantToGo.user_id == user_id, WantToGo.venue_id == venue_id)
    )).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(obj)
    await db.commit()


# ── Visited ───────────────────────────────────────────────────────────


@router.get("/{user_id}/visited", response_model=list[ReviewOut])
async def get_visited(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_owner(user_id, current_user)
    result = await db.execute(
        select(UserReview)
        .options(selectinload(UserReview.photos))
        .where(UserReview.user_id == user_id)
        .order_by(UserReview.visited_at.desc().nullslast())
    )
    return result.scalars().all()


# ── Custom Lists ──────────────────────────────────────────────────────


@router.get("/{user_id}/lists", response_model=list[CustomListOut])
async def get_user_lists(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_owner(user_id, current_user)
    result = await db.execute(
        select(CustomList)
        .options(selectinload(CustomList.items))
        .where(CustomList.user_id == user_id)
        .order_by(CustomList.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{user_id}/lists", response_model=CustomListOut, status_code=status.HTTP_201_CREATED)
async def create_list(
    user_id: uuid.UUID,
    body: CustomListCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _check_owner(user_id, current_user)
    cl = CustomList(user_id=user_id, name=body.name, entity_type=body.entity_type, description=body.description)
    db.add(cl)
    await db.commit()
    await db.refresh(cl, attribute_names=["items"])
    return cl


@router.get("/{user_id}/lists/{list_id}", response_model=CustomListOut)
async def get_list(
    user_id: uuid.UUID,
    list_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_owner(user_id, current_user)
    cl = (await db.execute(
        select(CustomList).options(selectinload(CustomList.items)).where(CustomList.id == list_id, CustomList.user_id == user_id)
    )).scalar_one_or_none()
    if not cl:
        raise HTTPException(status_code=404, detail="List not found")
    return cl


@router.put("/{user_id}/lists/{list_id}", response_model=CustomListOut)
async def update_list(
    user_id: uuid.UUID,
    list_id: uuid.UUID,
    body: CustomListCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _check_owner(user_id, current_user)
    cl = (await db.execute(
        select(CustomList).options(selectinload(CustomList.items)).where(CustomList.id == list_id, CustomList.user_id == user_id)
    )).scalar_one_or_none()
    if not cl:
        raise HTTPException(status_code=404, detail="List not found")
    cl.name = body.name
    cl.entity_type = body.entity_type
    cl.description = body.description
    await db.commit()
    await db.refresh(cl, attribute_names=["items"])
    return cl


@router.delete("/{user_id}/lists/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_list(
    user_id: uuid.UUID,
    list_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _check_owner(user_id, current_user)
    cl = (await db.execute(
        select(CustomList).where(CustomList.id == list_id, CustomList.user_id == user_id)
    )).scalar_one_or_none()
    if not cl:
        raise HTTPException(status_code=404, detail="List not found")
    await db.delete(cl)
    await db.commit()


@router.post("/{user_id}/lists/{list_id}/venues/{venue_id}", status_code=status.HTTP_201_CREATED)
async def add_venue_to_list(
    user_id: uuid.UUID,
    list_id: uuid.UUID,
    venue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _check_owner(user_id, current_user)
    next_position = (
        await db.execute(
            select(func.coalesce(func.max(CustomListItem.position) + 1, 0)).where(
                CustomListItem.list_id == list_id
            )
        )
    ).scalar() or 0
    item = CustomListItem(list_id=list_id, venue_id=venue_id, position=next_position)
    db.add(item)
    await db.commit()
    return {"ok": True}


@router.delete("/{user_id}/lists/{list_id}/venues/{venue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_venue_from_list(
    user_id: uuid.UUID,
    list_id: uuid.UUID,
    venue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _check_owner(user_id, current_user)
    item = (await db.execute(
        select(CustomListItem).where(CustomListItem.list_id == list_id, CustomListItem.venue_id == venue_id)
    )).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()


# ── Saved ─────────────────────────────────────────────────────────────


@router.get("/{user_id}/saved", response_model=list[SavedVenueOut])
async def get_saved(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_owner(user_id, current_user)
    result = await db.execute(
        select(SavedVenue).where(SavedVenue.user_id == user_id).order_by(SavedVenue.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{user_id}/saved/{venue_id}", response_model=SavedVenueOut, status_code=status.HTTP_201_CREATED)
async def save_venue(
    user_id: uuid.UUID,
    venue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _check_owner(user_id, current_user)
    obj = SavedVenue(user_id=user_id, venue_id=venue_id)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{user_id}/saved/{venue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_venue(
    user_id: uuid.UUID,
    venue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _check_owner(user_id, current_user)
    obj = (await db.execute(
        select(SavedVenue).where(SavedVenue.user_id == user_id, SavedVenue.venue_id == venue_id)
    )).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(obj)
    await db.commit()


# ── Settings ──────────────────────────────────────────────────────────


@router.put("/{user_id}/settings", response_model=UserOut)
async def update_settings(
    user_id: uuid.UUID,
    body: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _check_owner(user_id, current_user)
    current_user.reviews_public = body.reviews_public
    await db.commit()
    await db.refresh(current_user)
    return current_user
