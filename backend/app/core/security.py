# app/core/security.py
# Auto-D Kenya - Security Utilities
# ================================================================
# TYPE: CORE - Security and authentication utilities

import jwt
from jwt import PyJWKClient
import bcrypt
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─── SUPABASE JWKS CLIENT ───────────────────────────────────────
# Supabase signs session tokens with ES256 (asymmetric ECDSA), using a
# rotating keypair published at this JWKS endpoint — not a static
# HS256 shared secret. PyJWKClient fetches and caches Supabase's
# public signing keys and picks the right one via the token's "kid"
# header, including handling key rotation automatically.
# Created once at module load rather than per-request.
_jwks_client = PyJWKClient(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")


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
    sends Supabase-issued (ES256) tokens on every request instead.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token issued by Supabase Auth.

    The frontend sends session.access_token from supabase-js (see
    dashboard.html). Supabase signs these with ES256 using an
    asymmetric keypair — verification requires fetching the matching
    public key from Supabase's JWKS endpoint (via the token's "kid"
    header), not a static HS256 shared secret.
    """
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
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
