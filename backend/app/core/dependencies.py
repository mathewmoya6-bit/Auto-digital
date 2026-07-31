# app/core/dependencies.py
# Auto-D Kenya - Dependency Injection
# ================================================================
# TYPE: CORE - FastAPI dependency injection

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import decode_token
from app.core.database import get_supabase
from app.core.exceptions import UnauthorizedException

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Get current authenticated user.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        dict: User information
        
    Raises:
        UnauthorizedException: If token is invalid
    """
    token = credentials.credentials
    
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id:
            raise UnauthorizedException("Invalid token: missing user ID")
        
        return {
            "id": user_id,
            "email": email,
            "payload": payload
        }
        
    except ValueError as e:
        raise UnauthorizedException(str(e))
    except Exception as e:
        raise UnauthorizedException(f"Authentication failed: {str(e)}")


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Get current user if authenticated, otherwise None.
    
    Args:
        credentials: HTTP Bearer credentials (optional)
        
    Returns:
        Optional[dict]: User information or None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except UnauthorizedException:
        return None


async def get_supabase_client():
    """
    Get Supabase client for dependency injection.
    
    Returns:
        Client: Supabase client
    """
    return get_supabase()
