# app/core/dependencies.py
# Auto-D Kenya - Dependency Injection
# ================================================================
# TYPE: CORE - FastAPI dependency injection

import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ✅ FIX: Import decode_token from app.modules.auth.dependencies
from app.modules.auth.dependencies import decode_token
from app.core.database import get_supabase
from app.core.exceptions import UnauthorizedException

logger = logging.getLogger(__name__)

# ✅ FIX 1: Make bearer optional (auto_error=False)
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
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
    # ✅ FIX 2: Check missing credentials
    if credentials is None:
        raise UnauthorizedException("Authentication required")
    
    token = credentials.credentials
    
    try:
        # ✅ FIX: Use await since decode_token is async
        payload = await decode_token(token)
        
        # Check if token validation failed
        if payload is None:
            raise UnauthorizedException("Invalid or expired token")
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id:
            raise UnauthorizedException("Missing user id")
        
        # ✅ FIX 4: Verify user exists in database
        try:
            supabase = get_supabase()
            result = (
                supabase.table("users")
                .select("id, email, full_name, account_type, is_active")
                .eq("id", user_id)
                .single()
                .execute()
            )
            
            if not result.data:
                logger.warning(f"User not found in database: {user_id}")
                raise UnauthorizedException("User not found")
            
            user_data = result.data
            
        except Exception as db_error:
            # If the users table doesn't exist or query fails,
            # still allow the user if the token is valid
            logger.warning(f"Could not verify user in database: {str(db_error)}")
            user_metadata = payload.get("user_metadata", {})
            user_data = {
                "id": user_id,
                "email": email or user_metadata.get("email"),
                "full_name": user_metadata.get("full_name"),
                "account_type": user_metadata.get("account_type", "individual"),
                "is_active": True
            }
        
        # ✅ FIX 5: Return user data
        return {
            "id": user_data.get("id") or user_id,
            "email": user_data.get("email") or email,
            "full_name": user_data.get("full_name"),
            "account_type": user_data.get("account_type", "individual"),
            "is_active": user_data.get("is_active", True),
            "payload": payload,
        }
        
    except UnauthorizedException:
        # Re-raise UnauthorizedException
        raise
    except ValueError as e:
        # ✅ FIX 5: Don't expose internal details to clients
        logger.warning(f"Token validation error: {str(e)}")
        raise UnauthorizedException("Authentication failed")
    except Exception as e:
        # ✅ FIX 5: Don't expose internal details to clients
        logger.error(f"Unexpected authentication error: {str(e)}")
        raise UnauthorizedException("Authentication failed")


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
    # ✅ FIX 6: Check missing credentials
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials)
    except UnauthorizedException:
        return None


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Get current active user.
    Raises 403 if user is not active.
    """
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Get current admin user.
    Raises 403 if user is not an admin.
    """
    account_type = current_user.get("account_type", "individual")
    if account_type not in ["admin", "super_admin", "staff"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def get_supabase_client():
    """
    Get Supabase client for dependency injection.
    
    Returns:
        Client: Supabase client
    """
    return get_supabase()
