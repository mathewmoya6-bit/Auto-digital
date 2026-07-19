# backend/app/core/security.py
"""
Security - Authentication and authorization utilities

Auth model:
    The frontend authenticates users via Supabase Auth (email/password,
    OAuth, etc). Supabase issues the JWT that gets sent as
    `Authorization: Bearer <token>` on every API request. This backend
    does NOT issue its own login tokens for end users — it only verifies
    the token Supabase already signed.

    That verification is done against SUPABASE_JWT_SECRET (Project
    Settings -> API -> JWT Secret in the Supabase dashboard). This is a
    different value from SUPABASE_ANON_KEY and from any custom JWT_SECRET
    used elsewhere in this app — do not confuse the three.

    create_access_token()/JWT_SECRET are kept below only for any
    internal/service-to-service tokens this backend may still need to
    mint itself. They are NOT used to validate frontend requests anymore.
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

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()

# Supabase signs its access tokens with HS256 and sets aud="authenticated"
SUPABASE_JWT_ALGORITHM = "HS256"
SUPABASE_JWT_AUDIENCE = "authenticated"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    NOTE: This is for internal/service tokens only. It is unrelated to
    Supabase-issued user session tokens and is not used by
    get_current_user() below.
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


def decode_supabase_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a Supabase-issued user session token.

    Requires SUPABASE_JWT_SECRET to be set in the environment/settings
    to the value from Supabase Dashboard -> Project Settings -> API ->
    JWT Secret. This is NOT the anon key.
    """
    if not settings.SUPABASE_JWT_SECRET:
        logger.error("SUPABASE_JWT_SECRET is not configured — cannot verify Supabase tokens")
        return None

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[SUPABASE_JWT_ALGORITHM],
            audience=SUPABASE_JWT_AUDIENCE,
        )
        return payload
    except JWTError as e:
        logger.warning(f"Supabase JWT decode error: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """
    Get the current authenticated user from a Supabase-issued JWT token.
    """
    token = credentials.credentials

    payload = decode_supabase_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # jose already validates `exp` during jwt.decode() and raises
    # ExpiredSignatureError (a JWTError subclass) if expired, so no
    # separate expiry check is needed here.

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Supabase stores custom claims (like role) under user_metadata /
    # app_metadata rather than top-level, but top-level "role" defaults
    # to "authenticated" for normal users. Fall back to "user" if absent.
    app_metadata = payload.get("app_metadata") or {}

    return {
        "id": user_id,
        "email": payload.get("email"),
        "role": app_metadata.get("role", payload.get("role", "user")),
        **payload,
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
