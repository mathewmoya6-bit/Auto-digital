# app/modules/mpesa/stk_push.py
# Auto-D Kenya - M-Pesa STK Push
# ================================================================
# TYPE: MODULE - M-Pesa STK Push logic
#
# Fixes applied this pass:
#   1.  _post_with_retry() now refreshes an expired OAuth token on a 401
#       and retries the same request once, instead of hard-failing
#   2.  Notification + audit-log writes inside the unlock transaction are
#       now fire-and-forget background tasks — a slow/failed notification
#       can no longer make a successful unlock look like it failed
#   4.  mpesa_callback_replays now self-prunes rows older than
#       REPLAY_RETENTION_DAYS (same random-sampling pattern as the
#       existing payment_logs cleanup)
#   5.  Service cache is a bounded cachetools.TTLCache (maxsize=500)
#       instead of an unbounded dict
#   6.  Audit-log writes (_log_payment_event) throughout the callback path
#       are now background tasks so they can't add latency before this
#       service responds to Safaricom
#   7.  Notification creation uses upsert() instead of insert + catch
#       duplicate-key
#   9.  Retry backoff now uses wait_random_exponential (jittered) instead
#       of a fixed exponential ladder, to avoid retry storms
#   10. generate_callback_signature() docstring now explicitly says it's
#       unused and why — Safaricom doesn't sign callbacks, so there was
#       nothing on the other end to check it against
#   12. CALLBACK_SECRET is now OPTIONAL — warn but don't fail startup
#
# NOT changed in this file (needs infra/DB, documented in comments below):
#   3.  UNIQUE constraint on payments.checkout_request_id — add via
#       migration, this file already treats it as unique
#   8.  Currency validation on callback_amount — add once you confirm
#       whether/how currency is stored on payments/services
#   11. unlock_paid_service RPC should use SELECT ... FOR UPDATE — that's
#       inside the Postgres function body, not this file
#
# Previously applied fixes (kept):
#   - HTTP retry wraps STK push + status-query calls
#   - Replay protection is DB-backed (persists across restarts/instances)
#   - Logging uses plain f-strings, not extra={} dicts
#   - _upsert_user_service() uses a real DB-level upsert (ON CONFLICT)
#   - Health check pings a dedicated no-op RPC instead of calling
#     unlock_paid_service with fake data
#   - Removed duplicate user_services creation in initiate_push()
#   - verify_payment_status() is read-only (no database writes)
#   - callback_amount validation
#   - payment_logs retention policy
#   - notification creation is idempotent
#   - PaymentContext correlation object for structured logging

import asyncio
import base64
import hashlib
import hmac
import logging
import math
import secrets
import string
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

import httpx
from cachetools import TTLCache
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception,
)

from app.core.config import settings
from app.core.exceptions import AppException, NotFoundException, ValidationException
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

# ─── CONSTANTS ──────────────────────────────────────────────

class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    UNKNOWN = "unknown"

    @property
    def is_terminal(self) -> bool:
        return self in (
            PaymentStatus.COMPLETED,
            PaymentStatus.FAILED,
            PaymentStatus.CANCELLED,
            PaymentStatus.EXPIRED,
        )


class UnlockStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ServiceStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    EXPIRED = "expired"
    INACTIVE = "inactive"


# ─── CONFIGURATION ──────────────────────────────────────────

HTTP_TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_WAIT_MIN = 2
RETRY_WAIT_MAX = 30
DESCRIPTION_MAX_LENGTH = 100
ACCESS_TOKEN_EXPIRY_OFFSET = 60
DEFAULT_EXPIRY_DAYS = 365
STALE_PAYMENT_HOURS = 24
MAX_CONNECTIONS = 20
MAX_KEEPALIVE = 10
MINIMUM_AMOUNT = 1
ACCOUNT_REFERENCE_LENGTH = 12
ACCOUNT_REFERENCE_ALPHABET = string.ascii_uppercase + string.digits
LOG_RETENTION_DAYS = 180
CALLBACK_SIGNATURE_TTL = 300  # 5 minutes, in-memory fast-path cache only
SERVICE_CACHE_TTL = 300  # 5 minutes
SERVICE_CACHE_MAXSIZE = 500  # fix #5: bounded, so a huge catalog can't grow this unbounded
REPLAY_RETENTION_DAYS = 30  # fix #4: mpesa_callback_replays rows older than this get purged

# Table names
TABLE_PAYMENTS = "payments"
TABLE_USER_SERVICES = "user_services"
TABLE_SERVICES = "services"
TABLE_PAYMENT_LOGS = "payment_logs"
TABLE_NOTIFICATIONS = "notifications"
TABLE_CALLBACK_REPLAYS = "mpesa_callback_replays"  # NEW — see migration note below

# Safaricom constants
TRANSACTION_TYPE = "CustomerPayBillOnline"

# Retryable HTTP status codes
RETRYABLE_HTTP_STATUS = {429, 500, 502, 503, 504}
NON_RETRYABLE_HTTP_STATUS = {400, 401, 403, 404}


# ─── DATA CLASSES FOR STRUCTURED LOGGING ──────────────────

@dataclass
class PaymentContext:
    """Correlation context for payment operations."""
    checkout_request_id: str
    merchant_request_id: str = ""
    payment_id: int = 0
    user_id: str = ""
    service_id: int = 0
    amount: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkout_request_id": self.checkout_request_id,
            "merchant_request_id": self.merchant_request_id,
            "payment_id": self.payment_id,
            "user_id": self.user_id,
            "service_id": self.service_id,
            "amount": self.amount,
        }

    def __str__(self) -> str:
        d = self.to_dict()
        return " ".join(f"{k}={v}" for k, v in d.items())


# ─── PHONE VALIDATION ──────────────────────────────────────

def normalize_phone(phone: str) -> str:
    """Normalize phone number to 254 format."""
    cleaned = ''.join(filter(str.isdigit, phone))
    if not cleaned:
        raise ValidationException("Phone number is empty")

    if cleaned.startswith('2540'):
        cleaned = cleaned.replace('2540', '254', 1)

    if cleaned.startswith('0'):
        cleaned = cleaned[1:]

    if cleaned.startswith('254'):
        normalized = cleaned
    else:
        normalized = f"254{cleaned}"

    if len(normalized) != 12:
        raise ValidationException(f"Phone number must be 12 digits, got {len(normalized)}")

    if not (normalized.startswith('2547') or normalized.startswith('2541')):
        raise ValidationException(f"Phone must start with 2547 or 2541, got {normalized[:4]}")

    return normalized


def mask_sensitive(value: str, visible: int = 4) -> str:
    """Mask sensitive values for logging."""
    if not value:
        return "***"
    if len(value) <= visible * 2:
        return value[:2] + "***" + value[-2:]
    return f"{value[:visible]}...{value[-visible:]}"


def generate_account_reference(service_name: str = "", user_id: str = "") -> str:
    """
    Generate a meaningful account reference for support.
    Format: {prefix}-{random}
    """
    if service_name:
        prefix = service_name[:3].upper()
    elif user_id:
        prefix = user_id[:3].upper()
    else:
        prefix = "PAY"

    random_part = ''.join(secrets.choice(ACCOUNT_REFERENCE_ALPHABET) for _ in range(8))
    return f"{prefix}-{random_part}"


def generate_callback_signature(checkout_request_id: str, timestamp: str) -> str:
    """
    fix #10: kept for backward compatibility, but NOT wired into the
    callback path — and it shouldn't be, without more infrastructure.

    Safaricom does not sign its STK callbacks with an HMAC of any kind, so
    there's nothing on the receiving end to verify this signature against
    unless you're running your own reverse proxy that independently signs
    requests before they hit this service. Calling this function and
    checking its output against an incoming callback would just be
    comparing two values this service generated itself, which verifies
    nothing.

    The real protections against forged/malicious callbacks, already in
    place across router.py + this file, are:
      - a shared secret on the callback URL itself (query param, checked
        in router.py before the body is even parsed)
      - matching CheckoutRequestID to an existing, known payment record
      - verifying MerchantRequestID matches what was issued at STK-push
        time (see process_callback())
      - validating the callback amount against the expected amount
      - refusing to reprocess a payment that's already in a terminal
        status (idempotency)
      - DB-backed replay detection (see _is_replay())

    If you later put this behind a reverse proxy that signs requests with
    a shared key, THIS function becomes genuinely useful — call it there
    to generate the signature, and verify it in router.py before this
    function is ever reached. Until then, don't call it.
    """
    message = f"{checkout_request_id}:{timestamp}"
    return hmac.new(
        settings.MPESA_CALLBACK_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()


def _is_retryable_http_error(exc: BaseException) -> bool:
    """fix #16: shared predicate for what counts as a transient, retryable
    failure — connection-level issues, plus specific 429/5xx status codes.
    Anything else (4xx auth/validation errors) is NOT retried."""
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError, ConnectionError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_HTTP_STATUS
    return False


# ─── HELPER: Async DB operations ──────────────────────────

async def execute_supabase_async(query_func, *args, **kwargs):
    """Execute Supabase query in thread to avoid blocking."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: query_func(*args, **kwargs))


# ─── STK PUSH SERVICE ─────────────────────────────────────

class StkPushService:
    """M-Pesa STK Push service with payment verification."""

    def __init__(self):
        self.supabase = get_supabase()
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE
        self.callback_url = settings.MPESA_CALLBACK_URL
        self.callback_secret = settings.MPESA_CALLBACK_SECRET

        self.base_url = (
            "https://api.safaricom.co.ke"
            if settings.MPESA_ENVIRONMENT == "production"
            else "https://sandbox.safaricom.co.ke"
        )

        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self._token_lock = asyncio.Lock()
        self._closed = False

        # HTTP client with connection pooling
        self._client = None
        self._client_lock = asyncio.Lock()

        # Cache for service data — fix #5: bounded TTLCache instead of a
        # plain dict, so a catalog with thousands of services can't grow
        # this unbounded. Handles expiry internally too.
        self._service_cache: TTLCache = TTLCache(maxsize=SERVICE_CACHE_MAXSIZE, ttl=SERVICE_CACHE_TTL)

        # Cache for active column detection
        self._service_active_column: Optional[str] = None
        self._service_column_lock = asyncio.Lock()

        # In-memory replay fast-path cache (see _is_replay for the
        # authoritative, DB-backed check — this just avoids a DB round
        # trip for the common case of Safaricom re-firing the same
        # callback seconds apart on the *same* process/instance).
        self._callback_cache: Dict[str, datetime] = {}
        self._cache_lock = asyncio.Lock()

        # fix #2 / #6: strong references for fire-and-forget background
        # tasks (notifications, audit logging) so they aren't garbage
        # collected mid-flight — asyncio only holds a weak reference to
        # tasks created via create_task().
        self._background_tasks: set = set()

        # Validate configuration
        self._validate_configuration()
        self._log_configuration()

    # ─── HEALTH CHECK ────────────────────────────────────────

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check endpoint."""
        health = {
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        try:
            # 1. Database connectivity
            db_start = datetime.now()
            try:
                await execute_supabase_async(
                    lambda: self.supabase.table(TABLE_PAYMENTS).select("id").limit(1).execute()
                )
                health["checks"]["database"] = {
                    "status": "healthy",
                    "response_time_ms": (datetime.now() - db_start).total_seconds() * 1000
                }
            except Exception as e:
                health["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
                health["status"] = "degraded"

            # 2. OAuth token
            try:
                token_start = datetime.now()
                await self._get_access_token()
                health["checks"]["oauth"] = {
                    "status": "healthy",
                    "response_time_ms": (datetime.now() - token_start).total_seconds() * 1000
                }
            except Exception as e:
                health["checks"]["oauth"] = {"status": "unhealthy", "error": str(e)}
                health["status"] = "degraded"

            # 3. RPC availability — fix #20: no longer calls unlock_paid_service
            # with fabricated payment/user/service IDs. Even with p_payment_id=0,
            # that's still a real invocation of a function that performs writes,
            # which has no business running on every health check hit.
            #
            # Instead this pings a dedicated, side-effect-free function. Create
            # it once in Supabase:
            #
            #   CREATE OR REPLACE FUNCTION mpesa_health_ping()
            #   RETURNS boolean
            #   LANGUAGE sql
            #   AS $$ SELECT true; $$;
            #
            # If that function doesn't exist yet, this check reports "unknown"
            # (not "unhealthy") so a missing ping-RPC doesn't page you at 2am.
            try:
                rpc_start = datetime.now()
                await execute_supabase_async(
                    lambda: self.supabase.rpc("mpesa_health_ping", {}).execute()
                )
                health["checks"]["rpc"] = {
                    "status": "healthy",
                    "response_time_ms": (datetime.now() - rpc_start).total_seconds() * 1000
                }
            except Exception as e:
                health["checks"]["rpc"] = {
                    "status": "unknown",
                    "message": "mpesa_health_ping RPC not found — see health_check() docstring/comment to add it",
                    "error": str(e)
                }
                # Deliberately NOT downgrading overall status for this one —
                # it's a missing convenience probe, not a real outage signal.

            # 4. Services table readable
            try:
                services_start = datetime.now()
                await self._get_service_active_column()
                health["checks"]["services_table"] = {
                    "status": "healthy",
                    "response_time_ms": (datetime.now() - services_start).total_seconds() * 1000
                }
            except Exception as e:
                health["checks"]["services_table"] = {"status": "unhealthy", "error": str(e)}
                health["status"] = "degraded"

            # 5. Callback URL configured
            if self.callback_url and "localhost" not in self.callback_url:
                health["checks"]["callback_url"] = {"status": "healthy", "url_configured": True}
            else:
                health["checks"]["callback_url"] = {
                    "status": "warning",
                    "url_configured": False,
                    "message": "Callback URL is not set or uses localhost"
                }

        except Exception as e:
            health["status"] = "unhealthy"
            health["error"] = str(e)

        return health

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling."""
        if self._closed:
            raise RuntimeError("Service is closed")
        async with self._client_lock:
            if self._client is None or self._client.is_closed:
                self._client = httpx.AsyncClient(
                    timeout=httpx.Timeout(HTTP_TIMEOUT),
                    limits=httpx.Limits(
                        max_connections=MAX_CONNECTIONS,
                        max_keepalive_connections=MAX_KEEPALIVE
                    )
                )
            return self._client

    async def close(self) -> None:
        """Close HTTP client session."""
        self._closed = True
        async with self._client_lock:
            if self._client and not self._client.is_closed:
                await self._client.aclose()
                logger.info("HTTP client closed")
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _spawn_background(self, coro) -> asyncio.Task:
        """fix #2 / #6: run a coroutine (notification creation, audit
        logging) without making the caller wait for it. Keeps a strong
        reference in self._background_tasks until it finishes so it can't
        be silently garbage-collected mid-flight, and logs (rather than
        raises) if the task itself errors — a background log/notification
        failure should never surface as an error to whoever's awaiting the
        payment flow."""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)

        def _on_done(t: asyncio.Task):
            self._background_tasks.discard(t)
            if t.cancelled():
                return
            exc = t.exception()
            if exc:
                logger.error(f"Background task failed | error={exc}")

        task.add_done_callback(_on_done)
        return task

    def _validate_configuration(self) -> None:
        """Validate M-Pesa configuration at startup."""
        # fix #12: CALLBACK_SECRET is now OPTIONAL
        # Only require the truly mandatory M-Pesa credentials
        required = {
            "MPESA_CONSUMER_KEY": self.consumer_key,
            "MPESA_CONSUMER_SECRET": self.consumer_secret,
            "MPESA_PASSKEY": self.passkey,
            "MPESA_SHORTCODE": self.shortcode,
            "MPESA_CALLBACK_URL": self.callback_url,
        }

        errors = []
        for name, value in required.items():
            if not value:
                errors.append(name)

        # CALLBACK_SECRET is optional — warn if not set
        if not self.callback_secret:
            logger.warning(
                "MPESA_CALLBACK_SECRET not configured. "
                "Callback signature verification is disabled. "
                "This is acceptable if you're not using HMAC-signed callbacks."
            )

        if errors:
            raise AppException(
                f"M-Pesa configuration incomplete: {', '.join(errors)}. "
                f"Please set these environment variables.",
                500
            )

        # Log a warning if callback URL uses localhost in production
        if settings.MPESA_ENVIRONMENT == "production" and "localhost" in self.callback_url:
            logger.warning(
                "MPESA_CALLBACK_URL contains 'localhost' in production environment. "
                "Safaricom cannot reach localhost. Please use a public URL."
            )

    def _log_configuration(self) -> None:
        """Log M-Pesa configuration."""
        callback_host = self.callback_url.split("/")[2] if "://" in self.callback_url else "unset"
        # fix #18: plain f-string instead of extra={} — see module docstring.
        logger.info(
            f"M-Pesa configuration loaded | environment={settings.MPESA_ENVIRONMENT} "
            f"base_url={self.base_url} shortcode={self.shortcode} callback_host={callback_host} "
            f"callback_secret_configured={'yes' if self.callback_secret else 'no'}"
        )

    def _get_expiry_date(self, expiry_days: Optional[int] = None) -> str:
        """Get expiry date for service access."""
        days = expiry_days if expiry_days and expiry_days > 0 else DEFAULT_EXPIRY_DAYS
        return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

    # ─── TOKEN MANAGEMENT ────────────────────────────────────

    def _token_is_fresh(self) -> bool:
        if not (self.access_token and self.token_expiry):
            return False
        buffer_time = timedelta(seconds=ACCESS_TOKEN_EXPIRY_OFFSET)
        return datetime.now(timezone.utc) < (self.token_expiry - buffer_time)

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        # fix #9: wait_random_exponential adds jitter (multiplier is randomized
        # per attempt) instead of a deterministic 2/4/8s ladder — this stops
        # every failing instance from retrying in lockstep and hammering
        # Safaricom's API at the exact same moments (a "retry storm").
        wait=wait_random_exponential(multiplier=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),
        retry=retry_if_exception(_is_retryable_http_error),
        reraise=True
    )
    async def _get_access_token(self) -> str:
        """Get OAuth access token, with double-checked locking."""
        if self._token_is_fresh():
            return self.access_token

        async with self._token_lock:
            if self._token_is_fresh():
                logger.debug("Using token refreshed by a concurrent request")
                return self.access_token

            auth = base64.b64encode(
                f"{self.consumer_key}:{self.consumer_secret}".encode()
            ).decode()

            url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
            logger.info("Requesting new OAuth token")

            try:
                client = await self._get_client()
                response = await client.get(
                    url,
                    headers={"Authorization": f"Basic {auth}", "Accept": "application/json"}
                )

                if response.status_code == 401:
                    logger.error("OAuth failed: Invalid credentials (401)")
                    self.clear_token_cache()
                    raise AppException("M-Pesa OAuth credentials invalid", 401)

                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    self.clear_token_cache()
                    raise AppException("M-Pesa OAuth credentials invalid", 401)
                raise

            data = response.json()
            token = data.get("access_token")
            if not token:
                error_msg = data.get("error", data.get("error_description", "Unknown error"))
                raise AppException(f"OAuth failed: {error_msg}", 503)

            expires_in = int(data.get("expires_in", 3600))
            self.access_token = token
            self.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            logger.info(f"OAuth token obtained | expires_in_seconds={expires_in}")
            return token

    def clear_token_cache(self) -> None:
        """Clear the cached access token to force refresh."""
        self.access_token = None
        self.token_expiry = None
        logger.info("Token cache cleared")

    # ─── RETRYABLE HTTP POST (fix #16) ──────────────────────
    # Both the STK push initiation and the status query hit this. Transient
    # 429/500/502/503/504 responses and connection-level failures are
    # retried with exponential backoff; anything else (400/401/403/404,
    # or a successful 2xx) passes straight through on the first attempt.

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_random_exponential(multiplier=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),  # fix #9: jittered
        retry=retry_if_exception(_is_retryable_http_error),
        reraise=True
    )
    async def _post_with_retry(self, url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> httpx.Response:
        client = await self._get_client()
        response = await client.post(url, headers=headers, json=payload)

        # fix #1: Safaricom's token can expire slightly earlier than the
        # `expires_in` value it originally quoted us, so _token_is_fresh()
        # can say "fine" right before a call comes back 401. Rather than
        # let that propagate as a hard failure (it's not in
        # RETRYABLE_HTTP_STATUS, so the @retry decorator above won't touch
        # it), refresh the token once here and retry the same request
        # immediately with the new one.
        if response.status_code == 401:
            logger.warning("Got 401 from Safaricom mid-request — refreshing token and retrying once")
            self.clear_token_cache()
            new_token = await self._get_access_token()
            headers = dict(headers)
            headers["Authorization"] = f"Bearer {new_token}"
            response = await client.post(url, headers=headers, json=payload)

        response.raise_for_status()
        return response

    # ─── SERVICE CACHE ──────────────────────────────────────

    async def _get_cached_service(self, service_id: int) -> Optional[Dict[str, Any]]:
        """Get service from cache or database. TTLCache handles both
        expiry and max-size eviction internally now (fix #5)."""
        cached = self._service_cache.get(service_id)
        if cached is not None:
            return cached

        try:
            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_SERVICES).select("*").eq("id", service_id).maybe_single().execute()
            )
            if result.data:
                self._service_cache[service_id] = result.data
                return result.data
        except Exception as e:
            logger.error(f"Error fetching service | service_id={service_id} error={e}")

        return None

    # ─── REPLAY PROTECTION (fix #17) ────────────────────────
    # In-memory cache is a fast-path only; it does NOT survive restarts,
    # deploys, or multiple Render instances. The database check below is
    # the actual source of truth.
    #
    # Requires a migration once:
    #
    #   CREATE TABLE IF NOT EXISTS mpesa_callback_replays (
    #       checkout_request_id text PRIMARY KEY,
    #       processed_at timestamptz NOT NULL DEFAULT now()
    #   );
    #
    # (Also fine to skip this table and rely purely on the existing
    # "payment already terminal" idempotency check in process_callback() —
    # that check is itself DB-backed and closes most of the same gap.
    # This adds a second, independent layer specifically against exact
    # duplicate callback replays arriving before the payment row updates.)

    async def _is_replay(self, checkout_request_id: str) -> bool:
        """Returns True if this checkout_request_id has already been seen —
        checks the fast in-memory cache first, then the DB as the
        authoritative record. Records the ID as seen either way."""
        now = datetime.now(timezone.utc)

        async with self._cache_lock:
            expired = [
                k for k, v in self._callback_cache.items()
                if now - v > timedelta(seconds=CALLBACK_SIGNATURE_TTL)
            ]
            for k in expired:
                del self._callback_cache[k]

            if checkout_request_id in self._callback_cache:
                return True

            self._callback_cache[checkout_request_id] = now

        try:
            await execute_supabase_async(
                lambda: self.supabase.table(TABLE_CALLBACK_REPLAYS).insert({
                    "checkout_request_id": checkout_request_id,
                    "processed_at": now.isoformat()
                }).execute()
            )
            # fix #4: same random-sampling pattern as _cleanup_old_logs —
            # avoid running a DELETE on every single callback, but make sure
            # it happens regularly so this table doesn't grow forever.
            if secrets.randbelow(100) < 5:  # 5% chance
                self._spawn_background(self._cleanup_old_replays())
            return False
        except Exception as e:
            if "duplicate key" in str(e).lower() or "23505" in str(e):
                return True
            # Table missing, or any other DB error: don't block real payment
            # processing on this secondary safeguard — fall back to relying
            # on the in-memory cache + the terminal-status idempotency check
            # further down in process_callback().
            logger.warning(
                f"Replay-protection DB check failed, continuing on in-memory cache only | "
                f"checkout_request_id={mask_sensitive(checkout_request_id)} error={e}"
            )
            return False

    # ─── DATABASE HELPERS (Async) ──────────────────────────

    async def _log_payment_event(
        self,
        checkout_request_id: str,
        event_type: str,
        details: Dict[str, Any]
    ) -> None:
        """Log payment event with automatic retention."""
        try:
            log_data = {
                "checkout_request_id": checkout_request_id,
                "event_type": event_type,
                "details": details,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await execute_supabase_async(
                lambda: self.supabase.table(TABLE_PAYMENT_LOGS).insert(log_data).execute()
            )

            if secrets.randbelow(100) < 5:  # 5% chance, avoid running every call
                await self._cleanup_old_logs()

        except Exception as e:
            logger.warning(
                f"Failed to log payment event | checkout_request_id={mask_sensitive(checkout_request_id)} "
                f"event_type={event_type} error={e}"
            )

    async def _cleanup_old_logs(self) -> None:
        """Delete payment logs older than LOG_RETENTION_DAYS."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=LOG_RETENTION_DAYS)
            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_PAYMENT_LOGS).delete().lt("created_at", cutoff.isoformat()).execute()
            )
            if result.data:
                logger.info(f"Cleaned up old payment logs | count={len(result.data)}")
        except Exception as e:
            logger.warning(f"Failed to cleanup old logs | error={e}")

    async def _cleanup_old_replays(self) -> None:
        """fix #4: delete mpesa_callback_replays rows older than
        REPLAY_RETENTION_DAYS. This table only needs to be long enough to
        catch genuine duplicate deliveries (Safaricom retries within
        minutes/hours, not weeks), so 30 days is generous headroom."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=REPLAY_RETENTION_DAYS)
            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_CALLBACK_REPLAYS).delete().lt(
                    "processed_at", cutoff.isoformat()
                ).execute()
            )
            if result.data:
                logger.info(f"Cleaned up old callback replay records | count={len(result.data)}")
        except Exception as e:
            logger.warning(f"Failed to cleanup old replay records | error={e}")

    async def _create_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "info",
        reference_id: Optional[str] = None,
    ) -> None:
        """
        Create a notification for a user.

        fix #7: uses Supabase's upsert() instead of insert-then-catch-
        duplicate-key. Simpler, and it's one round trip instead of
        (sometimes) two.

        REQUIRES a unique constraint matching the on_conflict columns below.
        If your notifications table doesn't have one yet:

          ALTER TABLE notifications
          ADD CONSTRAINT notifications_user_reference_type_unique
          UNIQUE (user_id, reference_id, type);

        Adjust the columns/on_conflict to match whatever actually makes a
        notification "the same" in your schema — this assumes one
        notification per (user, reference_id, type) combo, e.g. one
        "service_unlocked" notification per user per checkout_request_id.
        """
        try:
            notification_data = {
                "user_id": user_id,
                "title": title,
                "message": message,
                "type": notification_type,
                "reference_id": reference_id,
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await execute_supabase_async(
                lambda: self.supabase.table(TABLE_NOTIFICATIONS).upsert(
                    notification_data, on_conflict="user_id,reference_id,type"
                ).execute()
            )
            logger.info(f"Notification created | user_id={user_id} title={title}")

        except Exception as e:
            logger.warning(f"Failed to create notification | user_id={user_id} error={e}")

    async def _get_payment_record(self, checkout_request_id: str) -> Optional[Dict[str, Any]]:
        """Get payment record from database."""
        try:
            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_PAYMENTS).select("*").eq(
                    "checkout_request_id", checkout_request_id
                ).maybe_single().execute()
            )
            return result.data
        except Exception as e:
            logger.error(
                f"Error getting payment record | checkout_request_id={
