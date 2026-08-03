# app/modules/mpesa/stk_push.py
# Auto-D Kenya - M-Pesa STK Push
# ================================================================
# TYPE: MODULE - M-Pesa STK Push logic

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

HTTP_TIMEOUT = 60.0
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
CALLBACK_SIGNATURE_TTL = 300
SERVICE_CACHE_TTL = 300
SERVICE_CACHE_MAXSIZE = 500
REPLAY_RETENTION_DAYS = 30

# Table names
TABLE_PAYMENTS = "payments"
TABLE_USER_SERVICES = "user_services"
TABLE_SERVICES = "services"
TABLE_PAYMENT_LOGS = "payment_logs"
TABLE_NOTIFICATIONS = "notifications"
TABLE_CALLBACK_REPLAYS = "mpesa_callback_replays"

# Safaricom constants
TRANSACTION_TYPE = "CustomerPayBillOnline"

# Retryable HTTP status codes
RETRYABLE_HTTP_STATUS = {429, 500, 502, 503, 504}


# ─── DATA CLASSES ──────────────────────────────────────────

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


# ─── HELPER FUNCTIONS ──────────────────────────────────────

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
    """Generate a meaningful account reference for support."""
    if service_name:
        prefix = service_name[:3].upper()
    elif user_id:
        prefix = user_id[:3].upper()
    else:
        prefix = "PAY"

    random_part = ''.join(secrets.choice(ACCOUNT_REFERENCE_ALPHABET) for _ in range(8))
    return f"{prefix}-{random_part}"


def _is_retryable_http_error(exc: BaseException) -> bool:
    """Check if an exception is retryable."""
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError, ConnectionError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_HTTP_STATUS
    return False


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

        self._client = None
        self._client_lock = asyncio.Lock()

        self._service_cache: TTLCache = TTLCache(maxsize=SERVICE_CACHE_MAXSIZE, ttl=SERVICE_CACHE_TTL)
        self._service_active_column: Optional[str] = None
        self._service_column_lock = asyncio.Lock()

        self._callback_cache: Dict[str, datetime] = {}
        self._cache_lock = asyncio.Lock()

        self._background_tasks: set = set()

        self._validate_configuration()
        self._log_configuration()

    # ─── CONFIGURATION ──────────────────────────────────────

    def _validate_configuration(self) -> None:
        """Validate M-Pesa configuration at startup."""
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

        if not self.callback_secret:
            logger.warning("MPESA_CALLBACK_SECRET not configured.")

        if errors:
            raise AppException(f"M-Pesa configuration incomplete: {', '.join(errors)}", 500)

    def _log_configuration(self) -> None:
        """Log M-Pesa configuration."""
        callback_host = self.callback_url.split("/")[2] if "://" in self.callback_url else "unset"
        logger.info(
            f"M-Pesa configuration loaded | environment={settings.MPESA_ENVIRONMENT} "
            f"base_url={self.base_url} shortcode={self.shortcode} callback_host={callback_host}"
        )

    def _get_expiry_date(self, expiry_days: Optional[int] = None) -> str:
        """Get expiry date for service access."""
        days = expiry_days if expiry_days and expiry_days > 0 else DEFAULT_EXPIRY_DAYS
        return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

    def _spawn_background(self, coro) -> asyncio.Task:
        """Run a coroutine as a background task."""
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

    # ─── HEALTH CHECK ──────────────────────────────────────

    async def health_check(self) -> bool:
        """Simple health check for OAuth token."""
        try:
            await self._get_access_token()
            return True
        except Exception:
            return False

    # ─── HTTP CLIENT ────────────────────────────────────────

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
                    ),
                    http2=True,
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

    # ─── TOKEN MANAGEMENT ──────────────────────────────────

    def _token_is_fresh(self) -> bool:
        if not (self.access_token and self.token_expiry):
            return False
        buffer_time = timedelta(seconds=ACCESS_TOKEN_EXPIRY_OFFSET)
        return datetime.now(timezone.utc) < (self.token_expiry - buffer_time)

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_random_exponential(multiplier=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),
        retry=retry_if_exception(_is_retryable_http_error),
        reraise=True
    )
    async def _get_access_token(self) -> str:
        """Get OAuth access token with double-checked locking."""
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

    # ─── RETRYABLE HTTP POST ──────────────────────────────

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_random_exponential(multiplier=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),
        retry=retry_if_exception(_is_retryable_http_error),
        reraise=True
    )
    async def _post_with_retry(self, url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> httpx.Response:
        """Make a POST request with retry logic."""
        client = await self._get_client()
        response = await client.post(url, headers=headers, json=payload)

        if response.status_code == 401:
            logger.warning("Got 401 from Safaricom mid-request — refreshing token and retrying once")
            self.clear_token_cache()
            new_token = await self._get_access_token()
            headers = dict(headers)
            headers["Authorization"] = f"Bearer {new_token}"
            response = await client.post(url, headers=headers, json=payload)

        response.raise_for_status()
        return response

    # ─── SERVICE CACHE ─────────────────────────────────────

    async def _get_cached_service(self, service_id: int) -> Optional[Dict[str, Any]]:
        """Get service from cache or database."""
        cached = self._service_cache.get(service_id)
        if cached is not None:
            return cached

        try:
            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_SERVICES).select("*").eq("id", service_id).maybe_single().execute()
            )
            if result and result.data:
                self._service_cache[service_id] = result.data
                return result.data
        except Exception as e:
            logger.error(f"Error fetching service | service_id={service_id} error={e}")

        return None

    # ─── REPLAY PROTECTION ─────────────────────────────────

    async def _is_replay(self, checkout_request_id: str) -> bool:
        """Check if a callback has already been processed."""
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
            if secrets.randbelow(100) < 5:
                self._spawn_background(self._cleanup_old_replays())
            return False
        except Exception as e:
            if "duplicate key" in str(e).lower() or "23505" in str(e):
                return True
            logger.warning(
                f"Replay-protection DB check failed | "
                f"checkout_request_id={mask_sensitive(checkout_request_id)} error={e}"
            )
            return False

    # ─── DATABASE HELPERS ──────────────────────────────────

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

            if secrets.randbelow(100) < 5:
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
            if result and result.data:
                logger.info(f"Cleaned up old payment logs | count={len(result.data)}")
        except Exception as e:
            logger.warning(f"Failed to cleanup old logs | error={e}")

    async def _cleanup_old_replays(self) -> None:
        """Delete old callback replay records."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=REPLAY_RETENTION_DAYS)
            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_CALLBACK_REPLAYS).delete().lt(
                    "processed_at", cutoff.isoformat()
                ).execute()
            )
            if result and result.data:
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
        """Create a notification for a user."""
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
            return result.data if result and result.data else None
        except Exception as e:
            logger.error(f"Error getting payment record | error={e}")
            return None

    async def _update_payment_status(
        self,
        checkout_request_id: str,
        result_code: str,
        result_desc: str,
        data: Dict[str, Any],
        callback_amount: Optional[float] = None,
        mpesa_receipt: Optional[str] = None,
        phone: Optional[str] = None,
        transaction_date: Optional[str] = None,
        callback_payload: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """Update payment record with full callback data."""
        try:
            current = await self._get_payment_record(checkout_request_id)
            if not current:
                return None

            if current and PaymentStatus(current.get("status", PaymentStatus.UNKNOWN.value)).is_terminal:
                logger.info(f"Skipping status update — payment already terminal | {checkout_request_id}")
                return current

            status = self._map_result_code_to_status(result_code)
            now = datetime.now(timezone.utc).isoformat()

            update_data = {
                "status": status.value,
                "result_code": str(result_code),
                "result_desc": result_desc,
                "updated_at": now
            }

            if str(result_code) == "0":
                update_data["mpesa_receipt"] = mpesa_receipt or data.get("MpesaReceiptNumber")
                update_data["transaction_id"] = checkout_request_id
                update_data["completed_at"] = now
                if callback_amount is not None:
                    update_data["paid_amount"] = callback_amount
                if phone:
                    update_data["paid_phone"] = phone
                if transaction_date:
                    update_data["transaction_date"] = transaction_date
                if callback_payload:
                    update_data["callback_payload"] = callback_payload

            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_PAYMENTS).update(update_data).eq(
                    "checkout_request_id", checkout_request_id
                ).execute()
            )

            self._spawn_background(self._log_payment_event(
                checkout_request_id, "status_update", {
                    "status": status.value,
                    "result_code": result_code
                }
            ))

            return result.data[0] if result and result.data else None

        except Exception as e:
            logger.error(f"Error updating payment status | error={e}")
            return None

    async def _upsert_user_service(
        self,
        user_id: str,
        service_id: int,
        payment_id: int,
        expiry_days: Optional[int] = None,
        mpesa_receipt: Optional[str] = None,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Atomic upsert user service record."""
        now = datetime.now(timezone.utc).isoformat()
        expires_at = self._get_expiry_date(expiry_days)

        row = {
            "user_id": user_id,
            "service_id": service_id,
            "payment_id": payment_id,
            "status": ServiceStatus.ACTIVE.value,
            "expires_at": expires_at,
            "mpesa_receipt": mpesa_receipt,
            "transaction_id": transaction_id,
            "updated_at": now,
        }

        try:
            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_USER_SERVICES).upsert(
                    row, on_conflict="user_id,service_id"
                ).execute()
            )
            if result and result.data:
                return result.data[0]
            return row

        except Exception as e:
            logger.error(f"Error upserting user service | error={e}")
            raise

    async def _atomic_unlock_transaction(
        self,
        checkout_request_id: str,
        mpesa_receipt: Optional[str] = None,
        callback_amount: Optional[float] = None
    ) -> Tuple[bool, str]:
        """Atomically mark the payment unlocked AND grant user_services access."""
        try:
            payment = await self._get_payment_record(checkout_request_id)
            if not payment:
                return False, "Payment record not found"

            if payment.get("unlock_status") == UnlockStatus.COMPLETED.value:
                return True, "Service already unlocked"

            user_id = payment.get("user_id")
            service_id = payment.get("service_id")
            payment_id = payment.get("id")
            expected_amount = payment.get("amount")

            if callback_amount is not None:
                if callback_amount <= 0:
                    return False, f"Invalid callback amount: {callback_amount}"
                if expected_amount and abs(float(callback_amount) - float(expected_amount)) > 0.01:
                    return False, f"Amount mismatch: expected {expected_amount}, got {callback_amount}"

            if not user_id or not service_id:
                return False, f"Missing user_id or service_id: {checkout_request_id}"

            service = await self._get_cached_service(service_id)
            expiry_days = service.get("expiry_days") if service else None

            now = datetime.now(timezone.utc).isoformat()
            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_PAYMENTS).update({
                    "unlock_status": UnlockStatus.COMPLETED.value,
                    "unlocked_at": now,
                }).eq("id", payment_id).eq("unlock_status", UnlockStatus.PENDING.value).execute()
            )

            if not result or not result.data:
                return True, "Service already unlocked (concurrent)"

            await self._upsert_user_service(
                user_id=user_id,
                service_id=service_id,
                payment_id=payment_id,
                expiry_days=expiry_days,
                mpesa_receipt=mpesa_receipt,
                transaction_id=checkout_request_id
            )

            service_name = service.get("name", "Service") if service else "Service"

            self._spawn_background(self._create_notification(
                user_id=user_id,
                title=f"🎉 {service_name} Unlocked!",
                message=f"Your {service_name} has been successfully unlocked.",
                notification_type="service_unlocked",
                reference_id=checkout_request_id,
            ))

            self._spawn_background(self._log_payment_event(
                checkout_request_id,
                "service_unlocked",
                {"user_id": user_id, "service_id": service_id, "mpesa_receipt": mpesa_receipt}
            ))

            logger.info(f"Service unlocked | service_id={service_id} user_id={user_id}")
            return True, "Service unlocked successfully"

        except Exception as e:
            logger.error(f"Error unlocking service | error={e}")
            return False, str(e)

    async def _create_payment_record(
        self,
        checkout_request_id: str,
        merchant_request_id: str,
        amount: float,
        phone: str,
        user_id: Optional[str],
        service_id: Optional[int],
        description: str,
        response_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a payment record."""
        try:
            existing = await self._get_payment_record(checkout_request_id)
            if existing:
                return existing

            if service_id:
                service = await self._get_cached_service(service_id)
                if not service:
                    raise NotFoundException(f"Service {service_id} not found")

            now = datetime.now(timezone.utc).isoformat()
            payment_data = {
                "checkout_request_id": checkout_request_id,
                "merchant_request_id": merchant_request_id,
                "amount": amount,
                "phone": phone,
                "user_id": user_id,
                "service_id": service_id,
                "description": description[:DESCRIPTION_MAX_LENGTH],
                "status": PaymentStatus.PENDING.value,
                "unlock_status": UnlockStatus.PENDING.value,
                "created_at": now,
                "updated_at": now,
            }

            if response_data:
                payment_data["response_code"] = response_data.get("ResponseCode")
                payment_data["response_description"] = response_data.get("ResponseDescription")
                payment_data["customer_message"] = response_data.get("CustomerMessage")

            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_PAYMENTS).insert(payment_data).execute()
            )

            return result.data[0] if result and result.data else payment_data

        except Exception as e:
            logger.error(f"Failed to create payment record | error={e}")
            raise

    async def _get_service_active_column(self) -> str:
        """Detect whether the services table uses 'active' or 'is_active'."""
        if self._service_active_column:
            return self._service_active_column

        async with self._service_column_lock:
            if self._service_active_column:
                return self._service_active_column

            try:
                result = await execute_supabase_async(
                    lambda: self.supabase.table(TABLE_SERVICES).select("*").limit(1).execute()
                )
                if result and result.data:
                    columns = result.data[0].keys()
                    if "is_active" in columns:
                        self._service_active_column = "is_active"
                    elif "active" in columns:
                        self._service_active_column = "active"
                    else:
                        self._service_active_column = "active"
                else:
                    self._service_active_column = "active"
            except Exception as e:
                logger.warning(f"Could not detect services active-column | error={e}")
                self._service_active_column = "active"

            return self._service_active_column

    def _map_result_code_to_status(self, result_code) -> PaymentStatus:
        """Map Safaricom result code to PaymentStatus."""
        try:
            code = int(result_code)
        except (TypeError, ValueError):
            return PaymentStatus.UNKNOWN

        if code == 0:
            return PaymentStatus.COMPLETED
        elif code in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
            return PaymentStatus.FAILED
        elif code in [17, 18, 19, 20, 21]:
            return PaymentStatus.CANCELLED
        else:
            return PaymentStatus.UNKNOWN

    # ─── STK PUSH ──────────────────────────────────────────

    async def initiate_push(
        self,
        phone: str,
        amount: float,
        description: str,
        checkout_request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        service_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Initiate STK Push payment."""
        try:
            normalized_phone = normalize_phone(phone)

            if amount <= 0:
                raise ValidationException("Amount must be greater than zero")
            if amount < MINIMUM_AMOUNT:
                raise ValidationException(f"Amount must be at least {MINIMUM_AMOUNT}")

            service_name = None
            if service_id:
                service = await self._get_cached_service(service_id)
                if not service:
                    raise NotFoundException(f"Service {service_id} not found")
                service_name = service.get("name", "Service")

            rounded_amount = math.ceil(amount)

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            password = self._generate_password(timestamp)

            account_reference = generate_account_reference(service_name, user_id)

            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": TRANSACTION_TYPE,
                "Amount": str(rounded_amount),
                "PartyA": normalized_phone,
                "PartyB": self.shortcode,
                "PhoneNumber": normalized_phone,
                "CallBackURL": self.callback_url,
                "AccountReference": account_reference,
                "TransactionDesc": description[:DESCRIPTION_MAX_LENGTH]
            }

            logger.info(f"Initiating STK Push | phone={mask_sensitive(normalized_phone)} amount={rounded_amount}")

            token = await self._get_access_token()

            response = await self._post_with_retry(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                payload
            )

            data = response.json()

            if "ResponseCode" not in data:
                raise AppException("Invalid response from Safaricom - missing ResponseCode", 502)

            response_code = data.get("ResponseCode")
            response_description = data.get("ResponseDescription", "Unknown error")

            if response_code != "0":
                raise AppException(f"STK push failed: {response_description}", 400)

            merchant_request_id = data.get("MerchantRequestID")
            checkout_id = data.get("CheckoutRequestID")
            customer_message = data.get("CustomerMessage", "STK Push sent successfully")

            if not checkout_id:
                raise AppException("Missing CheckoutRequestID from Safaricom", 502)

            if not merchant_request_id:
                raise AppException("Missing MerchantRequestID from Safaricom", 502)

            payment = await self._create_payment_record(
                checkout_request_id=checkout_id,
                merchant_request_id=merchant_request_id,
                amount=rounded_amount,
                phone=normalized_phone,
                user_id=user_id,
                service_id=service_id,
                description=description,
                response_data=data
            )

            logger.info(f"STK Push successful | checkout_id={mask_sensitive(checkout_id)}")

            return {
                "checkout_request_id": checkout_id,
                "merchant_request_id": merchant_request_id,
                "customer_message": customer_message,
                "status": "pending",
                "response_code": response_code,
                "response_description": response_description
            }

        except (ValidationException, NotFoundException, AppException):
            raise
        except httpx.HTTPStatusError as e:
            logger.exception(f"HTTP error during STK Push: {e}")
            raise AppException(f"STK Push HTTP error: {str(e)}", e.response.status_code if e.response else 503)
        except httpx.TimeoutException as e:
            logger.exception(f"Timeout during STK Push: {e}")
            raise AppException("STK Push timed out - please try again", 504)
        except httpx.TransportError as e:
            logger.exception(f"Transport error during STK Push: {e}")
            raise AppException("Network error - please try again", 503)
        except Exception as e:
            logger.exception(f"Unexpected error during STK Push: {e}")
            raise AppException(f"STK Push failed: {str(e)}", 500)

    # ─── CALLBACK PROCESSING ──────────────────────────────

    async def process_callback(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process M-Pesa callback with full payment update and unlock.
        """
        try:
            body = callback_data.get("Body", {})
            stk_callback = body.get("stkCallback", {})

            if not stk_callback:
                logger.error("Invalid callback structure")
                return {"status": "error", "message": "Invalid callback structure"}

            checkout_request_id = stk_callback.get("CheckoutRequestID")
            merchant_request_id = stk_callback.get("MerchantRequestID")
            result_code = stk_callback.get("ResultCode")
            result_desc = stk_callback.get("ResultDesc", "")

            if not checkout_request_id:
                logger.error("Callback missing CheckoutRequestID")
                return {"status": "error", "message": "Missing CheckoutRequestID"}

            # Replay protection
            if await self._is_replay(checkout_request_id):
                logger.warning(f"Replay detected — duplicate callback | {checkout_request_id}")
                return {
                    "status": "replay_detected",
                    "message": "Callback already processed",
                    "checkout_request_id": checkout_request_id
                }

            # Get payment
            payment = await self._get_payment_record(checkout_request_id)
            if not payment:
                logger.warning(f"Payment not found for callback: {checkout_request_id}")
                return {"status": "ignored", "message": "Payment record not found"}

            # Verify merchant request ID
            if payment.get("merchant_request_id") != merchant_request_id:
                logger.error(f"MerchantRequestID mismatch | expected={payment.get('merchant_request_id')} received={merchant_request_id}")
                return {"status": "error", "message": "MerchantRequestID mismatch"}

            # Check if already processed
            current_status = PaymentStatus(payment.get("status", PaymentStatus.UNKNOWN.value))
            if current_status.is_terminal:
                logger.info(f"Callback already processed | {checkout_request_id} status={current_status.value}")
                return {
                    "status": "already_processed",
                    "checkout_request_id": checkout_request_id,
                    "message": "Payment already processed"
                }

            # Extract callback metadata
            callback_amount = None
            mpesa_receipt = None
            transaction_date = None
            phone = None

            callback_metadata = stk_callback.get("CallbackMetadata")
            if callback_metadata:
                items = callback_metadata.get("Item", [])
                for item in items:
                    name = item.get("Name")
                    value = item.get("Value")
                    if name == "Amount":
                        callback_amount = float(value) if value else None
                    elif name == "MpesaReceiptNumber":
                        mpesa_receipt = value
                    elif name == "TransactionDate":
                        transaction_date = value
                    elif name == "PhoneNumber":
                        phone = value

            # Validate callback amount
            if callback_amount is not None:
                if callback_amount <= 0:
                    logger.error(f"Invalid callback amount | {callback_amount}")
                    return {
                        "status": "failed",
                        "checkout_request_id": checkout_request_id,
                        "message": f"Invalid callback amount: {callback_amount}"
                    }

                expected_amount = float(payment.get("amount", 0))
                if abs(callback_amount - expected_amount) > 0.01:
                    logger.error(f"Amount mismatch | expected={expected_amount} received={callback_amount}")
                    return {
                        "status": "failed",
                        "checkout_request_id": checkout_request_id,
                        "message": f"Amount mismatch: expected {expected_amount}, got {callback_amount}"
                    }

            # Update payment status
            updated_payment = await self._update_payment_status(
                checkout_request_id=checkout_request_id,
                result_code=str(result_code),
                result_desc=result_desc,
                data=stk_callback,
                callback_amount=callback_amount,
                mpesa_receipt=mpesa_receipt,
                phone=phone,
                transaction_date=transaction_date,
                callback_payload=callback_data
            )

            # Unlock service on success
            unlock_success = False
            unlock_message = ""

            if str(result_code) == "0" and updated_payment:
                unlock_success, unlock_message = await self._atomic_unlock_transaction(
                    checkout_request_id=checkout_request_id,
                    mpesa_receipt=mpesa_receipt,
                    callback_amount=callback_amount
                )

            if str(result_code) == "0" and unlock_success:
                logger.info(f"✅ Payment completed and service unlocked | {checkout_request_id}")
                return {
                    "status": "success",
                    "checkout_request_id": checkout_request_id,
                    "mpesa_receipt": mpesa_receipt,
                    "amount": callback_amount,
                    "message": "Payment confirmed and service unlocked"
                }
            elif str(result_code) == "0" and not unlock_success:
                logger.error(f"Payment completed but unlock failed | {checkout_request_id} | {unlock_message}")
                return {
                    "status": "partial",
                    "checkout_request_id": checkout_request_id,
                    "mpesa_receipt": mpesa_receipt,
                    "message": f"Payment received but service unlock failed: {unlock_message}"
                }
            else:
                logger.warning(f"Callback failed | result_code={result_code} | {checkout_request_id}")
                return {
                    "status": "failed",
                    "checkout_request_id": checkout_request_id,
                    "result_code": result_code,
                    "result_desc": result_desc,
                    "message": "Payment failed"
                }

        except Exception as e:
            logger.exception(f"Error processing callback: {e}")
            return {"status": "error", "message": str(e)}

    # ─── HELPERS ─────────────────────────────────────────────

    def _generate_password(self, timestamp: str) -> str:
        """Generate password for STK push."""
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(password_str.encode()).decode()

    # ─── STALE PAYMENT CLEANUP ──────────────────────────────

    async def cleanup_stale_payments(self) -> int:
        """Mark stale pending payments as expired."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=STALE_PAYMENT_HOURS)
            cutoff_str = cutoff.isoformat()

            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_PAYMENTS).update({
                    "status": PaymentStatus.EXPIRED.value,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("status", PaymentStatus.PENDING.value).lt("created_at", cutoff_str).execute()
            )

            count = len(result.data) if result and result.data else 0
            if count > 0:
                logger.info(f"Cleaned up stale payments | count={count}")

            return count

        except Exception as e:
            logger.error(f"Error cleaning up stale payments | error={e}")
            return 0
