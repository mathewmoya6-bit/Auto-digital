# app/core/__init__.py
"""
Auto-D Kenya Core Package
"""

from .config import settings
from .database import get_supabase

from .security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash as hash_password,
    verify_password,
    mask_sensitive,
    generate_random_string,
    generate_otp,
    generate_api_key,
)

from .utils import (
    mask_sensitive as utils_mask_sensitive,
    generate_random_token,
    generate_otp as utils_generate_otp,
    utc_now,
    safe_get,
    truncate_string,
)

from .dependencies import (
    get_current_user,
    get_current_user_optional,
    get_supabase_client,
)

from .exceptions import (
    AppException,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    ValidationException,
)

# Re-export mask_sensitive from utils (preferred location)
# but keep security version for backward compatibility
mask_sensitive = utils_mask_sensitive

__all__ = [
    # Config & Database
    "settings",
    "get_supabase",
    
    # Security
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "hash_password",
    "verify_password",
    "mask_sensitive",
    "generate_random_string",
    "generate_otp",
    "generate_api_key",
    
    # Utilities
    "generate_random_token",
    "utc_now",
    "safe_get",
    "truncate_string",
    
    # Dependencies
    "get_current_user",
    "get_current_user_optional",
    "get_supabase_client",
    
    # Exceptions
    "AppException",
    "NotFoundException",
    "UnauthorizedException",
    "ForbiddenException",
    "ValidationException",
]
