# app/core/dependencies.py
"""
Auto-D Kenya - Core Authentication Dependencies
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.database import get_supabase
from app.core.exceptions import UnauthorizedException
from app.core.security import decode_token

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    Return the currently authenticated user.
    """

    if credentials is None:
        raise UnauthorizedException("Authentication required")

    payload = await decode_token(credentials.credentials)

    if payload is None:
        raise UnauthorizedException("Invalid or expired token")

    user_id = payload.get("sub")

    if not user_id:
        raise UnauthorizedException("Invalid token")

    try:
        supabase = get_supabase()

        result = (
            supabase.table("users")
            .select("*")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        if result.data:
            user = result.data[0]

            return {
                "id": user.get("id"),
                "email": user.get("email"),
                "full_name": (
                    user.get("full_name")
                    or user.get("name")
                    or user.get("display_name")
                ),
                "account_type": user.get("account_type", "individual"),
                "is_active": user.get("is_active", True),
                "payload": payload,
            }

    except Exception as e:
        logger.warning(f"Database lookup failed: {e}")

    metadata = payload.get("user_metadata", {})

    return {
        "id": user_id,
        "email": payload.get("email") or metadata.get("email"),
        "full_name": metadata.get("full_name") or metadata.get("name"),
        "account_type": metadata.get("account_type", "individual"),
        "is_active": True,
        "payload": payload,
    }


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """
    Return authenticated user or None.
    """

    if credentials is None:
        return None

    try:
        return await get_current_user(credentials)
    except Exception:
        return None


async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
):
    """
    Ensure user is active.
    """

    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive account",
        )

    return current_user


async def get_current_admin_user(
    current_user: dict = Depends(get_current_user),
):
    """
    Ensure user is an administrator.
    """

    account_type = current_user.get("account_type", "")

    if account_type not in {
        "admin",
        "super_admin",
        "staff",
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return current_user


async def get_supabase_client():
    """
    Dependency for Supabase client.
    """
    return get_supabase()
