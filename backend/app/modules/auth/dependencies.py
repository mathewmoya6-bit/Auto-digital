# app/modules/auth/dependencies.py
"""Authentication dependencies for Auto-D Kenya"""
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import logging

from supabase import Client
from app.core.database import get_supabase
from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── SECURITY SCHEMES ────────────────────────────────────────────

security = HTTPBearer(auto_error=False)


# ─── TOKEN DECODER ────────────────────────────────────────────────

async def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Validate Supabase access token using Supabase's built-in validation.
    
    This is the ONLY token validation function in the application.
    It uses supabase.auth.get_user() which validates the token against
    Supabase's internal validation rules (expiry, signature, etc.).
    """
    try:
        supabase: Client = get_supabase()
        response = supabase.auth.get_user(token)

        if response and response.user:
            return {
                "sub": response.user.id,
                "email": response.user.email,
                "user_metadata": response.user.user_metadata or {},
                "aud": response.user.aud,
                "role": response.user.role,
                "created_at": response.user.created_at,
                "confirmed_at": getattr(response.user, 'confirmed_at', None),
                "last_sign_in_at": getattr(response.user, 'last_sign_in_at', None),
            }

        logger.warning("Invalid token: No user data returned")
        return None

    except Exception as e:
        logger.warning(f"Token validation failed: {str(e)}")
        return None


# ─── DEPENDENCIES ────────────────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Get current authenticated user from Supabase token.
    Raises 401 if token is invalid or missing.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = await decode_token(credentials.credentials)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Get current user from Supabase token if present.
    Returns None if no token or invalid token.
    """
    if credentials is None:
        return None
    
    payload = await decode_token(credentials.credentials)
    return payload


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current active user.
    Raises 403 if user is not active.
    """
    # Check if user is confirmed (email confirmed)
    if not current_user.get("confirmed_at"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not confirmed. Please verify your email."
        )
    return current_user


async def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current admin user.
    Raises 403 if user is not an admin.
    """
    # Check admin status from user_metadata or role
    user_metadata = current_user.get("user_metadata", {})
    role = current_user.get("role", "")
    account_type = user_metadata.get("account_type", "individual")
    
    if account_type not in ["admin", "super_admin", "staff"] and role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def get_current_super_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current super admin user.
    Raises 403 if user is not a super admin.
    """
    user_metadata = current_user.get("user_metadata", {})
    account_type = user_metadata.get("account_type", "individual")
    role = current_user.get("role", "")
    
    if account_type != "super_admin" and role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )
    return current_user


# ─── USER LOOKUP HELPERS ──────────────────────────────────────────

async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID from database (supports UUID)"""
    try:
        supabase = get_supabase()
        result = supabase.table("users")\
            .select("*")\
            .eq("id", user_id)\
            .execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting user by ID: {str(e)}")
        return None


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email from database"""
    try:
        supabase = get_supabase()
        result = supabase.table("users")\
            .select("*")\
            .eq("email", email)\
            .execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting user by email: {str(e)}")
        return None


# ─── PERMISSION CHECKERS ─────────────────────────────────────────

def require_permission(permission: str):
    """
    Dependency factory for permission checking.
    Usage: @router.get("/endpoint", dependencies=[Depends(require_permission("users:read"))])
    """
    async def permission_dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_metadata = current_user.get("user_metadata", {})
        permissions = user_metadata.get("permissions", [])
        
        if not permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        
        return current_user
    
    return permission_dependency


def require_role(role: str):
    """
    Dependency factory for role checking.
    Usage: @router.get("/endpoint", dependencies=[Depends(require_role("admin"))])
    """
    async def role_dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_metadata = current_user.get("user_metadata", {})
        user_role = user_metadata.get("role", current_user.get("role", "individual"))
        
        if user_role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required"
            )
        return current_user
    
    return role_dependency


def require_any_role(roles: list):
    """
    Dependency factory for checking any of multiple roles.
    Usage: @router.get("/endpoint", dependencies=[Depends(require_any_role(["admin", "manager"]))])
    """
    async def role_dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_metadata = current_user.get("user_metadata", {})
        user_role = user_metadata.get("role", current_user.get("role", "individual"))
        
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of roles {roles} required"
            )
        return current_user
    
    return role_dependency


# ─── RATE LIMITING (Optional) ────────────────────────────────────

class RateLimiter:
    """Simple rate limiter for API endpoints"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self._cache = {}  # In production, use Redis
    
    async def __call__(self, request: Request):
        # Get client identifier
        client_id = request.client.host if request.client else "unknown"
        current_time = datetime.utcnow().timestamp()
        
        # Initialize or clean old entries
        if client_id not in self._cache:
            self._cache[client_id] = []
        
        # Remove old entries (older than 1 minute)
        minute_ago = current_time - 60
        self._cache[client_id] = [
            t for t in self._cache[client_id] 
            if t > minute_ago
        ]
        
        # Check rate limit
        if len(self._cache[client_id]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute."
            )
        
        # Add current request
        self._cache[client_id].append(current_time)
        
        return True


def rate_limit(requests_per_minute: int = 60):
    """Rate limit dependency factory"""
    limiter = RateLimiter(requests_per_minute)
    return limiter
