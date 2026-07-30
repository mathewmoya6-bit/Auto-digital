# app/core/database.py
# Auto-D Kenya - Database Connection
# ================================================================
# TYPE: CORE - Database connection and session management

import logging
from typing import Optional
from supabase import create_client, Client

from app.core.config import settings

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """
    Get Supabase client instance.
    
    Returns:
        Client: Supabase client
    
    Raises:
        ValueError: If Supabase credentials are not configured
    """
    global _supabase_client
    
    if _supabase_client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise ValueError("Supabase credentials not configured")
        
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        logger.info("✅ Supabase client initialized")
    
    return _supabase_client


async def init_db() -> None:
    """
    Initialize database connection.
    Test connection and log status.
    """
    try:
        client = get_supabase()
        # Test connection with a simple query
        response = client.table("services").select("count").limit(1).execute()
        logger.info("✅ Database connection verified")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        raise


async def close_db() -> None:
    """Close database connection."""
    global _supabase_client
    if _supabase_client:
        _supabase_client = None
        logger.info("Database connection closed")
