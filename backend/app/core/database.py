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

            # ─── Determine the key's role ───
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

            # ──────────────────────────────────────────────────────────
            # VERIFY SERVICES TABLE
            # ──────────────────────────────────────────────────────────
            try:
                response = (
                    self.client
                    .table("services")
                    .select("id, code, name, price, active")
                    .execute()
                )
                rows = response.data or []
                logger.info("=" * 70)
                logger.info("SERVICES TABLE VERIFICATION")
                logger.info(f"Found {len(rows)} services:")
                
                if rows:
                    for row in rows:
                        logger.info(
                            f"  {row.get('id')} | {row.get('code')} | "
                            f"{row.get('name')} | {row.get('price')} KES | "
                            f"active: {row.get('active')}"
                        )
                    
                    # Verify expected services exist
                    expected = ["mileage", "valuation", "ownership"]
                    found = [row.get('code') for row in rows]
                    missing = [e for e in expected if e not in found]
                    if missing:
                        logger.warning(f"⚠️ Missing expected services: {missing}")
                    else:
                        logger.info("✅ All expected services found!")
                else:
                    logger.warning(
                        "services table returned ZERO rows. "
                        "Please insert the 3 services: mileage, valuation, ownership"
                    )
                logger.info("=" * 70)

            except Exception as db_error:
                logger.exception(
                    "❌ SERVICES TABLE VERIFICATION FAILED — "
                    "Make sure the 'services' table exists in your database"
                )

            # ──────────────────────────────────────────────────────────
            # VERIFY PAYMENTS TABLE
            # ──────────────────────────────────────────────────────────
            try:
                response = (
                    self.client
                    .table("payments")
                    .select("*")
                    .limit(1)
                    .execute()
                )
                logger.info("✅ Payments table is reachable")

            except Exception as e:
                logger.exception(
                    "❌ Payments table cannot be queried — "
                    "Make sure the 'payments' table exists"
                )

            # ──────────────────────────────────────────────────────────
            # VERIFY VEHICLE VARIANTS (for valuation engine)
            # ──────────────────────────────────────────────────────────
            try:
                variant = (
                    self.client
                    .table("vehicle_variants")
                    .select("id, name")
                    .eq("id", 728)
                    .limit(1)
                    .execute()
                )
                if variant.data:
                    logger.info(f"✅ Vehicle variant 728 found: {variant.data[0].get('name')}")
                else:
                    logger.warning("⚠️ Vehicle variant 728 not found")

            except Exception as e:
                logger.warning(
                    f"⚠️ Vehicle variant lookup failed: {e} — "
                    "Valuation engine may not work correctly"
                )

            # ──────────────────────────────────────────────────────────
            # VERIFY WRITE ACCESS TO PAYMENTS TABLE
            # Gated behind an env var so this doesn't run on every restart
            # ──────────────────────────────────────────────────────────
            if os.environ.get("RUN_STARTUP_DB_DIAGNOSTICS", "").lower() == "true":
                logger.info("-" * 50)
                logger.info("RUNNING STARTUP DB DIAGNOSTICS")
                logger.info("-" * 50)

                test_uuid = str(uuid.uuid4())
                test_checkout_id = f"startup-diagnostic-{test_uuid}"

                insert_ok = False
                try:
                    # ─── FIX: Use INTEGER for service_id ───
                    insert_resp = (
                        self.client
                        .table("payments")
                        .insert({
                            "id": test_uuid,
                            "checkout_request_id": test_checkout_id,
                            "status": "pending",
                            "amount": 0,
                            "currency": "KES",
                            "phone": "254700000000",
                            "service_id": 1,  # Existing service ID (mileage)
                            "service_name": "Diagnostic Test",
                            "user_id": None,
                        })
                        .execute()
                    )
                    if insert_resp.data:
                        insert_ok = True
                        logger.info("✅ SUPABASE WRITE TEST (payments): INSERT SUCCEEDED")
                    else:
                        logger.error(
                            "❌ SUPABASE WRITE TEST (payments): insert returned no "
                            "data — likely blocked by RLS or a schema mismatch, "
                            "even though no exception was raised."
                        )

                except Exception as insert_error:
                    logger.exception(
                        "❌ SUPABASE WRITE TEST (payments): INSERT FAILED — "
                        f"Error: {insert_error}"
                    )
                    if "permission denied" in str(insert_error) or "row-level security" in str(insert_error):
                        logger.error(
                            "   This is an RLS issue. Use the service_role key "
                            "or add RLS policies for the payments table."
                        )
                    elif "invalid input syntax for type integer" in str(insert_error):
                        logger.error(
                            "   This is a schema mismatch. Make sure service_id is "
                            "an INTEGER (1, 2, or 3) not a string."
                        )

                # Cleanup if insert succeeded
                if insert_ok:
                    try:
                        self.client.table("payments").delete().eq("id", test_uuid).execute()
                        logger.info("✅ SUPABASE WRITE TEST (payments): cleanup OK")
                    except Exception as cleanup_error:
                        logger.warning(
                            f"⚠️ SUPABASE WRITE TEST (payments): insert succeeded but "
                            f"cleanup delete failed — a leftover test row "
                            f"(id={test_uuid}) remains in your payments table and "
                            f"needs manual removal. Error: {cleanup_error}"
                        )

                logger.info("-" * 50)
                logger.info("DIAGNOSTICS COMPLETE")
                logger.info("-" * 50)
            else:
                logger.info(
                    "ℹ️ Startup DB diagnostics skipped (set "
                    "RUN_STARTUP_DB_DIAGNOSTICS=true to enable)"
                )

            logger.info("=" * 70)

        except Exception as e:
            logger.exception(f"❌ Failed to initialize Supabase client: {e}")
            raise

    def get_client(self) -> Client:
        return self.client

    def health_check(self) -> bool:
        """
        Health check method to verify Supabase connectivity.
        Returns True if connected, False otherwise.
        """
        try:
            self.client.table("services").select("id").limit(1).execute()
            logger.debug("✅ Supabase health check passed")
            return True
        except Exception as e:
            logger.error(f"❌ Supabase health check failed: {e}")
            return False


# Module-level singleton
supabase_client = SupabaseClient()

# Primary export
supabase: Client = supabase_client.get_client()

# Backward compatibility
db = supabase
