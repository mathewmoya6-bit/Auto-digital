# app/integrations/supabase.py
# Auto-D Kenya - Supabase Integration
# ================================================================
# TYPE: INTEGRATION - Supabase client wrapper

import logging
from typing import Optional
from supabase import create_client, Client

from app.core.config import settings

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Supabase client wrapper."""
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client."""
        if cls._instance is None:
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                raise ValueError("Supabase credentials not configured")
            
            cls._instance = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            logger.info("✅ Supabase client initialized")
        
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset the client instance."""
        cls._instance = None
        logger.info("Supabase client reset")
