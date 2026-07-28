"""
Core Dependencies - Authentication and authorization dependencies for FastAPI
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.database import supabase
from app.core.config import settings

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Get the current user from the JWT token.
    Raises 401 if invalid or expired.
    """
    token = credentials.credentials
    
    try:
        # Verify the token with Supabase
        response = supabase.auth.get_user(token)
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = response.user
        return {
            "id": user.id,
            "email": user.email,
            "user_metadata": user.user_metadata,
            "app_metadata": user.app_metadata,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Get the current user from the JWT token, or None if not authenticated.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


async def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Get the current admin user.
    Raises 401 if not authenticated or not an admin.
    """
    user = await get_current_user(credentials)
    
    # Check if user has admin role
    is_admin = user.get("app_metadata", {}).get("role") in ["admin", "super_admin"]
    if not is_admin:
        # Also check user_metadata
        is_admin = user.get("user_metadata", {}).get("role") in ["admin", "super_admin"]
    
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    return user
