"""
Auto-D Kenya - Security Utilities
=================================

Centralized security helpers for:

- Password hashing
- JWT creation
- JWT decoding
- OTP generation
- Phone hashing

Supports:
- Internal Auto-D JWTs (HS256)
- Supabase JWTs (ES256 / RS256)
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import bcrypt
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext

from app.core.config import settings

# =============================================================================
# Password Hashing
# =============================================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


def get_password_hash(password: str) -> str:
    """Compatibility alias."""
    return hash_password(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Verify password."""
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


# =============================================================================
# JWT Creation
# =============================================================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:

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


def create_refresh_token(
    data: Dict[str, Any],
) -> str:

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


# =============================================================================
# JWT Decode
# =============================================================================

def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode JWT.

    Supports both:

    - Auto-D HS256 tokens
    - Supabase ES256 / RS256 tokens

    Returns payload.

    Raises:
        ValueError
    """

    try:

        header = jwt.get_unverified_header(token)

        algorithm = header.get("alg", "")

        # ---------------------------------------------------------
        # Internal Auto-D token
        # ---------------------------------------------------------

        if algorithm.upper() == settings.ALGORITHM.upper():

            return jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )

        # ---------------------------------------------------------
        # Supabase token
        #
        # Claims are extracted without verification.
        # Proper verification should be done using
        # Supabase JWKS or auth.get_user().
        # ---------------------------------------------------------

        if algorithm in ("ES256", "RS256"):

            claims = jwt.get_unverified_claims(token)

            if "sub" not in claims:
                raise ValueError("Missing user id")

            return claims

        raise ValueError(f"Unsupported JWT algorithm: {algorithm}")

    except ExpiredSignatureError:
        raise ValueError("Token has expired")

    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


# =============================================================================
# OTP
# =============================================================================

def generate_otp(length: int = 6) -> str:
    """Generate numeric OTP."""

    minimum = 10 ** (length - 1)
    maximum = (10 ** length) - 1

    return str(
        random.randint(minimum, maximum)
    )


# =============================================================================
# Phone Hashing
# =============================================================================

def hash_phone(phone: str) -> str:
    """Hash phone."""

    return bcrypt.hashpw(
        phone.encode(),
        bcrypt.gensalt(),
    ).decode()


def verify_phone(
    phone: str,
    hashed_phone: str,
) -> bool:
    """Verify hashed phone."""

    return bcrypt.checkpw(
        phone.encode(),
        hashed_phone.encode(),
    )


# =============================================================================
# Exports
# =============================================================================

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
