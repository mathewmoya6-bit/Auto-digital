# backend/app/core/__init__.py
"""
Core modules for Auto-D Kenya
Provides configuration, database, security, and dependency injection
"""

from app.core.config import settings
from app.core.database import supabase
from app.core.security import get_current_user, create_access_token

__all__ = [
    "settings",
    "supabase",
    "get_current_user",
    "create_access_token",
]
