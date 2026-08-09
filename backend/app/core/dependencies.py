# app/core/dependencies.py
# ================================================================
# Auto-D Kenya - Core Dependencies
# ================================================================

import logging
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------
# Security
# ---------------------------------------------------------------

security = HTTPBearer(auto_error=False)

# Must match the cookie name set in app/modules/auth/router.py
ACCESS_COOKIE_NAME = "sb_access_token"


# ================================================================
# USERS
# ================================================================

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    Validate Supabase JWT token and return the authenticated user.

    Token is resolved in this order:
      1. Authorization: Bearer <token> header (used by SPA fetch/XHR calls)
      2. HttpOnly session cookie (used by plain browser navigation,
         e.g. someone typing a page URL directly, where no custom
         header is attached)

    Uses Supabase Auth's get_user() which validates the token
    and returns the user from Supabase's internal auth system.
    """
    token = credentials.credentials if credentials else request.cookies.get(ACCESS_COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    supabase = get_supabase()

    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database unavailable",
        )

    try:
        # Verify the access token with Supabase Auth
        # This validates the token and returns the user
        auth_response = supabase.auth.get_user(token)

        if not auth_response or not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication",
            )

        user = auth_response.user

        # Look up the user's profile using user_id
        try:
            profile = (
                supabase.table("profiles")
                .select("*")
                .eq("user_id", user.id)
                .maybe_single()
                .execute()
            )

            if profile and profile.data:
                logger.debug(f"Found profile for user: {user.id}")
                return profile.data

        except Exception:
            logger.exception("Failed to load profile")

        # Fallback to auth user info if no profile exists
        return {
            "id": user.id,
            "user_id": user.id,
            "email": user.email,
            "role": (
                user.app_metadata.get("role", "user")
                if user.app_metadata
                else "user"
            ),
            "is_active": True,
        }

    except HTTPException:
        raise

    except Exception as e:
        # Catch all authentication errors including:
        # - Session from session_id claim in JWT does not exist
        # - Invalid token
        # - Expired token
        logger.exception(f"Authentication failed: {str(e)}")

        # Check for specific Supabase error messages
        error_message = str(e).lower()
        if "session" in error_message and "does not exist" in error_message:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please log in again.",
            )
        elif "expired" in error_message:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired. Please refresh or log in again.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication. Please log in again.",
            )


# ================================================================
# OPTIONAL USER
# ================================================================

async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Dict[str, Any]]:
    """
    Returns the authenticated user if a valid token is supplied
    (header or cookie). Otherwise returns None.
    """
    token = credentials.credentials if credentials else request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        return None

    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None


# ================================================================
# ACTIVE USER
# ================================================================

async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Returns the current user if their account is active.
    """
    if current_user.get("is_active") is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return current_user


# ================================================================
# ADMIN
# ================================================================

async def get_current_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Returns the current user if they have admin privileges.
    """
    role = current_user.get("role", "user")

    if role not in {"admin", "super_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user


# ================================================================
# SUPER ADMIN
# ================================================================

async def get_current_super_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Returns the current user if they have super admin privileges.
    """
    role = current_user.get("role", "user")

    if role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )

    return current_user


# ================================================================
# BACKWARDS COMPATIBILITY
# ================================================================

get_admin_user = get_current_admin
get_current_admin_user = get_current_admin
get_current_super_admin_user = get_current_super_admin


# ================================================================
# DATABASE
# ================================================================

async def get_db():
    """
    Get Supabase database client.
    """
    supabase = get_supabase()

    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database unavailable",
        )

    return supabase


# ================================================================
# ROLE-BASED AUTHORIZATION
# ================================================================

def require_roles(roles: List[str]):
    """
    Factory for role-based authorization.

    Usage:
        @router.get("/admin")
        async def admin_endpoint(
            current_user: dict = Depends(require_roles(["admin", "super_admin"]))
        ):
            return {"message": "Welcome admin"}
    """
    async def role_checker(
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        user_role = current_user.get("role", "user")

        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(roles)}",
            )

        return current_user

    return role_checker


def require_permission(permission: str):
    """
    Factory for permission-based authorization.

    Usage:
        @router.get("/protected")
        async def protected_endpoint(
            current_user: dict = Depends(require_permission("view_reports"))
        ):
            return {"message": "Access granted"}
    """
    async def permission_checker(
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        permissions = current_user.get("permissions", [])

        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required permission: {permission}",
            )

        return current_user

    return permission_checker


# ================================================================
# PAGINATION
# ================================================================

async def get_pagination_params(
    page: int = 1,
    limit: int = 20,
) -> Dict[str, int]:
    """
    Get pagination parameters from query string.
    """
    if page < 1:
        page = 1

    if limit < 1:
        limit = 1

    if limit > 100:
        limit = 100

    return {
        "page": page,
        "limit": limit,
        "offset": (page - 1) * limit,
    }


# ================================================================
# SEARCH
# ================================================================

async def get_search_params(
    q: Optional[str] = None,
    search_fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Get search parameters from query string.
    """
    return {
        "q": q or "",
        "fields": search_fields or [],
    }


# ================================================================
# FILTERS
# ================================================================

async def get_filter_params(
    request: Request,
    filter_prefix: str = "filter_",
) -> Dict[str, Any]:
    """
    Get filter parameters from query string.
    """
    filters = {}

    for key, value in request.query_params.items():
        if key.startswith(filter_prefix):
            filter_key = key[len(filter_prefix):]
            filters[filter_key] = value

    return filters


# ================================================================
# RATE LIMITER
# ================================================================

async def get_rate_limiter() -> Dict[str, Any]:
    """
    Get rate limiter instance.
    """
    return {
        "enabled": True,
        "requests": settings.RATE_LIMIT_REQUESTS,
        "window": settings.RATE_LIMIT_WINDOW_SECONDS,
    }


# ================================================================
# EXPORTS
# ================================================================

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
]
