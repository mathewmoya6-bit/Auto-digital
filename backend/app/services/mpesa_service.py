"""
Auto-D Kenya
M-Pesa Business Logic - Enterprise Grade v7 (Production Ready)
FIXED: Uses existing 'payments' and 'service_access' tables
FIXED: Uses 'services' table for service data
FIXED: Proper column mappings for all tables
"""

import base64
import json
import logging
import asyncio
import httpx
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any, List
from enum import Enum
from decimal import Decimal, getcontext, ROUND_HALF_UP
from concurrent.futures import ThreadPoolExecutor
import uuid

from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.core.config import settings
from app.core.database import supabase

# ─── Decimal precision for money ───
getcontext().prec = 28

logger = logging.getLogger(__name__)

# ─── Thread pool for synchronous DB operations ───
_db_executor = ThreadPoolExecutor(max_workers=10)


# ============================================================
# ENUMS
# ============================================================

class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"
    PARTIAL_REFUND = "partial_refund"
    PROCESSING = "processing"


class ServiceAccessStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


# ============================================================
# PYDANTIC MODELS
# ============================================================

class STKPushRequest(BaseModel):
    """STK Push request model."""
    model_config = ConfigDict(use_enum_values=True)

    phone: str = Field(..., description="Phone number (e.g., 0712345678)")
    service_id: str = Field(..., max_length=50, description="Service ID or code")
    description: Optional[str] = Field(None, max_length=36, description="Transaction description")
    user_id: Optional[str] = Field(None, description="User ID for the payment")
    corporate_id: Optional[str] = Field(None, description="Corporate customer ID for discounts")
    request_id: Optional[str] = Field(
        None,
        description="Optional id of the row in the 'requests' table this payment fulfills. "
                     "When provided, the backend will mark that request 'paid' once the "
                     "M-Pesa callback (or manual confirm) succeeds — this is the ONLY "
                     "code path allowed to write that status; the frontend must never do it."
    )

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = ''.join(filter(str.isdigit, v))
        if cleaned.startswith('0'):
            cleaned = cleaned[1:]
        if cleaned.startswith('254'):
            cleaned = cleaned[3:]
        if len(cleaned) != 9:
            raise ValueError(f"Phone must be 9 digits after formatting")
        valid_prefixes = ('7', '11')
        if not any(cleaned.startswith(p) for p in valid_prefixes):
            raise ValueError(f"Invalid Safaricom prefix: {cleaned[:2]}")
        return f"254{cleaned}"

    @field_validator('service_id')
    @classmethod
    def validate_service_id(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        # FIX: Safaricom hard-rejects TransactionDesc > 36 chars; truncate here too,
        # not just at the point of building the Safaricom payload, so the value we
        # persist to the payments table always matches what Safaricom actually saw.
        if v is None:
            return v
        v = v.strip()
        return v[:36] if len(v) > 36 else v


# ============================================================
# SERVICE REPOSITORY
# ============================================================

class ServiceRepository:
    """Service database operations using the 'services' table."""

    def __init__(self):
        self._cache = {}
        self._last_refresh = None
        self._cache_duration = timedelta(minutes=5)

    async def _run_sync(self, operation):
        """Run a synchronous database operation in a thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_db_executor, operation)

    async def get_by_code(self, code: str, include_inactive: bool = False) -> Optional[Dict]:
        """Get service by code from services table."""
        try:
            code = code.strip().lower()
            logger.info(f"Looking for service: {code}")

            query = supabase.table("services").select("*").eq("code", code)
            
            if not include_inactive:
                query = query.eq("active", True)

            response = await self._run_sync(
                lambda: query.limit(1).execute()
            )

            if not response.data:
                logger.error(f"Service {code} NOT FOUND")
                return None

            row = response.data[0]
            logger.info(f"Found service: {row.get('code')} | active={row.get('active')} | price={row.get('price')}")

            return {
                "id": row.get("id"),
                "code": row.get("code"),
                "name": row.get("name"),
                "price": Decimal(str(row.get("price", 0))),
                "base_price": Decimal(str(row.get("price", 0))),
                "currency": row.get("currency", "KES"),
                "description": row.get("description", ""),
                "service_fee": Decimal(str(row.get("service_fee", 0))),
                "vat_rate": Decimal("0"),
                "discount_value": Decimal("0"),
                "discount_type": None,
                "active": row.get("active", True),
                "is_active": row.get("active", True),
                "version": row.get("version", 1),
                "display_order": row.get("display_order", 0),
            }

        except Exception as e:
            logger.exception(f"Get service error: {code}")
            return None

    async def get_all(self, include_inactive: bool = False) -> List[Dict]:
        """Get all services from services table."""
        try:
            query = supabase.table("services").select("*")

            if not include_inactive:
                query = query.eq("active", True)

            response = await self._run_sync(
                lambda: query.order("display_order").execute()
            )

            services = []
            for row in (response.data or []):
                services.append({
                    "id": row.get("id"),
                    "code": row.get("code"),
                    "name": row.get("name"),
                    "price": Decimal(str(row.get("price", 0))),
                    "base_price": Decimal(str(row.get("price", 0))),
                    "currency": row.get("currency", "KES"),
                    "description": row.get("description", ""),
                    "service_fee": Decimal(str(row.get("service_fee", 0))),
                    "vat_rate": Decimal("0"),
                    "discount_value": Decimal("0"),
                    "discount_type": None,
                    "active": row.get("active", True),
                    "is_active": row.get("active", True),
                    "version": row.get("version", 1),
                    "display_order": row.get("display_order", 0),
                })

            logger.info(f"[ServiceRepository] Loaded {len(services)} services")
            return services

        except Exception as e:
            logger.exception("Get all services error")
            return []

    async def get_service_with_price(self, code: str) -> Optional[Dict]:
        """Get service with price validation."""
        service = await self.get_by_code(code)

        if not service:
            return None

        if Decimal(str(service["price"])) <= 0:
            logger.error(f"Invalid price for {code}: {service['price']}")
            return None

        return service

    async def create(self, data: Dict) -> Optional[Dict]:
        """Create a new service (admin only)."""
        try:
            data['id'] = str(uuid.uuid4())
            data['created_at'] = datetime.now(UTC).isoformat()
            data['updated_at'] = datetime.now(UTC).isoformat()

            response = await self._run_sync(
                lambda: supabase.table("services").insert(data).execute()
            )
            return response.data[0] if response.data else None

        except Exception as e:
            logger.exception("Create service error")
            return None

    async def update(self, service_id: str, data: Dict) -> Optional[Dict]:
        """Update a service (admin only)."""
        try:
            data['updated_at'] = datetime.now(UTC).isoformat()

            response = await self._run_sync(
                lambda: supabase.table("services")
                .update(data)
                .eq("id", service_id)
                .execute()
            )
            return response.data[0] if response.data else None

        except Exception as e:
            logger.exception("Update service error")
            return None

    async def soft_delete(self, service_id: str, deleted_by: str) -> bool:
        """Soft delete a service (admin only)."""
        try:
            data = {
                "active": False,
                "deleted_at": datetime.now(UTC).isoformat(),
                "deleted_by": deleted_by
            }
            response = await self._run_sync(
                lambda: supabase.table("services")
                .update(data)
                .eq("id", service_id)
                .execute()
            )
            return bool(response.data)

        except Exception as e:
            logger.exception("Soft delete service error")
            return False

    async def restore(self, service_id: str) -> bool:
        """Restore a soft-deleted service (admin only)."""
        try:
            data = {
                "active": True,
                "deleted_at": None,
                "deleted_by": None
            }
            response = await self._run_sync(
                lambda: supabase.table("services")
                .update(data)
                .eq("id", service_id)
                .execute()
            )
            return bool(response.data)

        except Exception as e:
            logger.exception("Restore service error")
            return False


# ============================================================
# PAYMENT REPOSITORY - Uses 'payments' table
# ============================================================

class PaymentRepository:
    """Payment database operations using the 'payments' table."""

    async def _run_sync(self, operation):
        """Run a synchronous database operation in a thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_db_executor, operation)

    async def create(self, data: Dict) -> Optional[Dict]:
        """Create a payment record - BACKEND ONLY."""
        try:
            logger.info(f"📝 Creating payment: {json.dumps(data, default=str)}")
            
            if 'id' not in data or not data['id']:
                data['id'] = str(uuid.uuid4())
            
            data['created_at'] = datetime.now(UTC).isoformat()
            data['updated_at'] = datetime.now(UTC).isoformat()

            response = await self._run_sync(
                lambda: supabase.table("payments").insert(data).execute()
            )
            
            logger.info(f"📥 Insert response: {response.data}")
            
            if response.data:
                logger.info(f"✅ Payment created: {response.data[0].get('id')}")
                return response.data[0]
            
            logger.error("❌ No data returned from insert")
            return None

        except Exception as e:
            logger.exception(f"❌ Create payment error: {e}")
            return None

    async def get_by_checkout_id(self, checkout_id: str) -> Optional[Dict]:
        """Get payment by checkout request ID."""
        try:
            logger.info(f"🔍 Looking up payment: {checkout_id}")
            
            response = await self._run_sync(
                lambda: supabase.table("payments")
                .select("*")
                .eq("checkout_request_id", checkout_id)
                .limit(1)
                .execute()
            )
            
            if response.data and len(response.data) > 0:
                logger.info(f"✅ Payment found: {response.data[0].get('status')}")
                return response.data[0]
            
            logger.warning(f"❌ No payment found for: {checkout_id}")
            return None

        except Exception as e:
            logger.exception(f"Get payment error: {checkout_id}")
            return None

    async def update_with_optimistic_lock(
        self,
        checkout_id: str,
        data: Dict,
        expected_status: str = "pending"
    ) -> Optional[Dict]:
        """Update payment with optimistic locking."""
        try:
            data['updated_at'] = datetime.now(UTC).isoformat()

            response = await self._run_sync(
                lambda: supabase.table("payments")
                .update(data)
                .eq("checkout_request_id", checkout_id)
                .eq("status", expected_status)
                .execute()
            )

            if response.data:
                logger.info(f"✅ Payment updated: {checkout_id}")
                return response.data[0]

            logger.warning(f"Optimistic lock failed for {checkout_id}")
            return None

        except Exception as e:
            logger.exception(f"Update payment error: {checkout_id}")
            return None

    async def get_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get payment history for a user."""
        try:
            response = await self._run_sync(
                lambda: supabase.table("payments")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []

        except Exception as e:
            logger.exception("Get history error")
            return []

    async def get_service_access(self, user_id: str, service_id: str) -> Optional[Dict]:
        """Get service access record."""
        try:
            response = await self._run_sync(
                lambda: supabase.table("service_access")
                .select("*")
                .eq("user_id", user_id)
                .eq("service_id", service_id)
                .eq("status", "active")
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None

        except Exception as e:
            logger.exception("Get service access error")
            return None

    async def create_service_access(self, data: Dict) -> Optional[Dict]:
        """Create service access record."""
        try:
            data['id'] = str(uuid.uuid4())
            data['created_at'] = datetime.now(UTC).isoformat()

            response = await self._run_sync(
                lambda: supabase.table("service_access").insert(data).execute()
            )
            return response.data[0] if response.data else None

        except Exception as e:
            logger.exception("Create service access error")
            return None

    async def get_user_services(self, user_id: str) -> List[Dict]:
        """Get all active services for a user."""
        try:
            response = await self._run_sync(
                lambda: supabase.table("service_access")
                .select("*")
                .eq("user_id", user_id)
                .eq("status", "active")
                .execute()
            )
            return response.data or []

        except Exception as e:
            logger.exception("Get user services error")
            return []

    async def create_notification(self, data: Dict) -> bool:
        """Create a notification."""
        try:
            data['id'] = str(uuid.uuid4())
            data['created_at'] = datetime.now(UTC).isoformat()

            await self._run_sync(
                lambda: supabase.table("notifications").insert(data).execute()
            )
            return True

        except Exception as e:
            logger.exception("Notification error")
            return False

    async def create_audit_log(self, data: Dict) -> bool:
        """Create audit log."""
        try:
            data['created_at'] = datetime.now(UTC).isoformat()

            await self._run_sync(
                lambda: supabase.table("payment_audit_log").insert(data).execute()
            )
            return True

        except Exception as e:
            logger.exception("Audit log error")
            return False

    async def create_price_history(self, data: Dict) -> bool:
        """Create price history record."""
        try:
            data['created_at'] = datetime.now(UTC).isoformat()

            await self._run_sync(
                lambda: supabase.table("service_price_history").insert(data).execute()
            )
            return True

        except Exception as e:
            logger.exception("Price history error")
            return False

    async def create_failed_event(self, event_type: str, payload: Dict, error: str) -> bool:
        """Create failed event for dead-letter queue."""
        try:
            data = {
                "event_type": event_type,
                "payload": payload,
                "error": error,
                "retry_count": 0,
                "created_at": datetime.now(UTC).isoformat()
            }

            await self._run_sync(
                lambda: supabase.table("failed_events").insert(data).execute()
            )
            return True

        except Exception as e:
            logger.exception("Failed event error")
            return False

    async def expire_stale_payments(self, minutes: int = 30) -> int:
        """Expire stale pending payments."""
        try:
            cutoff = (datetime.now(UTC) - timedelta(minutes=minutes)).isoformat()

            response = await self._run_sync(
                lambda: supabase.table("payments")
                .update({
                    "status": PaymentStatus.FAILED.value,
                    "updated_at": datetime.now(UTC).isoformat(),
                    "result_desc": "Payment expired - no callback received"
                })
                .eq("status", PaymentStatus.PENDING.value)
                .lt("created_at", cutoff)
                .execute()
            )

            return len(response.data) if response.data else 0

        except Exception as e:
            logger.exception("Expire stale payments error")
            return 0

    async def get_by_id_for_user(self, request_id: str, user_id: str) -> Optional[Dict]:
        """FIX: fetch a requests row scoped to the owning user, used to validate
        that a request_id passed into /mpesa/stkpush actually belongs to the
        caller before we trust it (defense in depth against IDOR)."""
        try:
            response = await self._run_sync(
                lambda: supabase.table("requests")
                .select("*")
                .eq("id", request_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.exception(f"Get request by id error: {request_id}")
            return None

    async def update_request_status(self, request_id: str, status: str) -> bool:
        """
        FIX: Server-side (service-role client, bypasses RLS) update of the
        'requests' table status. This is intentionally the ONLY place in the
        whole system allowed to move a request to 'paid'/'completed' — the
        dashboard frontend must never write that field itself, since a
        client with only the anon key could otherwise forge a 'paid' status
        even if RLS on other columns is correctly locked down.
        """
        try:
            if not request_id:
                return False

            response = await self._run_sync(
                lambda: supabase.table("requests")
                .update({
                    "status": status,
                    "updated_at": datetime.now(UTC).isoformat()
                })
                .eq("id", request_id)
                .execute()
            )
            ok = bool(response.data)
            if ok:
                logger.info(f"✅ Request {request_id} marked '{status}'")
            else:
                logger.warning(f"⚠️ Could not update request {request_id} to '{status}' (not found?)")
            return ok

        except Exception as e:
            logger.exception(f"Update request status error: {request_id}")
            return False


# ============================================================
# AUTH SERVICE
# ============================================================

class MpesaAuthService:
    """Handles M-Pesa authentication with token caching."""

    def __init__(self):
        self.environment = settings.MPESA_ENV
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.base_url = "https://api.safaricom.co.ke" if self.environment == "production" else "https://sandbox.safaricom.co.ke"

        self.token_cache_minutes = getattr(settings, "TOKEN_CACHE_MINUTES", 50)
        self.timeout = getattr(settings, "MPESA_TIMEOUT", 10)

        self._cached_token = None
        self._token_expiry = None
        self._token_lock = asyncio.Lock()

    async def get_access_token(self) -> Optional[str]:
        """Get access token with caching."""
        async with self._token_lock:
            if self._cached_token and self._token_expiry:
                if datetime.now(UTC) < self._token_expiry:
                    logger.debug("Using cached token")
                    return self._cached_token

            logger.info("Refreshing access token")

            try:
                auth = base64.b64encode(
                    f"{self.consumer_key}:{self.consumer_secret}".encode()
                ).decode()

                headers = {"Authorization": f"Basic {auth}"}
                url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"

                async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()

                    data = response.json()
                    token = data.get("access_token")

                    if token:
                        self._cached_token = token
                        self._token_expiry = datetime.now(UTC) + timedelta(minutes=self.token_cache_minutes)
                        logger.info("Token cached")
                        return token
                    else:
                        logger.error("No token in response")
                        return None

            except Exception as e:
                logger.exception("Token error")
                return None


# ============================================================
# STK SERVICE
# ============================================================

class MpesaSTKService:
    """Handles STK Push operations."""

    def __init__(self, auth_service: MpesaAuthService):
        self.auth_service = auth_service

        self.environment = settings.MPESA_ENV
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.callback_url = f"{settings.CALLBACK_BASE_URL}/api/v1/mpesa/callback"
        self.base_url = "https://api.safaricom.co.ke" if self.environment == "production" else "https://sandbox.safaricom.co.ke"

        self.max_retries = getattr(settings, "MPESA_MAX_RETRIES", 3)
        self.retry_delay = getattr(settings, "MPESA_RETRY_DELAY", 2)
        self.timeout = getattr(settings, "MPESA_TIMEOUT", 60)

        self.safaricom_prefixes = getattr(settings, "SAFARICOM_PREFIXES", [
            '70', '71', '72', '74', '79', '11'
        ])

    async def initiate_stk_push(
        self,
        phone: str,
        amount: float,
        account_reference: str,
        transaction_desc: str
    ) -> Optional[Dict]:
        """Initiate STK Push - returns raw Safaricom response."""
        try:
            logger.info(f"Initiating STK Push: amount={amount}, ref={account_reference}")

            # Validate phone
            if not any(phone.startswith(f"254{p}") for p in self.safaricom_prefixes):
                logger.error(f"Invalid phone prefix: {phone}")
                return None

            token = await self.auth_service.get_access_token()
            if not token:
                logger.error("Failed to get access token")
                return None

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            password = base64.b64encode(
                f"{self.shortcode}{self.passkey}{timestamp}".encode()
            ).decode()

            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": phone,
                "PartyB": self.shortcode,
                "PhoneNumber": phone,
                "CallBackURL": self.callback_url,
                "AccountReference": account_reference[:12],
                "TransactionDesc": transaction_desc[:36],
            }

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"

            for attempt in range(self.max_retries):
                try:
                    async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
                        response = await client.post(url, json=payload, headers=headers)
                        response.raise_for_status()

                        data = response.json()
                        logger.info(f"STK Push response: {data}")

                        if data.get("ResponseCode") == "0":
                            return {
                                "success": True,
                                "checkout_request_id": data.get("CheckoutRequestID"),
                                "merchant_request_id": data.get("MerchantRequestID"),
                                "customer_message": data.get("CustomerMessage"),
                                "response_description": data.get("ResponseDescription"),
                            }
                        else:
                            logger.error(f"STK Push error: {data.get('ResponseDescription')}")
                            return None

                except httpx.HTTPStatusError as e:
                    if e.response.status_code in [500, 502, 503, 504] and attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    logger.error(f"HTTP error: {e}")
                    return None

                except Exception as e:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    logger.error(f"STK Push error: {e}")
                    return None

            return None

        except Exception as e:
            logger.exception("STK Push error")
            return None


# ============================================================
# CALLBACK SERVICE
# ============================================================

class MpesaCallbackService:
    """Handles M-Pesa callbacks with atomic processing."""

    def __init__(self, payment_repo: PaymentRepository, service_repo: ServiceRepository):
        self.payment_repo = payment_repo
        self.service_repo = service_repo
        self.service_access_days = getattr(settings, "SERVICE_ACCESS_DAYS", 365)

    async def process_callback(self, callback_data: Dict) -> bool:
        """Process callback with idempotency."""
        try:
            logger.info("=" * 60)
            logger.info("Processing callback")

            body = callback_data.get("Body", {})
            stk = body.get("stkCallback", {})

            checkout_id = stk.get("CheckoutRequestID")
            result_code = stk.get("ResultCode")
            result_desc = stk.get("ResultDesc", "")

            if not checkout_id:
                logger.error("No CheckoutRequestID")
                return False

            logger.info(f"Checkout: {checkout_id}, Result: {result_code}")

            # ─── FIX: If payment doesn't exist, log error and return False ───
            payment = await self.payment_repo.get_by_checkout_id(checkout_id)
            if not payment:
                logger.error(
                    f"❌ Payment missing for checkout {checkout_id}. "
                    "The payment record was never created in the database."
                )
                return False

            # ─── Idempotency ───
            if payment.get("status") == PaymentStatus.COMPLETED.value:
                logger.info(f"Already completed: {checkout_id}")
                return True

            # ─── Extract metadata ───
            metadata = stk.get("CallbackMetadata", {}).get("Item", [])
            metadata_dict = {item.get("Name"): item.get("Value") for item in metadata}

            receipt = metadata_dict.get("MpesaReceiptNumber")
            paid_amount = metadata_dict.get("Amount")
            paid_phone = metadata_dict.get("PhoneNumber")
            transaction_date_raw = metadata_dict.get("TransactionDate")

            transaction_date = None
            if transaction_date_raw:
                try:
                    transaction_date = datetime.strptime(transaction_date_raw, "%Y%m%d%H%M%S")
                    transaction_date = transaction_date.replace(tzinfo=UTC)
                except ValueError:
                    logger.warning(f"Could not parse date: {transaction_date_raw}")

            if result_code == 0:
                return await self._handle_success(
                    payment=payment,
                    checkout_id=checkout_id,
                    result_code=result_code,
                    result_desc=result_desc,
                    receipt=receipt,
                    paid_amount=paid_amount,
                    paid_phone=paid_phone,
                    transaction_date=transaction_date,
                    callback_data=callback_data
                )
            else:
                return await self._handle_failure(
                    checkout_id=checkout_id,
                    result_code=result_code,
                    result_desc=result_desc,
                    callback_data=callback_data
                )

        except Exception as e:
            logger.exception("Callback processing error")
            return False

    async def _handle_success(
        self,
        payment: Dict,
        checkout_id: str,
        result_code: int,
        result_desc: str,
        receipt: Optional[str],
        paid_amount: Optional[float],
        paid_phone: Optional[str],
        transaction_date: Optional[datetime],
        callback_data: Dict
    ) -> bool:
        """Handle successful payment."""
        try:
            user_id = payment.get("user_id")
            service_id = payment.get("service_id")
            request_id = payment.get("request_id")

            # ─── Verify amount ───
            if paid_amount:
                paid_dec = Decimal(str(paid_amount))
                expected_dec = Decimal(str(payment.get("amount", 0)))
                if paid_dec != expected_dec:
                    logger.error(f"Amount mismatch: expected {expected_dec}, got {paid_dec}")
                    return False

            update_data = {
                "status": PaymentStatus.COMPLETED.value,
                "updated_at": datetime.now(UTC).isoformat(),
            }

            if result_code is not None:
                update_data["result_code"] = str(result_code)
            if result_desc:
                update_data["result_desc"] = result_desc
            if receipt:
                update_data["mpesa_receipt"] = receipt
            if paid_amount is not None:
                update_data["paid_amount"] = float(paid_amount)
            if paid_phone:
                update_data["paid_phone"] = paid_phone
            if transaction_date:
                update_data["transaction_date"] = transaction_date.isoformat()

            update_data["callback_payload"] = callback_data

            updated = await self.payment_repo.update_with_optimistic_lock(
                checkout_id=checkout_id,
                data=update_data,
                expected_status=PaymentStatus.PENDING.value
            )

            if not updated:
                logger.info(f"Payment already processed: {checkout_id}")
                return True

            # ─── Unlock service ───
            if user_id and service_id:
                try:
                    unlock_success = await self._unlock_service(user_id, service_id, checkout_id)
                    if unlock_success:
                        logger.info(f"✅ Service unlocked: {service_id}")
                    else:
                        logger.error(f"Failed to unlock service {service_id}")
                except Exception as e:
                    logger.exception(f"Unlock service error: {service_id}")

            # ─── FIX: Flip the originating request row to 'paid' server-side ───
            # This is what the dashboard's "My Requests" list depends on. It was
            # previously never written anywhere, so a completed M-Pesa payment
            # unlocked the service but the request card stayed stuck on "Pending".
            if request_id:
                try:
                    await self.payment_repo.update_request_status(request_id, "paid")
                except Exception as e:
                    logger.warning(f"Could not update request {request_id} status: {e}")

            # ─── Audit log ───
            try:
                await self._create_audit_log(
                    payment_id=payment.get("id"),
                    action="payment_completed",
                    old_status=payment.get("status"),
                    new_status=PaymentStatus.COMPLETED.value,
                    payload=update_data
                )
            except Exception as e:
                logger.warning(f"Audit log failed: {e}")

            # ─── Notification ───
            if user_id and service_id:
                try:
                    await self._create_notification(user_id, service_id)
                except Exception as e:
                    logger.warning(f"Notification failed: {e}")

            logger.info(f"✅ Payment completed: {checkout_id}")
            return True

        except Exception as e:
            logger.exception("Success handler error")
            return False

    async def _handle_failure(
        self,
        checkout_id: str,
        result_code: int,
        result_desc: str,
        callback_data: Dict
    ) -> bool:
        """Handle failed payment."""
        try:
            update_data = {
                "status": PaymentStatus.FAILED.value,
                "updated_at": datetime.now(UTC).isoformat(),
            }

            if result_code is not None:
                update_data["result_code"] = str(result_code)
            if result_desc:
                update_data["result_desc"] = result_desc

            update_data["callback_payload"] = callback_data

            updated = await self.payment_repo.update_with_optimistic_lock(
                checkout_id=checkout_id,
                data=update_data,
                expected_status=PaymentStatus.PENDING.value
            )

            if updated:
                try:
                    await self._create_audit_log(
                        payment_id=updated.get("id"),
                        action="payment_failed",
                        old_status=None,
                        new_status=PaymentStatus.FAILED.value,
                        payload=update_data
                    )
                except Exception as e:
                    logger.warning(f"Audit log failed: {e}")

            logger.warning(f"Payment failed: {result_code} - {result_desc}")
            return True

        except Exception as e:
            logger.exception("Failure handler error")
            return False

    async def _unlock_service(self, user_id: str, service_id: str, payment_ref: str) -> bool:
        """Unlock service for user."""
        try:
            existing = await self.payment_repo.get_service_access(user_id, service_id)
            if existing:
                logger.info(f"Service already unlocked: {service_id}")
                return True

            expires_at = datetime.now(UTC) + timedelta(days=self.service_access_days)

            data = {
                "user_id": user_id,
                "service_id": service_id,
                "status": ServiceAccessStatus.ACTIVE.value,
                "expires_at": expires_at.isoformat(),
                "payment_ref": payment_ref
            }

            result = await self.payment_repo.create_service_access(data)
            if result:
                logger.info(f"Service unlocked: {service_id} for {user_id}")
                return True
            else:
                logger.error(f"Failed to unlock service: {service_id}")
                return False

        except Exception as e:
            logger.exception(f"Unlock error: {service_id}")
            return False

    async def _create_notification(self, user_id: str, service_id: str) -> bool:
        """Create notification (best effort)."""
        try:
            service = await self.service_repo.get_by_code(service_id)
            service_name = service.get('name', service_id) if service else service_id

            data = {
                "user_id": user_id,
                "message": f"🎉 {service_name} has been unlocked!",
                "type": "service",
                "read": False
            }
            return await self.payment_repo.create_notification(data)

        except Exception as e:
            logger.warning(f"Notification failed: {e}")
            return False

    async def _create_audit_log(
        self,
        payment_id: Optional[str],
        action: str,
        old_status: Optional[str],
        new_status: Optional[str],
        payload: Dict
    ) -> bool:
        """Create audit log (best effort)."""
        try:
            data = {
                "payment_id": payment_id,
                "action": action,
                "old_status": old_status,
                "new_status": new_status,
                "payload": payload
            }
            return await self.payment_repo.create_audit_log(data)

        except Exception as e:
            logger.warning(f"Audit log failed: {e}")
            return False


# ============================================================
# VERIFY SERVICES TABLE ON STARTUP
# ============================================================

def verify_services_table():
    """Verify services table has correct data."""
    try:
        response = supabase.table("services").select("id, code, price, active").execute()
        services = response.data or []
        
        logger.info("=" * 70)
        logger.info("SERVICES TABLE VERIFICATION")
        logger.info(f"Found {len(services)} services:")
        
        for svc in services:
            logger.info(f"  {svc.get('id')}: {svc.get('code')} = {svc.get('price')} KES (active: {svc.get('active')})")
        
        # Verify expected services exist
        expected = ["mileage", "valuation", "ownership"]
        found = [svc.get('code') for svc in services]
        
        missing = [e for e in expected if e not in found]
        if missing:
            logger.warning(f"⚠️ Missing expected services: {missing}")
        else:
            logger.info("✅ All expected services found!")
        
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"Failed to verify services table: {e}")


# ============================================================
# MAIN MPESA SERVICE
# ============================================================

class MpesaService:
    """Main M-Pesa service orchestrator."""

    def __init__(self):
        self.service_repo = ServiceRepository()
        self.payment_repo = PaymentRepository()
        self.auth_service = MpesaAuthService()
        self.stk_service = MpesaSTKService(self.auth_service)
        self.callback_service = MpesaCallbackService(self.payment_repo, self.service_repo)

        logger.info("M-Pesa Service initialized (Enterprise Grade v7)")
        logger.info(f"  Environment: {self.auth_service.environment}")
        logger.info(f"  Shortcode: {self.stk_service.shortcode}")
        logger.info(f"  Configured: {self.is_configured()}")
        
        # ─── Verify services table ───
        verify_services_table()

    def is_configured(self) -> bool:
        """Check configuration."""
        return all([
            settings.MPESA_CONSUMER_KEY,
            settings.MPESA_CONSUMER_SECRET,
            settings.MPESA_SHORTCODE,
            settings.MPESA_PASSKEY,
            settings.CALLBACK_BASE_URL
        ])

    async def get_service(self, service_id: str) -> Optional[Dict]:
        """Get service by code."""
        return await self.service_repo.get_by_code(service_id)

    async def initiate_stk_push(
        self,
        phone: str,
        service_id: str,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        corporate_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Dict:
        """
        Initiate STK Push - BACKEND CREATES PAYMENT RECORD.
        This is the single source of truth for payment creation.
        """
        try:
            # ─── 1. Validate request ───
            request = STKPushRequest(
                phone=phone,
                service_id=service_id,
                description=description,
                user_id=user_id,
                corporate_id=corporate_id,
                request_id=request_id,
            )
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            return {"success": False, "error": str(e)}

        try:
            # ─── 2. Get service with price ───
            service = await self.service_repo.get_service_with_price(request.service_id)
            if not service:
                logger.error(f"Service not found or no price: {request.service_id}")
                return {
                    "success": False,
                    "error": f"Service '{request.service_id}' not found or not configured with a price"
                }

            # ─── 3. Get final price (directly from services table) ───
            amount = float(service["price"])
            
            if amount <= 0:
                logger.error(f"Invalid price for service {request.service_id}: {amount}")
                return {
                    "success": False,
                    "error": f"Service '{request.service_id}' has invalid price: {amount}"
                }

            logger.info(f"Service: {service.get('name')}, Price: {amount} KES")

            # ─── 3b. If a request_id was supplied, verify it actually belongs
            # to this user before we trust it. This stops one user from
            # attaching their payment to (and flipping the status of) another
            # user's request row. ───
            validated_request_id = None
            if request.request_id and request.user_id:
                owned_request = await self.payment_repo.get_by_id_for_user(
                    request.request_id, request.user_id
                )
                if owned_request:
                    validated_request_id = request.request_id
                else:
                    logger.warning(
                        f"request_id {request.request_id} does not belong to "
                        f"user {request.user_id}; ignoring it for this payment"
                    )

            # ─── 4. Send STK Push ───
            stk_result = await self.stk_service.initiate_stk_push(
                phone=request.phone,
                amount=amount,
                account_reference=request.service_id,
                transaction_desc=description or service.get("name", request.service_id)
            )

            if not stk_result:
                logger.error("STK Push failed")
                return {
                    "success": False,
                    "error": "Failed to initiate STK Push. Please try again."
                }

            checkout_id = stk_result.get("checkout_request_id")
            if not checkout_id:
                logger.error("No checkout_request_id in STK response")
                return {
                    "success": False,
                    "error": "Failed to get checkout ID from M-Pesa"
                }

            # ─── 5. Create payment record in database ───
            payment_data = {
                "user_id": request.user_id,
                "service_id": request.service_id,
                "service_name": service.get("name", request.service_id),
                "amount": amount,
                "phone": request.phone,
                "checkout_request_id": checkout_id,
                "status": PaymentStatus.PENDING.value,
                "pricing_version": service.get("version", 1),
            }

            # FIX: thread the originating 'requests' row through to the payment
            # record so the callback/manual-confirm path can flip that row's
            # status to 'paid' server-side once M-Pesa actually confirms payment.
            # Requires a nullable `request_id` column on the `payments` table
            # (ALTER TABLE payments ADD COLUMN IF NOT EXISTS request_id uuid;).
            if validated_request_id:
                payment_data["request_id"] = validated_request_id

            logger.info(f"📝 Creating payment record: {json.dumps(payment_data, default=str)}")

            saved = await self.payment_repo.create(payment_data)
            if not saved:
                logger.error(
                    f"❌ Payment record NOT saved for checkout: {checkout_id}. "
                    "Aborting — frontend will be told this failed, even though "
                    "the STK push itself went out."
                )
                # Log to failed events for manual reconciliation
                try:
                    await self.payment_repo.create_failed_event(
                        event_type="payment_create_failed",
                        payload=payment_data,
                        error="payment_repo.create() returned None after successful STK push"
                    )
                except Exception:
                    logger.exception("Could not log failed_event for manual reconciliation")

                return {
                    "success": False,
                    "error": (
                        "Your M-Pesa prompt was sent, but we couldn't save the "
                        "payment record on our end. Please do NOT enter your PIN — "
                        "cancel the prompt on your phone and try again. If you "
                        "already paid, contact support with this reference: "
                        f"{checkout_id}"
                    ),
                    "checkout_request_id": checkout_id,
                }

            logger.info(f"✅ STK Push initiated and payment saved: {checkout_id}")

            return {
                "success": True,
                "checkout_request_id": checkout_id,
                "merchant_request_id": stk_result.get("merchant_request_id"),
                "customer_message": stk_result.get("customer_message"),
                "response_description": stk_result.get("response_description"),
                "service_name": service.get("name", request.service_id),
                "amount": amount,
                "currency": service.get("currency", "KES"),
            }

        except Exception as e:
            logger.exception("STK Push error")
            return {"success": False, "error": str(e)}

    async def process_callback(self, callback_data: Dict) -> bool:
        """Process M-Pesa callback."""
        return await self.callback_service.process_callback(callback_data)

    async def get_payment_status(self, checkout_request_id: str) -> Dict:
        """Get payment status."""
        try:
            payment = await self.payment_repo.get_by_checkout_id(checkout_request_id)

            if not payment:
                return {"success": False, "error": "Payment not found"}

            return {
                "success": True,
                "checkout_request_id": payment["checkout_request_id"],
                "status": payment["status"],
                "amount": payment["amount"],
                "service_id": payment.get("service_id"),
                "service_name": payment.get("service_name"),
                "created_at": payment["created_at"],
                "updated_at": payment.get("updated_at"),
                "mpesa_receipt": payment.get("mpesa_receipt"),
                "pricing_version": payment.get("pricing_version"),
            }

        except Exception as e:
            logger.exception("Get payment status error")
            return {"success": False, "error": str(e)}

    async def confirm_payment_manually(self, checkout_request_id: str, user_id: str) -> Dict:
        """Manually confirm a payment."""
        try:
            payment = await self.payment_repo.get_by_checkout_id(checkout_request_id)

            if not payment:
                return {"success": False, "error": "Payment not found"}

            if payment.get("user_id") != user_id:
                return {"success": False, "error": "Payment does not belong to this user"}

            request_id = payment.get("request_id")

            if payment.get("status") == PaymentStatus.COMPLETED.value:
                service_id = payment.get("service_id")
                if service_id:
                    await self.callback_service._unlock_service(user_id, service_id, checkout_request_id)
                # FIX: keep the request row in sync even on the "already completed" path
                if request_id:
                    await self.payment_repo.update_request_status(request_id, "paid")
                return {"success": True, "message": "Already confirmed", "already_completed": True}

            service_id = payment.get("service_id")
            if not service_id:
                return {"success": False, "error": "Service ID not found"}

            update_data = {
                "status": PaymentStatus.COMPLETED.value,
                "updated_at": datetime.now(UTC).isoformat(),
                "result_code": "0",
                "result_desc": "Confirmed manually"
            }

            updated = await self.payment_repo.update_with_optimistic_lock(
                checkout_id=checkout_request_id,
                data=update_data,
                expected_status=PaymentStatus.PENDING.value
            )

            if not updated:
                return {"success": False, "error": "Payment was already processed"}

            unlock_success = await self.callback_service._unlock_service(
                user_id, service_id, checkout_request_id
            )

            if unlock_success:
                await self.callback_service._create_notification(user_id, service_id)
                # FIX: same request-status sync as the callback path
                if request_id:
                    await self.payment_repo.update_request_status(request_id, "paid")
                return {
                    "success": True,
                    "message": "Payment confirmed and service unlocked",
                    "service_id": service_id
                }
            else:
                return {"success": False, "error": "Failed to unlock service"}

        except Exception as e:
            logger.exception("Manual confirm error")
            return {"success": False, "error": str(e)}

    async def get_user_services(self, user_id: str) -> List[Dict]:
        """Get unlocked services for a user."""
        try:
            records = await self.payment_repo.get_user_services(user_id)

            services = []
            for item in records:
                service_id = item.get("service_id")
                expires_at = item.get("expires_at")

                if expires_at and datetime.fromisoformat(expires_at) < datetime.now(UTC):
                    continue

                service = await self.service_repo.get_by_code(service_id)
                service_name = service.get('name', service_id) if service else service_id

                services.append({
                    "service_id": service_id,
                    "service_name": service_name,
                    "status": ServiceAccessStatus.ACTIVE.value,
                    "expires_at": expires_at,
                    "unlocked_at": item.get("created_at")
                })

            return services

        except Exception as e:
            logger.exception("Get user services error")
            return []

    async def check_service_access(self, user_id: str, service_id: str) -> Dict:
        """Check if a user has access to a service."""
        try:
            access = await self.payment_repo.get_service_access(user_id, service_id)
            has_access = access is not None

            if has_access and access.get("expires_at"):
                if datetime.fromisoformat(access["expires_at"]) < datetime.now(UTC):
                    has_access = False

            service = await self.service_repo.get_by_code(service_id)
            service_name = service.get('name', service_id) if service else service_id

            return {
                "service_id": service_id,
                "unlocked": has_access,
                "service_name": service_name
            }

        except Exception as e:
            logger.exception("Check service access error")
            return {"service_id": service_id, "unlocked": False, "service_name": service_id}

    async def get_payment_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get payment history."""
        return await self.payment_repo.get_history(user_id, limit)

    async def get_all_services(self, include_inactive: bool = False) -> List[Dict]:
        """Get all available services from database."""
        return await self.service_repo.get_all(include_inactive)

    # ─── Admin API ───

    async def admin_create_service(self, data: Dict) -> Optional[Dict]:
        """Admin: Create a new service."""
        return await self.service_repo.create(data)

    async def admin_update_service(
        self,
        service_id: str,
        data: Dict,
        changed_by: str,
        reason: str = None
    ) -> Optional[Dict]:
        """Admin: Update a service with price history."""
        try:
            current = await self.service_repo.get_by_code(service_id, include_inactive=True)
            if not current:
                return None

            updated = await self.service_repo.update(service_id, data)
            if updated:
                if 'price' in data:
                    await self.payment_repo.create_price_history({
                        "service_id": current.get("id"),
                        "old_price": current.get("price"),
                        "new_price": data["price"],
                        "changed_by": changed_by,
                        "reason": reason or data.get("reason", "Price update")
                    })

                await self.payment_repo.create_audit_log({
                    "payment_id": None,
                    "action": "service_updated",
                    "old_status": None,
                    "new_status": None,
                    "payload": {
                        "service_id": service_id,
                        "changes": data,
                        "changed_by": changed_by,
                        "reason": reason
                    }
                })

            return updated

        except Exception as e:
            logger.exception("Admin update service error")
            return None

    async def admin_delete_service(self, service_id: str, deleted_by: str) -> bool:
        """Admin: Delete/Deactivate a service."""
        return await self.service_repo.soft_delete(service_id, deleted_by)

    async def admin_restore_service(self, service_id: str) -> bool:
        """Admin: Restore a soft-deleted service."""
        return await self.service_repo.restore(service_id)

    async def admin_get_service(self, service_id: str) -> Optional[Dict]:
        """Admin: Get a service (including inactive)."""
        return await self.service_repo.get_by_code(service_id, include_inactive=True)

    async def admin_get_all_services(self) -> List[Dict]:
        """Admin: Get all services including inactive."""
        return await self.service_repo.get_all(include_inactive=True)

    async def admin_get_price_history(self, service_id: str) -> List[Dict]:
        """Admin: Get price history for a service."""
        try:
            service = await self.service_repo.get_by_code(service_id, include_inactive=True)
            if not service:
                return []

            response = await self.payment_repo._run_sync(
                lambda: supabase.table("service_price_history")
                .select("*")
                .eq("service_id", service.get("id"))
                .order("created_at", desc=True)
                .execute()
            )
            return response.data or []

        except Exception as e:
            logger.exception("Get price history error")
            return []

    async def expire_stale_payments(self, minutes: int = 30) -> int:
        """Expire stale pending payments."""
        return await self.payment_repo.expire_stale_payments(minutes)


# ============================================================
# SINGLE INSTANCE
# ============================================================

mpesa_service = MpesaService()
