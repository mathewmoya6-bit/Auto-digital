# app/core/security.py
"""
Auto-D Kenya - Security Utilities
=================================

Centralized security helpers for:

- Password hashing
- JWT creation
- JWT decoding
- OTP generation
- Phone hashing
- Sensitive data masking

Supports:
- Internal Auto-D JWTs (HS256)
- Supabase JWTs (ES256 / RS256)
"""

import random
import secrets
import string
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
# Sensitive Data Masking
# =============================================================================

def mask_sensitive(value: str, visible: int = 4) -> str:
    """
    Mask sensitive values for logging.

    Args:
        value: The string to mask
        visible: Number of characters to show at start and end

    Returns:
        Masked string

    Examples:
        >>> mask_sensitive("254712345678")
        '2547...5678'
        >>> mask_sensitive("test@example.com")
        'test...ple.com'
        >>> mask_sensitive("short")
        'sh...rt'
        >>> mask_sensitive("")
        '***'
    """
    if not value:
        return "***"
    if len(value) <= visible * 2:
        return value[:2] + "***" + value[-2:]
    return f"{value[:visible]}...{value[-visible:]}"


def generate_random_string(length: int = 32) -> str:
    """
    Generate a cryptographically secure random string.

    Args:
        length: Length of the string to generate

    Returns:
        Random alphanumeric string
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_api_key() -> str:
    """
    Generate a secure API key with prefix.

    Returns:
        API key in format: ak_{32_random_chars}
    """
    prefix = "ak"
    random_part = generate_random_string(32)
    return f"{prefix}_{random_part}"


def generate_secure_token(length: int = 64) -> str:
    """
    Generate a cryptographically secure token (hex).

    Args:
        length: Length of the token in bytes (output will be 2x length)

    Returns:
        Hexadecimal token
    """
    return secrets.token_hex(length)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Password
    "hash_password",
    "get_password_hash",
    "verify_password",
    
    # JWT
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    
    # OTP
    "generate_otp",
    
    # Phone
    "hash_phone",
    "verify_phone",
    
    # Utilities
    "mask_sensitive",
    "generate_random_string",
    "generate_api_key",
    "generate_secure_token",
]
