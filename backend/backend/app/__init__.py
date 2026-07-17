# backend/app/__init__.py
"""
Auto-D Kenya - FastAPI Application Package
"""

__version__ = "4.0.0"

from app.core.config import settings
from app.core.database import supabase

__all__ = [
    "settings",
    "supabase",
]
