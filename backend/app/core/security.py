# backend/app/core/security.py
"""
Security - Authentication and authorization utilities

Auth model:
    The frontend authenticates users via Supabase Auth (email/password,
    OAuth, etc). Supabase issues the JWT that gets sent as
    `Authorization: Bearer <token>` on every API request.

    Token verification is delegated to Supabase itself via
    `supabase.auth.get_user(token)` rather than decoding the JWT locally
    with a shared secret. This is deliberate: Supabase projects can be
    configured with either a legacy shared HS256 "JWT Secret" or newer
    asymmetric "JWT Signing Keys" (ES256) — local decoding requires
    knowing which one is in play and copying the exact right value, and
    silently fails (401 on every request) if that assumption is wrong.
    Calling Supabase's own verification endpoint sidesteps that entirely
    and stays correct even if the project's signing method changes later.

    This does mean each authenticated request costs one extra network
    round-trip to Supabase. If that becomes a bottleneck, local HS256
    decoding can be reintroduced via SUPABASE_JWT_SECRET (see git history
    for the previous implementation) — but only once it's confirmed the
    project actually uses the legacy shared-secret signing method.

    create_access_token()/JWT_SECRET below are unrelated — kept only for
    any internal/service-to-service tokens this backend may mint itself.
    They are NOT used to validate frontend requests.
"""

import os
import logging
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional, Dict, Any, Union

from fastapi import HTTPException, Security, Depends, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import supabase, supabase_client

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer(
    scheme_name="Bearer",
    description="Enter your Supabase JWT token (obtained from login/register)"
)


# ─── Models ──────────────────────────────────────────────────────────

class TokenData(BaseModel):
    """Token payload model"""
    sub: Optional[str] = None
    exp: Optional[int] = None
    role: Optional[str] = None
    email: Optional[str] = None


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiry in seconds")


class UserAuth(BaseModel):
    """User authentication model"""
    id: str
    email: Optional[str] = None
    role: str = "user"
    is_authenticated: bool = True


# ─── Password Utilities ─────────────────────────────────────────────

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning(f"Password verification failed: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password."""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing failed: {e}")
        raise


def validate_password_strength(password: str) -> bool:
    """Validate password strength."""
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    if not any(c in "!@#$%^&*()-_=+[]{}|;:'\",.<>?/" for c in password):
        return False
    return True


# ─── JWT Utilities (Internal/Service Tokens) ──────────────────────

def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    NOTE: For internal/service tokens only. Unrelated to Supabase-issued
    user session tokens and not used by get_current_user() below.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire.timestamp()})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET, 
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire.timestamp(), "type": "refresh"})
    
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )


def decode_internal_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode a token issued by create_access_token() (internal use only)."""
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning(f"Internal JWT decode error: {e}")
        return None


def verify_internal_token(token: str, required_role: Optional[str] = None) -> bool:
    """Verify an internal token, optionally checking role."""
    payload = decode_internal_token(token)
    if not payload:
        return False
    
    # Check expiration
    exp = payload.get("exp")
    if exp:
        if isinstance(exp, (int, float)):
            if datetime.now(timezone.utc).timestamp() > exp:
                return False
    
    # Check role if required
    if required_role and payload.get("role") != required_role:
        return False
    
    return True


# ─── API Key Utilities ─────────────────────────────────────────────

def generate_api_key() -> str:
    """Generate a new API key."""
    return secrets.token_urlsafe(32)


def validate_api_key(api_key: str, expected_key: str) -> bool:
    """Validate an API key using constant-time comparison."""
    if not expected_key:
        return False
    return secrets.compare_digest(api_key, expected_key)


# ─── Main Auth Dependencies ────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """
    Get the current authenticated user by asking Supabase to verify the
    bearer token. This works regardless of whether the Supabase project
    signs tokens with a legacy shared secret or newer asymmetric keys.
    """
    token = credentials.credentials

    if not token or len(token) < 10:
        logger.warning("Token is empty or too short")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        response = supabase.auth.get_user(token)
        user = response.user if response else None
    except Exception as e:
        # Any failure here (expired token, malformed token, revoked
        # session, network error talking to Supabase) is treated as an
        # auth failure. Logged at warning level with the exception type
        # so real causes are distinguishable from routine expiries.
        error_msg = str(e).lower()
        
        if "expired" in error_msg:
            logger.info(f"Token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.warning(f"Supabase token verification failed: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract role from app_metadata
    app_metadata = getattr(user, "app_metadata", None) or {}
    if isinstance(app_metadata, dict):
        role = app_metadata.get("role", "user")
    else:
        role = getattr(app_metadata, "role", "user") or "user"
    
    # Also check user_metadata for role
    user_metadata = getattr(user, "user_metadata", None) or {}
    if isinstance(user_metadata, dict):
        if user_metadata.get("role"):
            role = user_metadata.get("role")

    # Check if admin email
    admin_emails = getattr(settings, "ADMIN_EMAILS", [])
    if isinstance(admin_emails, str):
        admin_emails = [admin_emails]
    if getattr(user, "email", None) in admin_emails:
        role = "admin"

    user_data = {
        "id": user.id,
        "email": getattr(user, "email", None),
        "role": role,
        "user_metadata": user_metadata,
        "app_metadata": app_metadata,
        "created_at": getattr(user, "created_at", None),
        "confirmed_at": getattr(user, "confirmed_at", None),
        "phone": getattr(user, "phone", None),
    }

    # Log successful authentication at debug level
    logger.debug(f"User authenticated: {user_data.get('email')} (ID: {user_data.get('id')[:8]}...)")

    return user_data


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current active user (alias for get_current_user).
    """
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(HTTPBearer(auto_error=False))
) -> Optional[Dict[str, Any]]:
    """
    Get the current user if authenticated, otherwise return None.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# ─── Admin Dependencies ────────────────────────────────────────────

async def verify_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Verify that the current user has admin privileges.
    """
    if current_user.get("role") != "admin":
        logger.warning(f"Non-admin user attempted admin access: {current_user.get('email')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user


async def verify_admin_api_key(
    api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """
    Verify an API key for admin endpoints.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check against configured admin API key
    expected_key = os.environ.get("ADMIN_API_KEY", "")

    if not expected_key:
        logger.warning("⚠️ ADMIN_API_KEY not configured in environment variables")
        # If no API key is configured, allow requests from localhost only
        return api_key

    if not validate_api_key(api_key, expected_key):
        logger.warning(f"Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    return api_key


# ─── Service Token Dependencies ───────────────────────────────────

async def verify_service_token(
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> Dict[str, Any]:
    """
    Verify a service-to-service token.
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
        if service_token and validate_api_key(token, service_token):
            return {
                "id": "service",
                "role": "service",
                "is_service": True
            }
        
        # Fallback: validate as regular user
        return await get_current_user(security)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Service auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service authentication failed"
        )


# ─── Rate Limiting Helper ──────────────────────────────────────────

def get_client_ip(request) -> str:
    """Get client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ─── Security Headers ──────────────────────────────────────────────

class SecurityHeaders:
    """Security headers for responses."""
    
    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Get security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }


# ─── Export ─────────────────────────────────────────────────────────

__all__ = [
    # Password utilities
    "verify_password",
    "get_password_hash",
    "validate_password_strength",
    
    # JWT utilities
    "create_access_token",
    "create_refresh_token",
    "decode_internal_token",
    "verify_internal_token",
    
    # API key utilities
    "generate_api_key",
    "validate_api_key",
    
    # Auth dependencies
    "get_current_user",
    "get_current_active_user",
    "get_current_user_optional",
    
    # Admin dependencies
    "verify_admin",
    "verify_admin_api_key",
    
    # Service dependencies
    "verify_service_token",
    
    # Utilities
    "get_client_ip",
    "SecurityHeaders",
    
    # Models
    "TokenData",
    "TokenResponse",
    "UserAuth",
]

# ─── Backward Compatibility ─────────────────────────────────────────
# Keep these for imports from other modules

security = security
HTTPBearer = HTTPBearer
