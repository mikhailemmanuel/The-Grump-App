from fastapi import APIRouter, Depends, HTTPException, Query
from app.permissions import require_auth
from app.models.user import User
from app.services.photos import generate_presigned_url, ALLOWED_TYPES

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/presigned-url")
async def get_presigned_url(
    content_type: str = Query(default="image/jpeg"),
    user: User = Depends(require_auth),
):
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Allowed types: {ALLOWED_TYPES}")
    result = generate_presigned_url(user.id, content_type)
    return result
