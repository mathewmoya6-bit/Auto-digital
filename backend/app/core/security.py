# app/core/security.py
# Auto-D Kenya - Security Utilities
# ================================================================
# TYPE: CORE - Security and authentication utilities

import jwt
import bcrypt
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token issued by THIS backend (used by the
    /auth/login endpoint's own token flow, e.g. app.modules.auth.service).

    NOTE: This is a separate signing key/purpose from decode_token()
    below. The frontend dashboard does not currently use tokens from
    this function — it authenticates via Supabase Auth directly and
    sends Supabase-issued tokens on every request instead.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token issued by Supabase Auth.

    The frontend sends session.access_token from supabase-js
    (see dashboard.html), which is signed by Supabase using the
    project's JWT secret — NOT this backend's SECRET_KEY. Supabase
    tokens also set "aud": "authenticated" in the payload, which
    PyJWT validates by default, so it must be passed explicitly here
    or verification will fail even with the correct secret.
    """
    try:
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


def generate_otp() -> str:
    """Generate a 6-digit OTP."""
    return f"{random.randint(100000, 999999)}"


def hash_phone(phone: str) -> str:
    """Hash a phone number for secure storage."""
    return bcrypt.hashpw(phone.encode(), bcrypt.gensalt()).decode()
