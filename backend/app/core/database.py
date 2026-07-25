# backend/app/core/database.py

import logging
import base64
import json
import uuid
import os
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

    def _decode_jwt_role(self, jwt: str) -> str:
        """Decode the `role` claim from a Supabase JWT without verifying the
        signature — safe, since this is the same unsigned payload sent with
        every request. Returns 'unknown' if it can't be parsed."""
        try:
            parts = jwt.split(".")
            if len(parts) != 3:
                return "unknown (not a 3-part JWT)"
            payload_b64 = parts[1]
            # base64url needs padding restored
            padding = "=" * (-len(payload_b64) % 4)
            payload_json = base64.urlsafe_b64decode(payload_b64 + padding)
            payload = json.loads(payload_json)
            return payload.get("role", "unknown (no role claim)")
        except Exception as e:
            return f"unknown (decode failed: {e})"

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

            # ─── ACTUALLY determine the key's role, don't guess from a
            #     substring match ───
            actual_role = self._decode_jwt_role(key)
            logger.info(f"Key Role (decoded from JWT): {actual_role}")
            
            if actual_role != "service_role":
                logger.warning(
                    f"⚠️ SUPABASE_KEY has role '{actual_role}', not "
                    "'service_role'. If Row Level Security is enabled on any "
                    "table this backend needs to write to (e.g. `payments`), "
                    "inserts/updates from this backend WILL be silently "
                    "blocked unless RLS policies explicitly allow this role. "
                    "Using the service_role key here is almost always what "
                    "a backend service wants, since it bypasses RLS entirely."
                )

            # --------------------------------------------------
            # VERIFY DATABASE CONNECTION (read test)
            # --------------------------------------------------
            try:
                response = (
                    self.client
                    .table("service_prices")
                    .select("*")
                    .execute()
                )
                rows = response.data or []
                logger.info("SUPABASE READ TEST (service_prices): SUCCESS")
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
                    "SUPABASE READ TEST (service_prices) FAILED"
                )

            # --------------------------------------------------
            # VERIFY WRITE ACCESS TO THE TABLE THAT ACTUALLY MATTERS:
            # payments. Insert a throwaway row and delete it immediately.
            # Gated behind an env var so this doesn't run against production
            # on every restart once you're done diagnosing — set
            # RUN_STARTUP_DB_DIAGNOSTICS=true in Render temporarily.
            # --------------------------------------------------
            if os.environ.get("RUN_STARTUP_DB_DIAGNOSTICS", "").lower() == "true":
                test_uuid = str(uuid.uuid4())  # must be a bare UUID — payments.id is
                                                # typed uuid, a prefixed string like
                                                # "startup-write-test-<uuid>" will fail
                                                # with "invalid input syntax for type uuid"
                                                # and masquerade as an RLS failure.
                test_checkout_id = f"startup-diagnostic-{test_uuid}"  # this one's fine
                                                                       # as free text

                insert_ok = False
                try:
                    insert_resp = (
                        self.client
                        .table("payments")
                        .insert({
                            "id": test_uuid,
                            "checkout_request_id": test_checkout_id,
                            "status": "pending",
                            "amount": 0,
                            "user_id": None,
                            "service_id": "startup_test",
                        })
                        .execute()
                    )
                    if insert_resp.data:
                        insert_ok = True
                        logger.info("SUPABASE WRITE TEST (payments): INSERT SUCCEEDED")
                    else:
                        logger.error(
                            "SUPABASE WRITE TEST (payments): insert returned no "
                            "data — likely blocked by RLS or a schema mismatch, "
                            "even though no exception was raised."
                        )
                except Exception as insert_error:
                    logger.exception(
                        "SUPABASE WRITE TEST (payments): INSERT FAILED — read the "
                        "exception message above carefully. 'permission denied' or "
                        "'new row violates row-level security policy' means it's "
                        "RLS. Anything else (invalid input syntax, null value in "
                        "column X, foreign key violation) means it's a schema/"
                        "constraint issue, not permissions — this diagnostic insert "
                        "used dummy values (user_id=None, service_id='startup_test') "
                        "that may not satisfy your table's constraints even with "
                        "correct permissions."
                    )

                # Only attempt cleanup if insert actually succeeded, and report
                # its failure separately so it's never confused with an insert
                # failure.
                if insert_ok:
                    try:
                        self.client.table("payments").delete().eq("id", test_uuid).execute()
                        logger.info("SUPABASE WRITE TEST (payments): cleanup OK")
                    except Exception as cleanup_error:
                        logger.warning(
                            f"SUPABASE WRITE TEST (payments): insert succeeded but "
                            f"cleanup delete failed — a leftover test row "
                            f"(id={test_uuid}) remains in your payments table and "
                            f"needs manual removal. This does NOT mean insert is "
                            f"broken. Error: {cleanup_error}"
                        )
            else:
                logger.info(
                    "SUPABASE WRITE TEST (payments): skipped (set "
                    "RUN_STARTUP_DB_DIAGNOSTICS=true to enable)"
                )

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
