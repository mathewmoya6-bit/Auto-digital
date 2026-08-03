# app/core/utils.py

import secrets
import string
from typing import Optional, Any
from datetime import datetime, timezone


def mask_sensitive(value: str, visible: int = 4) -> str:
    """
    Mask sensitive values for logging.
    
    Args:
        value: The string to mask
        visible: Number of characters to show at start and end
    
    Returns:
        Masked string
    """
    if not value:
        return "***"
    if len(value) <= visible * 2:
        return value[:2] + "***" + value[-2:]
    return f"{value[:visible]}...{value[-visible:]}"


def generate_random_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP."""
    return ''.join(secrets.choice(string.digits) for _ in range(length))


def utc_now() -> str:
    """Get current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def safe_get(data: dict, key: str, default: Any = None) -> Any:
    """Safely get a value from a dict, returning default if key doesn't exist."""
    return data.get(key, default) if isinstance(data, dict) else default


def truncate_string(value: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate a string to a maximum length."""
    if not value:
        return ""
    if len(value) <= max_length:
        return value
    return value[:max_length - len(suffix)] + suffix
