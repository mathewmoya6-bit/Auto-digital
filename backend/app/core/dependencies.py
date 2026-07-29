# backend/app/core/dependencies.py

from fastapi import HTTPException, Depends, Header, Request, status
from typing import Optional, Dict, Any
import logging
from functools import lru_cache
from datetime import datetime, timezone

from app.core.database import supabase, supabase_client
from app.core.config import settings

logger = logging.getLogger(__name__)


# ─── User Model ─────────────────────────────────────────────────────
class User:
    """User model with typed properties."""
    
    def __init__(self, user_data: Dict[str, Any]):
        self.id = user_data.get("id")
        self.email = user_data.get("email")
        self.phone = user_data.get("phone")
        self.user_metadata = user_data.get("user_metadata", {})
        self.app_metadata = user_data.get("app_metadata", {})
        self.created_at = user_data.get("created_at")
        self.updated_at = user_data.get("updated_at")
        self.last_sign_in_at = user_data.get("last_sign_in_at")
        self.confirmed_at = user_data.get("confirmed_at")
        self.is_authenticated = True
        
        # Extract common metadata
        self.full_name = self.user_metadata.get("full_name") or self.user_metadata.get("name")
        self.avatar_url = self.user_metadata.get("avatar_url")
        self.role = self.user_metadata.get("role", "user")
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "phone": self.phone,
            "full_name": self.full_name,
            "avatar_url": self.avatar_url,
            "role": self.role,
            "user_metadata": self.user_metadata,
            "app_metadata": self.app_metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_sign_in_at": self.last_sign_in_at,
            "confirmed_at": self.confirmed_at,
        }
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == "admin" or self.email in getattr(settings, "ADMIN_EMAILS", [])
    
    @property
    def is_confirmed(self) -> bool:
        """Check if user's email is confirmed."""
        return self.confirmed_at is not None


# ─── Cache for user sessions ──────────────────────────────────────
_user_cache = {}
_cache_lock = None  # Will be initialized lazily
CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_cache_lock():
    """Get or create cache lock."""
    import threading
    global _cache_lock
    if _cache_lock is None:
        _cache_lock = threading.Lock()
    return _cache_lock


def _get_cached_user(token: str) -> Optional[Dict]:
    """Get cached user by token."""
    import threading
    with _get_cache_lock():
        if token in _user_cache:
            entry = _user_cache[token]
            if datetime.now(timezone.utc).timestamp() - entry["timestamp"] < CACHE_TTL_SECONDS:
                return entry["user"]
            else:
                del _user_cache[token]
    return None


def _set_cached_user(token: str, user_data: Dict):
    """Cache user data by token."""
    import threading
    with _get_cache_lock():
        _user_cache[token] = {
            "user": user_data,
            "timestamp": datetime.now(timezone.utc).timestamp()
        }
        # Limit cache size
        if len(_user_cache) > 1000:
            # Remove oldest entries
            sorted_entries = sorted(
                _user_cache.items(),
                key=lambda x: x[1]["timestamp"]
            )
            for key, _ in sorted_entries[:100]:
                del _user_cache[key]


# ─── Main Dependency ──────────────────────────────────────────────

async def get_current_user(
    authorization: Optional[str] = Header(None, description="Bearer token"),
    request: Optional[Request] = None
) -> Dict:
    """
    Get current user from Supabase session.
    
    Returns a dictionary with user information.
    Raises HTTPException 401 if not authenticated.
    """
    if not authorization:
        logger.warning("No authorization header provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Parse Authorization header
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning(f"Invalid auth header format: {authorization[:20]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format. Expected 'Bearer <token>'",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = parts[1]
        
        # Validate token is not empty
        if not token or len(token) < 10:
            logger.warning("Token is empty or too short")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check cache first (with TTL)
        cached_user = _get_cached_user(token)
        if cached_user:
            logger.debug(f"User {cached_user.get('email')} found in cache")
            return cached_user

        # Verify with Supabase
        try:
            response = supabase.auth.get_user(token)
            
            if not response or not response.user:
                logger.warning("Supabase get_user returned no user")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            user_data = {
                "id": response.user.id,
                "email": response.user.email,
                "phone": response.user.phone,
                "user_metadata": response.user.user_metadata or {},
                "app_metadata": response.user.app_metadata or {},
                "created_at": response.user.created_at,
                "updated_at": response.user.updated_at,
                "last_sign_in_at": response.user.last_sign_in_at,
                "confirmed_at": response.user.confirmed_at,
                "role": response.user.user_metadata.get("role", "user") if response.user.user_metadata else "user",
            }
            
            # Cache the user data
            _set_cached_user(token, user_data)
            
            logger.info(f"✅ User authenticated: {user_data.get('email')} (ID: {user_data.get('id')[:8]}...)")
            return user_data

        except Exception as supabase_error:
            logger.error(f"Supabase auth error: {supabase_error}")
            
            # Check if token is expired
            error_str = str(supabase_error).lower()
            if "expired" in error_str or "invalid" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired. Please log in again.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─── Optional User (for endpoints that allow unauthenticated) ──

async def get_optional_user(
    authorization: Optional[str] = Header(None, description="Bearer token")
) -> Optional[Dict]:
    """
    Get current user if authenticated, otherwise return None.
    Does not raise 401 if no token is provided.
    """
    if not authorization:
        return None
    
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None


# ─── Admin Only Dependency ───────────────────────────────────────

async def get_current_admin_user(
    authorization: Optional[str] = Header(None, description="Bearer token")
) -> Dict:
    """
    Get current user and verify they are an admin.
    Raises HTTPException 403 if not an admin.
    """
    user = await get_current_user(authorization)
    
    # Check if user is admin
    user_role = user.get("user_metadata", {}).get("role", "user")
    user_email = user.get("email", "")
    
    # Admin emails from settings
    admin_emails = getattr(settings, "ADMIN_EMAILS", ["admin@auto-d.ke"])
    if isinstance(admin_emails, str):
        admin_emails = [admin_emails]
    
    is_admin = (
        user_role == "admin" or 
        user_email in admin_emails or
        user.get("app_metadata", {}).get("role") == "admin"
    )
    
    if not is_admin:
        logger.warning(f"Unauthorized admin access attempt: {user_email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return user


# ─── Service User (for internal service-to-service auth) ──────

async def get_service_user(
    authorization: Optional[str] = Header(None, description="Service token")
) -> Dict:
    """
    Validate service-to-service authentication.
    Used for internal API calls between services.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service authentication required"
        )
    
    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid service auth format"
            )
        
        token = parts[1]
        
        # Check against configured service token
        service_token = getattr(settings, "SERVICE_TOKEN", None)
        if service_token and token == service_token:
            return {
                "id": "service",
                "role": "service",
                "is_service": True
            }
        
        # Fallback: validate as regular user
        return await get_current_user(authorization)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Service auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service authentication failed"
        )


# ─── Health Check Dependency ─────────────────────────────────────

async def require_healthy_db():
    """Check if database is healthy before proceeding."""
    if not supabase_client.health_check():
        logger.error("Database health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is currently unavailable. Please try again later."
        )
    return True


# ─── Rate Limiting Dependencies ──────────────────────────────────

async def rate_limit_check(request: Request):
    """
    Check rate limits for the current request.
    Requires Redis to be configured.
    """
    if not settings.REDIS_ENABLED or not settings.RATE_LIMIT_ENABLED:
        return True
    
    try:
        import redis.asyncio as redis
        from app.core.config import settings
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Check rate limits
        redis_client = redis.from_url(settings.REDIS_URL)
        
        # Minute limit
        minute_key = f"rate_limit:minute:{client_ip}:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
        minute_count = await redis_client.incr(minute_key)
        await redis_client.expire(minute_key, 60)
        
        if minute_count > settings.RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded (per minute)"
            )
        
        # Hour limit
        hour_key = f"rate_limit:hour:{client_ip}:{datetime.now(timezone.utc).strftime('%Y%m%d%H')}"
        hour_count = await redis_client.incr(hour_key)
        await redis_client.expire(hour_key, 3600)
        
        if hour_count > settings.RATE_LIMIT_PER_HOUR:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded (per hour)"
            )
        
        # Day limit
        day_key = f"rate_limit:day:{client_ip}:{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        day_count = await redis_client.incr(day_key)
        await redis_client.expire(day_key, 86400)
        
        if day_count > settings.RATE_LIMIT_PER_DAY:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded (per day)"
            )
        
        return True
        
    except Exception as e:
        logger.warning(f"Rate limit check failed: {e}")
        # Fail open - don't block on rate limiter errors
        return True


# ─── User Token Management ──────────────────────────────────────

def invalidate_user_cache(token: str):
    """Invalidate cached user data for a token."""
    import threading
    with _get_cache_lock():
        if token in _user_cache:
            del _user_cache[token]
            logger.debug(f"User cache invalidated for token: {token[:8]}...")


def clear_user_cache():
    """Clear all cached user data."""
    import threading
    with _get_cache_lock():
        _user_cache.clear()
        logger.info("User cache cleared")


# ─── Export ──────────────────────────────────────────────────────

__all__ = [
    "get_current_user",
    "get_optional_user",
    "get_current_admin_user",
    "get_service_user",
    "require_healthy_db",
    "rate_limit_check",
    "invalidate_user_cache",
    "clear_user_cache",
    "User",
]
