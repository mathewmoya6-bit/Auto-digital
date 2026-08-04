# app/core/dependencies.py

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import jwt

from app.core.config import settings
from app.core.database import get_supabase

security = HTTPBearer(auto_error=False)


# ============================================================
# USERS
# ============================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        supabase = get_supabase()

        result = (
            supabase
            .table("users")
            .select("*")
            .eq("id", user_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=401, detail="User not found")

        return result.data[0]

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication"
        )


# ============================================================
# OPTIONAL USER
# ============================================================

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:

    if credentials is None:
        return None

    try:
        return await get_current_user(credentials)
    except Exception:
        return None


# ============================================================
# ACTIVE USER
# ============================================================

async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
):

    if not current_user.get("is_active", True):
        raise HTTPException(403, "Inactive user")

    return current_user


# ============================================================
# ADMIN
# ============================================================

async def get_current_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
):

    if current_user.get("role") not in [
        "admin",
        "super_admin"
    ]:
        raise HTTPException(403, "Admin access required")

    return current_user


# backwards compatibility

get_admin_user = get_current_admin
get_current_admin_user = get_current_admin


# ============================================================
# SUPER ADMIN
# ============================================================

async def get_current_super_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
):

    if current_user.get("role") != "super_admin":
        raise HTTPException(403, "Super Admin required")

    return current_user


get_current_super_admin_user = get_current_super_admin


# ============================================================
# DATABASE
# ============================================================

async def get_db():
    yield get_supabase()


# ============================================================
# PERMISSIONS
# ============================================================

def require_roles(roles: List[str]):

    async def checker(
        current_user=Depends(get_current_user)
    ):

        if current_user.get("role") not in roles:
            raise HTTPException(403, "Permission denied")

        return current_user

    return checker


def require_permission(permission: str):

    async def checker(
        current_user=Depends(get_current_user)
    ):
        return current_user

    return checker


# ============================================================
# PAGINATION
# ============================================================

def get_pagination_params(
    page: int = 1,
    limit: int = 20
):

    return {
        "page": page,
        "limit": limit,
        "offset": (page - 1) * limit
    }


def get_search_params(search: Optional[str] = None):

    return {
        "search": search
    }


def get_filter_params(filters=None):

    return {
        "filters": filters or {}
    }


# ============================================================
# RATE LIMITER
# ============================================================

class RateLimiter:

    async def __call__(self, request: Request):
        return True


def get_rate_limiter(*args, **kwargs):
    return RateLimiter()


# ============================================================
# TOKENS
# ============================================================

def create_access_token(data: dict):

    payload = data.copy()

    payload["exp"] = datetime.utcnow() + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return jwt.encode(
        payload,
        settings.SUPABASE_JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token(data: dict):

    payload = data.copy()

    payload["type"] = "refresh"

    payload["exp"] = datetime.utcnow() + timedelta(days=30)

    return jwt.encode(
        payload,
        settings.SUPABASE_JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )


def verify_token(token: str):

    return jwt.decode(
        token,
        settings.SUPABASE_JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM]
    )


__all__ = [
    "security",
    "get_current_user",
    "get_current_user_optional",
    "get_current_active_user",
    "get_current_admin",
    "get_current_admin_user",
    "get_admin_user",
    "get_current_super_admin",
    "get_current_super_admin_user",
    "get_db",
    "require_roles",
    "require_permission",
    "get_pagination_params",
    "get_search_params",
    "get_filter_params",
    "get_rate_limiter",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
]
