from fastapi import Depends, HTTPException, Request, status
from app.auth import get_current_user  # existing function
from app.models.user import User
import uuid


async def require_auth(user: User = Depends(get_current_user)) -> User:
    """Ensures user is authenticated and active."""
    if hasattr(user, 'is_active') and not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
    return user


async def require_admin(user: User = Depends(require_auth)) -> User:
    """Ensures user is an admin."""
    if not getattr(user, 'is_admin', False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def require_owner(user_id_param: str = "user_id"):
    """Factory: returns a dependency that checks JWT user matches the path user_id."""
    async def _check(request: Request, user: User = Depends(require_auth)):
        path_user_id = request.path_params.get(user_id_param)
        if path_user_id and uuid.UUID(path_user_id) != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return user
    return _check


def require_owner_or_admin(user_id_param: str = "user_id"):
    """Factory: owner OR admin can access."""
    async def _check(request: Request, user: User = Depends(require_auth)):
        path_user_id = request.path_params.get(user_id_param)
        is_owner = path_user_id and uuid.UUID(path_user_id) == user.id
        is_admin = getattr(user, 'is_admin', False)
        if not is_owner and not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return user
    return _check
