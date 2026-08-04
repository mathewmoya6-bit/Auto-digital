# app/core/__init__.py

"""
Auto-D Kenya - Core Module
==========================

Core functionality for the application.
"""

# Only import what's needed directly
from .config import settings
from .database import get_supabase
from .middleware import setup_middleware

# Don't import dependencies here to avoid circular imports
# Import dependencies directly from app.core.dependencies when needed

__all__ = [
    "settings",
    "get_supabase",
    "setup_middleware",
]
