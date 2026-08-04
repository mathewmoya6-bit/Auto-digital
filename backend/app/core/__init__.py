# app/core/__init__.py

from .config import settings
from .database import get_supabase
from .middleware import setup_middleware
from .dependencies import (
    # Authentication
    get_current_user,
    get_current_active_user,
    get_current_user_optional,
    get_current_admin_user,
    get_admin_user,
    get_current_super_admin_user,
    
    # Database
    get_db,
    
    # Permissions
    require_permission,
    require_roles,
    
    # Pagination
    get_pagination_params,
    get_search_params,
    get_filter_params,
    
    # Rate Limiting
    get_rate_limiter,
    
    # Helpers
    create_access_token,
    create_refresh_token,
    verify_token,
    security,
)

__all__ = [
    "settings",
    "get_supabase",
    "setup_middleware",
    "get_current_user",
    "get_current_active_user",
    "get_current_user_optional",
    "get_current_admin_user",
    "get_admin_user",
    "get_current_super_admin_user",
    "get_db",
    "require_permission",
    "require_roles",
    "get_pagination_params",
    "get_search_params",
    "get_filter_params",
    "get_rate_limiter",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "security",
]
