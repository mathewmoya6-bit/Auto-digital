"""
Auto-D Kenya - Authentication Dependencies
==========================================

FastAPI dependency injection for authentication.

Provides:
- Current authenticated user
- Optional authentication
- Active user validation
- Admin validation
- Supabase client dependency
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import get_supabase
from app.core.exceptions import UnauthorizedException
from app.core.security import decode_token

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Security Scheme
# ---------------------------------------------------------------------

security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------
# Current User
# ---------------------------------------------------------------------

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    Returns the authenticated user.

    Priority:
    1. Validate JWT.
    2. Load user from database.
    3. Fall back to JWT claims.
    """

    if credentials is None:
        raise UnauthorizedException("Authentication required")

    token = credentials.credentials

    try:
        payload = decode_token(token)

    except Exception as exc:
        logger.warning("Authentication failed: %s", exc)
        raise UnauthorizedException("Invalid or expired token")

    user_id = payload.get("sub")

    if not user_id:
        raise UnauthorizedException("Invalid token payload")

    metadata = payload.get("user_metadata", {})

    try:
        supabase = get_supabase()

        response = (
            supabase
            .table("users")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )

        if response.data:
            user = response.data

            return {
                "id": user.get("id"),
                "email": user.get("email"),
                "full_name": (
                    user.get("full_name")
                    or user.get("display_name")
                    or user.get("name")
                ),
                "account_type": user.get(
                    "account_type",
                    "individual",
                ),
                "is_active": user.get(
                    "is_active",
                    True,
                ),
                "payload": payload,
            }

    except Exception as exc:
        logger.warning(
            "Unable to load user from database: %s",
            exc,
        )

    # -----------------------------------------------------------------
    # Fallback to JWT Claims
    # -----------------------------------------------------------------

    return {
        "id": user_id,
        "email": payload.get("email") or metadata.get("email"),
        "full_name": (
            metadata.get("full_name")
            or metadata.get("name")
        ),
        "account_type": metadata.get(
            "account_type",
            "individual",
        ),
        "is_active": True,
        "payload": payload,
    }


# ---------------------------------------------------------------------
# Optional Authentication
# ---------------------------------------------------------------------

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """
    Returns the authenticated user or None.
    """

    if credentials is None:
        return None

    try:
        return await get_current_user(credentials)

    except Exception:
        return None


# ---------------------------------------------------------------------
# Active User
# ---------------------------------------------------------------------

async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Ensure account is active.
    """

    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    return current_user


# ---------------------------------------------------------------------
# Admin User
# ---------------------------------------------------------------------

async def get_current_admin_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Ensure user has administrator privileges.
    """

    allowed_roles = {
        "admin",
        "super_admin",
        "staff",
    }

    if current_user.get("account_type") not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required.",
        )

    return current_user


# ---------------------------------------------------------------------
# Supabase Dependency
# ---------------------------------------------------------------------

def get_supabase_client():
    """
    Returns the configured Supabase client.
    """
    return get_supabase()


# ---------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------

__all__ = [
    "security",
    "get_current_user",
    "get_current_user_optional",
    "get_current_active_user",
    "get_current_admin_user",
    "get_supabase_client",
]
