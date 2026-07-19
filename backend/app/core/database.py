# backend/app/core/database.py
import logging
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Singleton wrapper around the Supabase client."""

    _instance = None
    client: Client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        url = (settings.SUPABASE_URL or "").strip()
        key = (settings.SUPABASE_KEY or "").strip()

        if not url or not key:
            logger.error(
                "Supabase credentials missing. "
                f"SUPABASE_URL set: {bool(url)}, SUPABASE_KEY set: {bool(key)}"
            )
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must both be set "
                "(check Render environment variables)."
            )

        if not url.startswith("https://") or ".supabase.co" not in url:
            logger.error(f"SUPABASE_URL looks malformed: {url!r}")
            raise ValueError(
                "SUPABASE_URL does not look like a valid Supabase project URL."
            )

        if not key.startswith("eyJ"):
            logger.error("SUPABASE_KEY does not look like a valid JWT (check for typos, quotes, or wrong var).")
            raise ValueError(
                "SUPABASE_KEY does not look like a valid Supabase API key."
            )

        try:
            self.client = create_client(url, key)
            logger.info(f"Supabase client initialized for project: {url}")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    def get_client(self) -> Client:
        return self.client


# Module-level singleton instance used across the app
supabase_client = SupabaseClient()

# Primary export - use this in all files
supabase: Client = supabase_client.get_client()

# Alias for backward compatibility (for files that import 'db')
db = supabase
