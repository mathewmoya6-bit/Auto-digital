"""
Auto-D Kenya - Authentication Dependencies
==========================================

Authentication dependency injection for FastAPI.

This module is responsible only for:
- Getting the authenticated user
- Loading the user from the database
- Authorization (admin, active user, roles)

JWT creation/verification is handled by:
    app.core.security
"""

import logging
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import get_supabase
from app.core.security import decode_token

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


# ============================================================
# Database Helpers
# ============================================================

async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch user by UUID."""

    try:
        supabase = get_supabase()

        result = (
            supabase
            .table("users")
            .select("*")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]

        return None

    except Exception as e:
        logger.error(f"Database error: {e}")
        return None


# ============================================================
# Authentication
# ============================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """
    Return authenticated user.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token",
            )

        user = await get_user_by_id(user_id)

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="User not found",
            )

        return user

    except ValueError as e:
        logger.warning(str(e))

        raise HTTPException(
            status_code=401,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Dict[str, Any]]:
    """
    Return authenticated user or None.
    """

    if credentials is None:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# ============================================================
# User Status
# ============================================================

async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:

    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=403,
            detail="Inactive account",
        )

    return current_user


async def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:

    account_type = current_user.get("account_type", "").lower()

    if account_type not in (
        "admin",
        "super_admin",
        "staff",
    ):
        raise HTTPException(
            status_code=403,
            detail="Administrator privileges required",
        )

    return current_user


async def get_current_super_admin(
    current_user: Dict[str, Any] = Depends(get_current_admin_user),
) -> Dict[str, Any]:

    if current_user.get("account_type") != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Super administrator required",
        )

    return current_user


# ============================================================
# Role Helpers
# ============================================================

def require_role(role: str):
    """
    Require a single role.
    """

    async def checker(
        current_user: Dict[str, Any] = Depends(get_current_user),
    ):

        if current_user.get("role") != role:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{role}' required",
            )

        return current_user

    return checker


def require_any_role(roles: list[str]):
    """
    Require one of several roles.
    """

    async def checker(
        current_user: Dict[str, Any] = Depends(get_current_user),
    ):

        if current_user.get("role") not in roles:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions",
            )

        return current_user

    return checker


def require_permission(permission: str):
    """
    Require a permission.
    """

    async def checker(
        current_user: Dict[str, Any] = Depends(get_current_user),
    ):

        permissions = current_user.get("permissions", [])

        if permission not in permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{permission}' required",
            )

        return current_user

    return checker


# ============================================================
# Simple Rate Limiter
# ============================================================

class RateLimiter:

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.cache = {}

    async def __call__(self, request: Request):

        from datetime import datetime

        ip = request.client.host if request.client else "unknown"

        now = datetime.utcnow().timestamp()

        self.cache.setdefault(ip, [])

        self.cache[ip] = [
            t for t in self.cache[ip]
            if now - t < 60
        ]

        if len(self.cache[ip]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Too many requests",
            )

        self.cache[ip].append(now)

        return True


def rate_limit(requests_per_minute: int = 60):
    return RateLimiter(requests_per_minute)
