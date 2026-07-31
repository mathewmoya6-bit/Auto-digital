"""
Auto-D Kenya - Database
=======================

Centralized Supabase client management.
"""

from __future__ import annotations

import logging
from typing import Optional

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

_supabase: Optional[Client] = None


# =============================================================================
# Client Factory
# =============================================================================

def create_supabase_client() -> Client:
    """
    Create a new Supabase client.
    """

    if not settings.SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is not configured.")

    if not settings.SUPABASE_KEY:
        raise RuntimeError("SUPABASE_KEY is not configured.")

    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY,
    )


# =============================================================================
# Singleton Client
# =============================================================================

def get_supabase() -> Client:
    """
    Return the singleton Supabase client.
    """

    global _supabase

    if _supabase is None:
        logger.info("Initializing Supabase client...")
        _supabase = create_supabase_client()

    return _supabase


# =============================================================================
# Startup
# =============================================================================

async def init_db() -> None:
    """
    Verify database connectivity.
    """

    client = get_supabase()

    try:
        client.table("services") \
            .select("id") \
            .limit(1) \
            .execute()

        logger.info("Database connection verified.")

    except Exception:
        logger.exception("Database connectivity check failed.")
        raise


# =============================================================================
# Shutdown
# =============================================================================

async def close_db() -> None:
    """
    Release cached resources.
    """

    global _supabase

    _supabase = None

    logger.info("Supabase client released.")


# =============================================================================
# Health Check
# =============================================================================

def database_health() -> bool:
    """
    Return True if the database is reachable.
    """

    try:
        get_supabase() \
            .table("services") \
            .select("id") \
            .limit(1) \
            .execute()

        return True

    except Exception:
        logger.exception("Database health check failed.")
        return False


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "get_supabase",
    "create_supabase_client",
    "init_db",
    "close_db",
    "database_health",
]
