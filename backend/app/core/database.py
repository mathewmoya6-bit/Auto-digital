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
    Create the singleton backend Supabase client.

    The backend uses the Service Role key so trusted operations
    (payments, callbacks, service activation, admin tasks, etc.)
    bypass Row Level Security (RLS).
    """

    if not settings.SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is not configured.")

    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY is not configured."
        )

    logger.info("Initializing Supabase Service Role client...")

    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
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
        (
            client.table("services")
            .select("id")
            .limit(1)
            .execute()
        )

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
        (
            get_supabase()
            .table("services")
            .select("id")
            .limit(1)
            .execute()
        )

        return True

    except Exception:
        logger.exception("Database health check failed.")
        return False


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "create_supabase_client",
    "get_supabase",
    "init_db",
    "close_db",
    "database_health",
]
