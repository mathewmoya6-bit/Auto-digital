# app/core/security.py
# Auto-D Kenya - Security Utilities
# ================================================================
# TYPE: CORE - Security and authentication utilities

import random
from typing import Optional, Dict, Any

import bcrypt
from passlib.context import CryptContext

# ─── PASSWORD HASHING ────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ─── OTP GENERATION ──────────────────────────────────────────────

def generate_otp() -> str:
    """Generate a 6-digit OTP."""
    return f"{random.randint(100000, 999999)}"


# ─── PHONE HASHING ───────────────────────────────────────────────

def hash_phone(phone: str) -> str:
    """Hash a phone number for secure storage."""
    return bcrypt.hashpw(phone.encode(), bcrypt.gensalt()).decode()
