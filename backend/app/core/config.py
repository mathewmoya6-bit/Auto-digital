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
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.core.database import supabase

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    NOTE: For internal/service tokens only. Unrelated to Supabase-issued
    user session tokens and not used by get_current_user() below.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    return encoded_jwt


def decode_internal_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode a token issued by create_access_token() (internal use only)."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Internal JWT decode error: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """
    Get the current authenticated user by asking Supabase to verify the
    bearer token. This works regardless of whether the Supabase project
    signs tokens with a legacy shared secret or newer asymmetric keys.
    """
    token = credentials.credentials

    try:
        response = supabase.auth.get_user(token)
        user = response.user if response else None
    except Exception as e:
        # Any failure here (expired token, malformed token, revoked
        # session, network error talking to Supabase) is treated as an
        # auth failure. Logged at warning level with the exception type
        # so real causes are distinguishable from routine expiries.
        logger.warning(f"Supabase token verification failed: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    app_metadata = getattr(user, "app_metadata", None) or {}
    if isinstance(app_metadata, dict):
        role = app_metadata.get("role", "user")
    else:
        role = getattr(app_metadata, "role", "user") or "user"

    return {
        "id": user.id,
        "email": getattr(user, "email", None),
        "role": role,
    }


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current active user (alias for get_current_user).
    """
    return current_user


async def verify_api_key(
    api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """
    Verify an API key for admin endpoints.
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key is required"
        )

    # Check against configured admin API key
    expected_key = os.environ.get("ADMIN_API_KEY", "")

    if not expected_key:
        logger.warning("⚠️ ADMIN_API_KEY not configured in environment variables")
        # If no API key is configured, allow requests from localhost
        return api_key

    if api_key != expected_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )

    return api_key


async def verify_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Verify that the current user has admin privileges.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user


def generate_api_key() -> str:
    """Generate a new API key."""
    import secrets
    return secrets.token_urlsafe(32)


# ─── For backward compatibility ──────────────────────────────────────
# These aliases are used by other parts of the app

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
