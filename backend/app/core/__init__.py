# app/core/__init__.py
# Auto-D Kenya - Core Package
# ================================================================

"""Core package for Auto-D Kenya."""

from .config import settings
from .database import get_supabase
from .security import create_access_token, hash_password, verify_password, decode_token
from .dependencies import get_current_user, get_current_user_optional
from .exceptions import AppException, NotFoundException, UnauthorizedException, ForbiddenException, ValidationException

__all__ = [
    "settings",
    "get_supabase",
    "create_access_token",
    "get_current_user",
    "get_current_user_optional",
    "hash_password",
    "verify_password",
    "decode_token",
    "AppException",
    "NotFoundException",
    "UnauthorizedException",
    "ForbiddenException",
    "ValidationException"
]
