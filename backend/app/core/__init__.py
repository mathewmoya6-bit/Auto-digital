# backend/app/core/__init__.py
"""
Core modules for Auto-D Kenya
Provides configuration, database, security, and dependency injection
"""

# ─── Configuration ──────────────────────────────────────────────────
from app.core.config import settings

# ─── Database ───────────────────────────────────────────────────────
from app.core.database import (
    supabase,
    db,
    supabase_client,
    table_exists,
    get_table_count,
    get_service_by_code,
    get_active_services,
)

# ─── Security ──────────────────────────────────────────────────────
from app.core.security import (
    # Password utilities
    verify_password,
    get_password_hash,
    validate_password_strength,
    
    # JWT utilities
    create_access_token,
    create_refresh_token,
    decode_internal_token,
    verify_internal_token,
    
    # API key utilities
    generate_api_key,
    validate_api_key,
    
    # Auth dependencies
    get_current_user,
    get_current_active_user,
    get_current_user_optional,
    verify_admin,
    verify_admin_api_key,
    verify_service_token,
    
    # Utilities
    get_client_ip,
    SecurityHeaders,
    
    # Models
    TokenData,
    TokenResponse,
    UserAuth,
)

# ─── Dependencies ──────────────────────────────────────────────────
from app.core.dependencies import (
    # User models
    User,
    
    # Auth dependencies
    get_current_user as get_current_user_dep,
    get_optional_user,
    get_current_admin_user,
    get_service_user,
    
    # Health & Rate limiting
    require_healthy_db,
    rate_limit_check,
    
    # Cache management
    invalidate_user_cache,
    clear_user_cache,
)

# ─── Version ───────────────────────────────────────────────────────
__version__ = "4.0.0"
__author__ = "Auto-D Kenya Team"
__email__ = "support@auto-d.ke"

# ─── Public API ────────────────────────────────────────────────────
__all__ = [
    # ─── Configuration ────────────────────────────────────────────
    "settings",
    
    # ─── Database ─────────────────────────────────────────────────
    "supabase",
    "db",
    "supabase_client",
    "table_exists",
    "get_table_count",
    "get_service_by_code",
    "get_active_services",
    
    # ─── Security - Password ─────────────────────────────────────
    "verify_password",
    "get_password_hash",
    "validate_password_strength",
    
    # ─── Security - JWT ──────────────────────────────────────────
    "create_access_token",
    "create_refresh_token",
    "decode_internal_token",
    "verify_internal_token",
    
    # ─── Security - API Keys ────────────────────────────────────
    "generate_api_key",
    "validate_api_key",
    
    # ─── Security - Auth Dependencies ───────────────────────────
    "get_current_user",
    "get_current_active_user",
    "get_current_user_optional",
    "verify_admin",
    "verify_admin_api_key",
    "verify_service_token",
    
    # ─── Security - Utilities ────────────────────────────────────
    "get_client_ip",
    "SecurityHeaders",
    
    # ─── Security - Models ──────────────────────────────────────
    "TokenData",
    "TokenResponse",
    "UserAuth",
    
    # ─── Dependencies ─────────────────────────────────────────────
    "User",
    "get_current_user_dep",
    "get_optional_user",
    "get_current_admin_user",
    "get_service_user",
    "require_healthy_db",
    "rate_limit_check",
    "invalidate_user_cache",
    "clear_user_cache",
    
    # ─── Version Info ─────────────────────────────────────────────
    "__version__",
    "__author__",
    "__email__",
]

# ─── Log initialization ────────────────────────────────────────────
import logging
logger = logging.getLogger(__name__)
logger.debug("✅ Core modules loaded successfully")
