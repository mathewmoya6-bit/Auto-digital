"""
Authentication Dependencies
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import supabase

# Required authentication
required_security = HTTPBearer(auto_error=True)

# Optional authentication
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(required_security),
) -> dict:
    """
    Authenticate a user using a Supabase JWT.
    """

    token = credentials.credentials

    try:
        response = supabase.auth.get_user(token)

        if response is None or response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = response.user

        return {
            "id": user.id,
            "email": user.email,
            "user_metadata": user.user_metadata or {},
            "app_metadata": user.app_metadata or {},
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
) -> Optional[dict]:
    """
    Returns None if no Authorization header is supplied.
    """

    if credentials is None:
        return None

    return await get_current_user(credentials)


async def get_current_admin_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Require an authenticated administrator.
    """

    role = (
        current_user.get("app_metadata", {}).get("role")
        or current_user.get("user_metadata", {}).get("role")
    )

    if role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )

    return current_user
