# app/core/database.py
"""
Auto-D Kenya - Database Connection
==================================
Centralized Supabase client management.
"""

import logging
from typing import Optional

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

_supabase: Optional[Client] = None


def get_supabase() -> Client:
    """
    Return a singleton Supabase client.

    Raises:
        RuntimeError: If Supabase configuration is missing.
    """
    global _supabase

    if _supabase is not None:
        return _supabase

    if not settings.SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is not configured")

    if not settings.SUPABASE_KEY:
        raise RuntimeError("SUPABASE_KEY is not configured")

    try:
        _supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY,
        )

        logger.info("Supabase client initialized")
        return _supabase

    except Exception:
        logger.exception("Failed to initialize Supabase client")
        raise


async def init_db() -> None:
    """
    Verify that the database is reachable.
    """
    try:
        client = get_supabase()

        # Lightweight connectivity test
        client.table("services").select("id").limit(1).execute()

        logger.info("Database connection verified")

    except Exception:
        logger.exception("Database initialization failed")
        raise


async def close_db() -> None:
    """
    Release the cached client.
    """
    global _supabase

    _supabase = None
    logger.info("Supabase client released")
