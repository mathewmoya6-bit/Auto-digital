"""
Auto-D Kenya - Core Security Utilities
=====================================

Centralized authentication and security helpers.

Provides:
- Password hashing & verification
- JWT access & refresh tokens
- JWT decoding
- OTP generation
- Phone hashing
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import bcrypt
from jose import JWTError, ExpiredSignatureError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ---------------------------------------------------------------------
# Password Hashing
# ---------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def get_password_hash(password: str) -> str:
    """Alias for compatibility."""
    return hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------
# JWT Tokens
# ---------------------------------------------------------------------

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT access token.
    """

    payload = data.copy()

    expire = (
        datetime.utcnow() + expires_delta
        if expires_delta
        else datetime.utcnow()
        + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload.update(
        {
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
        }
    )

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create JWT refresh token.
    """

    payload = data.copy()

    payload.update(
        {
            "exp": datetime.utcnow()
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            "iat": datetime.utcnow(),
            "type": "refresh",
        }
    )

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT token.

    Raises:
        ValueError if token is invalid or expired.
    """

    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

    except ExpiredSignatureError:
        raise ValueError("Token has expired")

    except JWTError as e:
        raise ValueError(f"Invalid token: {str(e)}")


# ---------------------------------------------------------------------
# OTP
# ---------------------------------------------------------------------

def generate_otp(length: int = 6) -> str:
    """Generate numeric OTP."""

    minimum = 10 ** (length - 1)
    maximum = (10**length) - 1

    return str(random.randint(minimum, maximum))


# ---------------------------------------------------------------------
# Phone Utilities
# ---------------------------------------------------------------------

def hash_phone(phone: str) -> str:
    """Hash phone number."""
    return bcrypt.hashpw(
        phone.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_phone(phone: str, hashed_phone: str) -> bool:
    """Verify hashed phone."""
    return bcrypt.checkpw(
        phone.encode("utf-8"),
        hashed_phone.encode("utf-8"),
    )


# ---------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------

__all__ = [
    "hash_password",
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "generate_otp",
    "hash_phone",
    "verify_phone",
]
