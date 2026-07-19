# backend/app/core/security.py
"""
Security - Authentication and authorization utilities
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


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """
    Get the current authenticated user from the JWT token.
    """
    token = credentials.credentials
    
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if token is expired
    exp = payload.get("exp")
    if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database (optional - you can add this if you have a users table)
    # For now, return the payload
    return {
        "id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role", "user"),
        **payload
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

def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[Dict[str, Any]]:
    """
    Get the current user if authenticated, otherwise return None.
    """
    if not credentials:
        return None
    
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None
