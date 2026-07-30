# app/core/__init__.py
# ================================================================
# Auto-D Kenya - Core Package
# ================================================================

"""Core package for Auto-D Kenya."""

from .config import settings
from .database import get_supabase
from .security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)

from .dependencies import (
    get_current_user,
    get_optional_user,
)

from .exceptions import (
    AppException,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    ValidationException,
)

__all__ = [
    "settings",
    "get_supabase",
    "create_access_token",
    "decode_token",
    "hash_password",
    "verify_password",
    "get_current_user",
    "get_optional_user",
    "AppException",
    "NotFoundException",
    "UnauthorizedException",
    "ForbiddenException",
    "ValidationException",
]
