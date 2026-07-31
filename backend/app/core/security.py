# app/core/security.py
# Auto-D Kenya - Security Utilities
# ================================================================
# TYPE: CORE - Security and authentication utilities

import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import bcrypt
from jwt import (
    PyJWKClient,
    PyJWKClientError,
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidTokenError,
    decode as jwt_decode
)
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
# ✅ FIX 4: Added timeout to JWKS client
_jwks_client = PyJWKClient(
    f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json",
    timeout=5
)


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
    return jwt_encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token issued by Supabase Auth.

    The frontend sends session.access_token from supabase-js (see
    dashboard.html). Supabase signs these with ES256 using an
    asymmetric keypair — verification requires fetching the matching
    public key from Supabase's JWKS endpoint (via the token's "kid"
    header), not a static HS256 shared secret.

    ✅ FIX 1: Verify token issuer
    ✅ FIX 2: Handle JWT errors separately
    ✅ FIX 3: Validate required claims
    """
    try:
        # Get signing key from JWKS
        try:
            signing_key = _jwks_client.get_signing_key_from_jwt(token)
        except PyJWKClientError as e:
            raise ValueError(f"Unable to verify signing key: {str(e)}")

        # ✅ FIX 1: Added issuer validation
        # ✅ FIX 2: Decode with specific error handling
        try:
            payload = jwt_decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
                issuer=f"{settings.SUPABASE_URL}/auth/v1"
            )
        except ExpiredSignatureError:
            raise ValueError("Token has expired")
        except InvalidAudienceError:
            raise ValueError("Invalid token audience")
        except InvalidIssuerError:
            raise ValueError("Invalid token issuer")
        except InvalidTokenError:
            raise ValueError("Invalid token")

        # ✅ FIX 3: Validate required claims
        if "sub" not in payload:
            raise ValueError("Token missing user id")

        if "email" not in payload:
            raise ValueError("Token missing email")

        return payload

    except ValueError:
        # Re-raise ValueError with the specific message
        raise
    except Exception as e:
        raise ValueError(f"Token validation failed: {str(e)}")


def generate_otp() -> str:
    """Generate a 6-digit OTP."""
    return f"{random.randint(100000, 999999)}"


def hash_phone(phone: str) -> str:
    """Hash a phone number for secure storage."""
    return bcrypt.hashpw(phone.encode(), bcrypt.gensalt()).decode()
