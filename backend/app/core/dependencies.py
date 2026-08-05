# app/core/dependencies.py
# ================================================================
# Auto-D Kenya - Core Dependencies
# ================================================================

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------
# Security
# ---------------------------------------------------------------

security = HTTPBearer(auto_error=False)


# ================================================================
# USERS
# ================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    Validate JWT token and return the authenticated user.
    Uses Supabase Auth for token verification.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    token = credentials.credentials
    supabase = get_supabase()

    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database unavailable",
        )

    try:
        # Verify the access token with Supabase Auth
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
                return profile.data

        except Exception:
            logger.exception("Failed to load profile")

        # Fallback to auth user info
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
        logger.exception("Authentication failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication: {str(e)}",
        )


# ================================================================
# OPTIONAL USER
# ================================================================

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Dict[str, Any]]:
    """
    Returns the authenticated user if a valid token is supplied.
    Otherwise returns None.
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials)
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

    Usage:
        @router.get("/items")
        async def list_items(pagination: dict = Depends(get_pagination_params)):
            offset = pagination["offset"]
            limit = pagination["limit"]
    """
    # Validate
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

    Usage:
        @router.get("/search")
        async def search_items(search: dict = Depends(get_search_params)):
            query = search["q"]
            fields = search["fields"]
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

    Usage:
        @router.get("/items")
        async def list_items(filters: dict = Depends(get_filter_params)):
            # filters = {"status": "active", "category": "cars"}
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

    Returns a simple rate limiter that can be used to check
    request rates per client.
    """
    # This is a placeholder - actual rate limiting is implemented
    # in the M-Pesa router using the rate_limit() function
    return {
        "enabled": True,
        "requests": settings.RATE_LIMIT_REQUESTS,
        "window": settings.RATE_LIMIT_WINDOW_SECONDS,
    }


# ================================================================
# TOKENS
# ================================================================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT access token.
    """
    payload = data.copy()

    expire = (
        datetime.utcnow()
        + (
            expires_delta
            or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
    )

    payload.update(
        {
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
        }
    )

    jwt_secret = settings.get_jwt_secret()

    if not jwt_secret:
        raise RuntimeError("JWT secret not configured")

    return jwt.encode(
        payload,
        jwt_secret,
        algorithm=settings.ALGORITHM,
    )


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT refresh token.
    """
    payload = data.copy()

    expire = (
        datetime.utcnow()
        + (
            expires_delta
            or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
    )

    payload.update(
        {
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
        }
    )

    jwt_secret = settings.get_jwt_secret()

    if not jwt_secret:
        raise RuntimeError("JWT secret not configured")

    return jwt.encode(
        payload,
        jwt_secret,
        algorithm=settings.ALGORITHM,
    )


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode JWT token.
    """
    jwt_secret = settings.get_jwt_secret()

    if not jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret not configured",
        )

    try:
        return jwt.decode(
            token,
            jwt_secret,
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False},
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
        )


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
    "create_access_token",
    "create_refresh_token",
    "verify_token",
]
