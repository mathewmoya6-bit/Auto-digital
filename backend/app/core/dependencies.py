# app/core/dependencies.py

"""
Auto-D Kenya - Dependencies
===========================

FastAPI dependency injection functions for authentication, authorization,
and database operations.
"""

from typing import Optional, List, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import logging
import jwt
from jwt.exceptions import PyJWTError

from app.core.config import settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)
security = HTTPBearer()


# =============================================================================
# Authentication Dependencies
# =============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get the current authenticated user from the JWT token.
    
    Returns:
        Dict containing user information
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    
    try:
        # Decode JWT token - try Supabase JWT secret first
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )
        except jwt.InvalidTokenError:
            # Fallback to JWT_SECRET_KEY if available
            if hasattr(settings, 'JWT_SECRET_KEY') and settings.JWT_SECRET_KEY:
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM]
                )
            else:
                raise
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        supabase = get_supabase()
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = response.data[0]
        
        # Check if user is active
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current active user.
    
    Returns:
        Dict containing user information
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Get current user if authenticated, otherwise return None.
    Useful for endpoints that work for both authenticated and unauthenticated users.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


async def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current user and verify they are an admin.
    
    Returns:
        Dict containing user information
        
    Raises:
        HTTPException: If user is not an admin
    """
    # Check if user is admin
    is_admin = (
        current_user.get("is_admin", False) or 
        current_user.get("role") in ["admin", "super_admin"]
    )
    
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user


async def get_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Alias for get_current_admin_user.
    """
    return await get_current_admin_user(current_user)


async def get_current_super_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current user and verify they are a super admin.
    
    Returns:
        Dict containing user information
        
    Raises:
        HTTPException: If user is not a super admin
    """
    if current_user.get("role") != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )
    
    return current_user


# =============================================================================
# Database Dependencies
# =============================================================================

async def get_db():
    """
    Get database connection.
    
    Yields:
        Supabase client instance
    """
    supabase = get_supabase()
    try:
        yield supabase
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise


# =============================================================================
# Permission Dependencies
# =============================================================================

def require_permission(permission: str):
    """
    Dependency factory for checking user permissions.
    
    Args:
        permission: Required permission string
    
    Returns:
        Dependency function
    """
    async def _require_permission(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """
        Check if user has the required permission.
        """
        # Admin users have all permissions
        if current_user.get("is_admin", False) or current_user.get("role") in ["admin", "super_admin"]:
            return current_user
        
        # Get user permissions from database
        supabase = get_supabase()
        response = supabase.table("user_permissions").select("permission").eq("user_id", current_user["id"]).execute()
        
        user_permissions = [p["permission"] for p in response.data]
        
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        
        return current_user
    
    return _require_permission


def require_roles(allowed_roles: List[str]):
    """
    Dependency factory for checking user roles.
    
    Args:
        allowed_roles: List of allowed role names
    
    Returns:
        Dependency function
    """
    async def _require_roles(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """
        Check if user has one of the allowed roles.
        """
        user_role = current_user.get("role", "user")
        
        # Admin users have access to everything
        if current_user.get("is_admin", False) or user_role == "super_admin":
            return current_user
        
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role}' not allowed. Required: {', '.join(allowed_roles)}"
            )
        
        return current_user
    
    return _require_roles


# =============================================================================
# Pagination Dependencies
# =============================================================================

def get_pagination_params(
    page: int = 1,
    limit: int = 20,
    sort_by: Optional[str] = None,
    sort_order: str = "desc"
) -> Dict[str, Any]:
    """
    Get pagination parameters from query string.
    
    Args:
        page: Page number (default: 1)
        limit: Items per page (default: 20)
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc', default: 'desc')
    
    Returns:
        Dict containing pagination parameters
    """
    # Validate parameters
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 20
    if sort_order not in ["asc", "desc"]:
        sort_order = "desc"
    
    offset = (page - 1) * limit
    
    return {
        "page": page,
        "limit": limit,
        "offset": offset,
        "sort_by": sort_by,
        "sort_order": sort_order
    }


def get_search_params(
    search: Optional[str] = None,
    search_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get search parameters from query string.
    
    Args:
        search: Search query string
        search_fields: Fields to search in
    
    Returns:
        Dict containing search parameters
    """
    return {
        "search": search,
        "search_fields": search_fields or ["name", "description"]
    }


def get_filter_params(
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get filter parameters from query string.
    
    Args:
        filters: Dictionary of filter parameters
    
    Returns:
        Dict containing filter parameters
    """
    return {"filters": filters or {}}


# =============================================================================
# Rate Limiting Dependencies
# =============================================================================

class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    async def __call__(self, request: Request) -> bool:
        """
        Check if request is within rate limit.
        
        Args:
            request: FastAPI request object
        
        Returns:
            True if within limit, raises HTTPException if exceeded
        
        Raises:
            HTTPException: If rate limit exceeded
        """
        client_ip = request.client.host if request.client else "unknown"
        current_time = datetime.utcnow().timestamp()
        
        # Clean up old entries
        if client_ip in self.requests:
            self.requests[client_ip] = [
                t for t in self.requests[client_ip]
                if current_time - t < self.window_seconds
            ]
        else:
            self.requests[client_ip] = []
        
        # Check limit
        if len(self.requests[client_ip]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window_seconds} seconds."
            )
        
        # Add current request
        self.requests[client_ip].append(current_time)
        return True


def get_rate_limiter(max_requests: int = 60, window_seconds: int = 60) -> RateLimiter:
    """
    Get a rate limiter instance.
    
    Args:
        max_requests: Maximum requests allowed in the window
        window_seconds: Time window in seconds
    
    Returns:
        RateLimiter instance
    """
    return RateLimiter(max_requests=max_requests, window_seconds=window_seconds)


# =============================================================================
# Helper Functions
# =============================================================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
    
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SUPABASE_JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: Data to encode in the token
    
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SUPABASE_JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If token is invalid
    """
    try:
        payload = jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Authentication
    "get_current_user",
    "get_current_active_user",
    "get_current_user_optional",
    "get_current_admin_user",
    "get_admin_user",
    "get_current_super_admin_user",
    
    # Database
    "get_db",
    
    # Permissions
    "require_permission",
    "require_roles",
    
    # Pagination
    "get_pagination_params",
    "get_search_params",
    "get_filter_params",
    
    # Rate Limiting
    "get_rate_limiter",
    
    # Helpers
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "security",
]
