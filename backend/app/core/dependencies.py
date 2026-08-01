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
from typing import Optional, Dict, Any
from datetime import datetime

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
                "app_metadata": user.get("app_metadata", {}),
                "user_metadata": user.get("user_metadata", {}),
                "created_at": user.get("created_at"),
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
        "app_metadata": payload.get("app_metadata", {}),
        "user_metadata": metadata,
        "created_at": payload.get("created_at"),
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
# Admin User (Legacy)
# ---------------------------------------------------------------------

async def get_current_admin_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Ensure user has administrator privileges.

    Deprecated: Use require_admin() instead.
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
# Require Admin (Recommended)
# ---------------------------------------------------------------------

async def require_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Require admin role for access.
    
    Checks both app_metadata and user_metadata for admin role.
    
    Returns:
        dict: User information if admin
        
    Raises:
        HTTPException: If user is not an admin
    """
    # Check app_metadata
    app_metadata = current_user.get("app_metadata", {})
    role = app_metadata.get("role")
    
    # Check user_metadata if not found
    if not role:
        user_metadata = current_user.get("user_metadata", {})
        role = user_metadata.get("role")
    
    # Check account_type
    if not role:
        account_type = current_user.get("account_type")
        if account_type in ["admin", "super_admin", "staff"]:
            role = account_type
    
    if role not in ["admin", "super_admin", "staff"]:
        logger.warning(
            f"User {current_user.get('email', 'unknown')} "
            f"attempted admin access without admin role"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


# ---------------------------------------------------------------------
# Require Service Access
# ---------------------------------------------------------------------

async def require_service_access(
    service_code: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Check if user has access to a specific service.
    
    Args:
        service_code: Service code (e.g., 'valuation', 'mileage')
        current_user: Current authenticated user
        
    Returns:
        dict: User information if access granted
        
    Raises:
        HTTPException: If user does not have access
    """
    try:
        supabase = get_supabase()
        
        # Get service ID
        service_response = (
            supabase
            .table("services")
            .select("id")
            .eq("code", service_code)
            .eq("active", True)
            .execute()
        )
        
        if not service_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service '{service_code}' not found"
            )
        
        service_id = service_response.data[0]["id"]
        user_id = current_user.get("id")
        
        # Check if user has access
        user_service_response = (
            supabase
            .table("user_services")
            .select("status, expires_at")
            .eq("user_id", user_id)
            .eq("service_id", service_id)
            .execute()
        )
        
        if not user_service_response.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to '{service_code}' required. Please purchase this service."
            )
        
        record = user_service_response.data[0]
        status = record.get("status")
        expires_at = record.get("expires_at")
        
        # Check if expired
        if expires_at:
            try:
                expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if datetime.utcnow() > expires:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Access to '{service_code}' has expired. Please renew."
                    )
            except:
                pass
        
        # Check if active
        if status not in ["active", "completed", "paid", "success"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to '{service_code}' is not active. Please purchase this service."
            )
        
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking service access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check service access: {str(e)}"
        )


# ---------------------------------------------------------------------
# Get User ID
# ---------------------------------------------------------------------

async def get_current_user_id(
    current_user: dict = Depends(get_current_user),
) -> str:
    """
    Get current user ID.
    
    Returns:
        str: User ID
    """
    return current_user.get("id")


# ---------------------------------------------------------------------
# Supabase Client
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
    "require_admin",
    "require_service_access",
    "get_current_user_id",
    "get_supabase_client",
]
