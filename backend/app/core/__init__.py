# app/core/__init__.py

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
    get_current_user_optional,
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
    "get_current_user_optional",
    "AppException",
    "NotFoundException",
    "UnauthorizedException",
    "ForbiddenException",
    "ValidationException",
]
