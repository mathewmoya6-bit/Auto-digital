# backend/app/core/database.py

import logging
import base64
import json
import uuid
import os
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Singleton wrapper around the Supabase client with health checks and diagnostics."""

    _instance: Optional['SupabaseClient'] = None
    client: Optional[Client] = None
    _initialized: bool = False
    _health_status: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize once - only if not already initialized."""
        if not self._initialized:
            self._initialize()

    def _decode_jwt_role(self, jwt: str) -> str:
        """
        Decode the `role` claim from a Supabase JWT without verifying the signature.
        Safe since this is the same unsigned payload sent with every request.
        """
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
        """Initialize the Supabase client with validation and diagnostics."""
        url = (settings.SUPABASE_URL or "").strip()
        key = (settings.SUPABASE_KEY or "").strip()

        # ─── Validate credentials ──────────────────────────────────────
        if not url or not key:
            logger.error(
                "Supabase credentials missing. "
                f"SUPABASE_URL set: {bool(url)}, SUPABASE_KEY set: {bool(key)}"
            )
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must both be set.")

        if not url.startswith("https://") or ".supabase.co" not in url:
            logger.error(f"SUPABASE_URL looks malformed: {url!r}")
            raise ValueError("SUPABASE_URL does not look like a valid Supabase project URL.")

        if not key.startswith("eyJ"):
            logger.error("SUPABASE_KEY does not look like a valid JWT.")
            raise ValueError("SUPABASE_KEY does not look like a valid Supabase API key.")

        try:
            # ─── Create client ──────────────────────────────────────────
            self.client = create_client(url, key)
            self._initialized = True
            self._health_status = True

            logger.info("=" * 70)
            logger.info("✅ SUPABASE CLIENT INITIALIZED")
            logger.info(f"📡 Project URL: {url}")

            # ─── Determine the key's role ──────────────────────────────
            actual_role = self._decode_jwt_role(key)
            logger.info(f"🔑 Key Role (decoded from JWT): {actual_role}")

            if actual_role != "service_role":
                logger.warning(
                    f"⚠️ SUPABASE_KEY has role '{actual_role}', not 'service_role'. "
                    "If Row Level Security (RLS) is enabled on any table this backend "
                    "needs to write to (e.g. `payments`), inserts/updates WILL be "
                    "silently blocked unless RLS policies allow this role. "
                    "Using the service_role key is recommended for backend services."
                )

            # ─── Run diagnostics ──────────────────────────────────────
            self._run_diagnostics()

            logger.info("=" * 70)

        except Exception as e:
            self._initialized = False
            self._health_status = False
            logger.exception(f"❌ Failed to initialize Supabase client: {e}")
            raise

    def _run_diagnostics(self):
        """Run comprehensive database diagnostics."""
        logger.info("-" * 50)
        logger.info("🔍 RUNNING DATABASE DIAGNOSTICS")
        logger.info("-" * 50)

        # ─── 1. Verify SERVICES table ──────────────────────────────────
        self._verify_services_table()

        # ─── 2. Verify PAYMENTS table ──────────────────────────────────
        self._verify_payments_table()

        # ─── 3. Verify VEHICLE VARIANTS ────────────────────────────────
        self._verify_vehicle_variants()

        # ─── 4. Verify SERVICE ACCESS table ────────────────────────────
        self._verify_service_access_table()

        # ─── 5. Verify USERS table ──────────────────────────────────────
        self._verify_users_table()

        # ─── 6. Write access test (optional, gated by env var) ─────────
        self._run_write_test()

        logger.info("-" * 50)
        logger.info("✅ DIAGNOSTICS COMPLETE")
        logger.info("-" * 50)

    def _verify_services_table(self):
        """Verify the services table exists and has expected data."""
        try:
            response = (
                self.client
                .table("services")
                .select("id, code, name, price, active, currency")
                .order("display_order")
                .execute()
            )
            rows = response.data or []
            logger.info(f"📋 SERVICES TABLE: Found {len(rows)} services")

            if rows:
                expected = ["mileage", "valuation", "ownership"]
                found = [row.get('code') for row in rows]
                missing = [e for e in expected if e not in found]

                for row in rows:
                    logger.info(
                        f"  • {row.get('code')} | {row.get('name')} | "
                        f"{row.get('price', 0)} {row.get('currency', 'KES')} | "
                        f"active: {row.get('active', False)}"
                    )

                if missing:
                    logger.warning(f"⚠️ Missing expected services: {missing}")
                else:
                    logger.info("✅ All expected services found!")

                # Check if any services have zero/negative price
                zero_priced = [row.get('code') for row in rows if row.get('price', 0) <= 0]
                if zero_priced:
                    logger.warning(f"⚠️ Services with zero/negative price: {zero_priced}")
            else:
                logger.warning(
                    "⚠️ SERVICES TABLE EMPTY — "
                    "Please insert the 3 services: mileage, valuation, ownership"
                )

        except Exception as e:
            logger.exception(
                "❌ SERVICES TABLE VERIFICATION FAILED — "
                "Make sure the 'services' table exists in your database"
            )

    def _verify_payments_table(self):
        """Verify the payments table exists and is accessible."""
        try:
            response = (
                self.client
                .table("payments")
                .select("id")
                .limit(1)
                .execute()
            )
            logger.info("✅ PAYMENTS TABLE: Reachable")

            # Check if there are any pending payments that need attention
            try:
                pending = (
                    self.client
                    .table("payments")
                    .select("id", count="exact")
                    .eq("status", "pending")
                    .execute()
                )
                count = pending.count or 0
                if count > 0:
                    logger.info(f"📋 Pending payments: {count} (will be expired after timeout)")
            except Exception:
                pass

        except Exception as e:
            logger.exception(
                "❌ PAYMENTS TABLE VERIFICATION FAILED — "
                "Make sure the 'payments' table exists"
            )

    def _verify_service_access_table(self):
        """Verify the service_access table exists."""
        try:
            response = (
                self.client
                .table("service_access")
                .select("id")
                .limit(1)
                .execute()
            )
            logger.info("✅ SERVICE_ACCESS TABLE: Reachable")
        except Exception as e:
            logger.warning(
                "⚠️ SERVICE_ACCESS TABLE VERIFICATION FAILED — "
                "Service unlock functionality may not work. "
                "Make sure the 'service_access' table exists."
            )

    def _verify_users_table(self):
        """Verify the users table exists."""
        try:
            response = (
                self.client
                .table("users")
                .select("id")
                .limit(1)
                .execute()
            )
            logger.info("✅ USERS TABLE: Reachable")
        except Exception as e:
            logger.warning(
                "⚠️ USERS TABLE VERIFICATION FAILED — "
                "User authentication may not work. "
                "Make sure the 'users' table exists."
            )

    def _verify_vehicle_variants(self):
        """Verify vehicle variants table for valuation engine."""
        try:
            # Try to fetch a known variant (728 is Toyota Hilux)
            variant = (
                self.client
                .table("vehicle_variants")
                .select("id, name, make, model")
                .eq("id", 728)
                .limit(1)
                .execute()
            )
            if variant.data:
                logger.info(
                    f"✅ VEHICLE VARIANTS: Found variant 728: "
                    f"{variant.data[0].get('name', 'Unknown')}"
                )
            else:
                logger.warning("⚠️ Vehicle variant 728 not found — Valuation engine may not work")
        except Exception as e:
            logger.warning(
                f"⚠️ Vehicle variant lookup failed: {e} — "
                "Valuation engine may not work correctly"
            )

    def _run_write_test(self):
        """
        Verify write access to the payments table.
        Gated behind RUN_STARTUP_DB_DIAGNOSTICS env var.
        """
        if os.environ.get("RUN_STARTUP_DB_DIAGNOSTICS", "").lower() != "true":
            logger.info("ℹ️ Write test skipped (set RUN_STARTUP_DB_DIAGNOSTICS=true to enable)")
            return

        logger.info("-" * 30)
        logger.info("📝 RUNNING WRITE ACCESS TEST")
        logger.info("-" * 30)

        test_uuid = str(uuid.uuid4())
        test_checkout_id = f"diagnostic-{test_uuid[:8]}"

        insert_ok = False
        try:
            # First check if there's a service with ID 1
            service_check = (
                self.client
                .table("services")
                .select("id")
                .eq("id", 1)
                .limit(1)
                .execute()
            )

            service_id = 1
            if not service_check.data:
                # Try to find any service
                services = (
                    self.client
                    .table("services")
                    .select("id")
                    .limit(1)
                    .execute()
                )
                if services.data:
                    service_id = services.data[0].get("id")
                else:
                    logger.warning("⚠️ No services found for write test — skipping insert")
                    return

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
                    "service_id": service_id,
                    "service_name": "Diagnostic Test",
                    "user_id": None,
                })
                .execute()
            )

            if insert_resp.data:
                insert_ok = True
                logger.info("✅ WRITE TEST: INSERT SUCCEEDED")
            else:
                logger.error(
                    "❌ WRITE TEST: Insert returned no data — "
                    "likely blocked by RLS or schema mismatch"
                )

        except Exception as insert_error:
            logger.exception(f"❌ WRITE TEST: INSERT FAILED — {insert_error}")
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
                logger.info("✅ WRITE TEST: Cleanup OK")
            except Exception as cleanup_error:
                logger.warning(
                    f"⚠️ WRITE TEST: Insert succeeded but cleanup failed — "
                    f"test row (id={test_uuid}) remains. Error: {cleanup_error}"
                )

        logger.info("-" * 30)

    def get_client(self) -> Client:
        """Get the Supabase client instance."""
        if not self._initialized or self.client is None:
            raise RuntimeError("Supabase client not initialized. Call initialize() first.")
        return self.client

    def health_check(self) -> bool:
        """
        Health check method to verify Supabase connectivity.
        Returns True if connected, False otherwise.
        """
        if not self._initialized or self.client is None:
            return False

        try:
            self.client.table("services").select("id").limit(1).execute()
            self._health_status = True
            return True
        except Exception as e:
            logger.error(f"❌ Supabase health check failed: {e}")
            self._health_status = False
            return False

    def get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status."""
        return {
            "initialized": self._initialized,
            "healthy": self._health_status,
            "client_exists": self.client is not None,
        }


# ─── Module-level singleton ─────────────────────────────────────────
supabase_client = SupabaseClient()

# Primary export
supabase: Client = supabase_client.get_client()

# Backward compatibility
db = supabase

# Utility functions for common operations
def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    try:
        supabase.table(table_name).select("id").limit(1).execute()
        return True
    except Exception:
        return False

def get_table_count(table_name: str) -> int:
    """Get count of records in a table."""
    try:
        response = supabase.table(table_name).select("id", count="exact").limit(1).execute()
        return response.count or 0
    except Exception:
        return 0

def get_service_by_code(code: str) -> Optional[Dict]:
    """Get a service by its code."""
    try:
        response = supabase.table("services").select("*").eq("code", code).limit(1).execute()
        return response.data[0] if response.data else None
    except Exception:
        return None

def get_active_services() -> List[Dict]:
    """Get all active services."""
    try:
        response = supabase.table("services").select("*").eq("active", True).order("display_order").execute()
        return response.data or []
    except Exception:
        return []

# ─── Export ─────────────────────────────────────────────────────────
__all__ = [
    "supabase",
    "db",
    "supabase_client",
    "table_exists",
    "get_table_count",
    "get_service_by_code",
    "get_active_services",
]
