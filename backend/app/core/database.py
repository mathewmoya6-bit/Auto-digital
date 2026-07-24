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
                "SUPABASE_URL and SUPABASE_KEY must both be set."
            )

        if not url.startswith("https://") or ".supabase.co" not in url:
            logger.error(f"SUPABASE_URL looks malformed: {url!r}")
            raise ValueError(
                "SUPABASE_URL does not look like a valid Supabase project URL."
            )

        if not key.startswith("eyJ"):
            logger.error(
                "SUPABASE_KEY does not look like a valid JWT."
            )
            raise ValueError(
                "SUPABASE_KEY does not look like a valid Supabase API key."
            )

        try:
            self.client = create_client(url, key)
            logger.info("=" * 70)
            logger.info("SUPABASE CLIENT INITIALIZED")
            logger.info(f"Project URL: {url}")
            logger.info(f"Key Type: {'service_role' if 'service_role' in key else 'JWT'}")

            # --------------------------------------------------
            # VERIFY DATABASE CONNECTION
            # --------------------------------------------------
            try:
                response = (
                    self.client
                    .table("service_prices")
                    .select("*")
                    .execute()
                )

                rows = response.data or []

                logger.info("SUPABASE CONNECTION TEST: SUCCESS")
                logger.info(f"service_prices rows: {len(rows)}")

                if rows:
                    logger.info("Available services:")
                    for row in rows:
                        logger.info(
                            f" - {row.get('service_type')} = "
                            f"{row.get('price')} {row.get('currency')}"
                        )
                else:
                    logger.warning(
                        "service_prices table returned ZERO rows."
                    )
                    logger.warning(
                        "Possible causes:"
                    )
                    logger.warning("  • Wrong Supabase project")
                    logger.warning("  • RLS blocking access")
                    logger.warning("  • Empty table")

            except Exception as db_error:
                logger.exception(
                    "SUPABASE CONNECTION TEST FAILED"
                )
                logger.exception(db_error)

            logger.info("=" * 70)

        except Exception as e:
            logger.exception("Failed to initialize Supabase client")
            raise

    def get_client(self) -> Client:
        return self.client


# Module-level singleton
supabase_client = SupabaseClient()

# Primary export
supabase: Client = supabase_client.get_client()

# Backward compatibility
db = supabase
