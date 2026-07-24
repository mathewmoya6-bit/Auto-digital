"""
Auto-D Kenya
M-Pesa Business Logic - Enterprise Grade v5 (Production Ready)
FIXED: Works with service_prices table
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


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class PricingRuleType(str, Enum):
    CORPORATE = "corporate"
    PREMIUM = "premium"
    WEEKEND = "weekend"
    BULK = "bulk"
    PROMOTIONAL = "promotional"


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


class STKPushResponse(BaseModel):
    """STK Push response model."""
    success: bool
    checkout_request_id: Optional[str] = None
    customer_message: Optional[str] = None
    response_description: Optional[str] = None
    error: Optional[str] = None


class PricingResult(BaseModel):
    """Pricing calculation result."""
    base_price: Decimal
    vat: Decimal
    discount: Decimal
    service_fee: Decimal
    total: Decimal
    currency: str
    pricing_version: int
    breakdown: Dict[str, Any]


# ============================================================
# REPOSITORIES - FIXED for service_prices table
# ============================================================

class ServiceRepository:
    """Service database operations - FIXED to use service_prices table."""
    
    def __init__(self):
        self._cache = None
        self._last_refresh = None
        self._cache_duration = timedelta(minutes=5)
    
    async def get_by_code(self, code: str, include_inactive: bool = False) -> Optional[Dict]:
        """
        Get service by code from service_prices table.
        Maps service_prices fields to expected service fields.
        """
        try:
            # ─── FIX: Use service_prices table ───
            response = await self._run_sync(
                supabase.table("service_prices")
                .select("*")
                .eq("service_type", code)
                .limit(1)
                .execute()
            )
            
            if not response.data:
                logger.warning(f"Service not found: {code}")
                return None
            
            row = response.data[0]
            
            # ─── FIX: Map service_prices fields to expected service fields ───
            return {
                "id": row.get("id"),
                "code": row.get("service_type"),
                "name": row.get("service_type", code).replace("_", " ").title(),
                "base_price": Decimal(str(row.get("price", 0))),
                "price": Decimal(str(row.get("price", 0))),  # For compatibility
                "vat_rate": Decimal("0.16"),  # Default VAT rate
                "discount_value": Decimal("0"),
                "discount_type": None,
                "service_fee": Decimal("0"),
                "currency": row.get("currency", "KES"),
                "description": row.get("description", ""),
                "is_active": True,
                "active": True,
                "version": 1,
                "display_order": 0,
                "sort_order": 0,
            }
            
        except Exception as e:
            logger.exception(f"Get service error: {code}")
            return None
    
    async def get_all(self, include_inactive: bool = False) -> List[Dict]:
        """
        Get all services from service_prices table.
        """
        try:
            # ─── FIX: Use service_prices table ───
            response = await self._run_sync(
                supabase.table("service_prices")
                .select("*")
                .order("id")
                .execute()
            )
            
            if not response.data:
                return []
            
            # ─── FIX: Map each row to expected service format ───
            services = []
            for row in response.data:
                services.append({
                    "id": row.get("id"),
                    "code": row.get("service_type"),
                    "name": row.get("service_type", "").replace("_", " ").title(),
                    "base_price": Decimal(str(row.get("price", 0))),
                    "price": Decimal(str(row.get("price", 0))),
                    "vat_rate": Decimal("0.16"),
                    "discount_value": Decimal("0"),
                    "discount_type": None,
                    "service_fee": Decimal("0"),
                    "currency": row.get("currency", "KES"),
                    "description": row.get("description", ""),
                    "is_active": True,
                    "active": True,
                    "version": 1,
                    "display_order": 0,
                    "sort_order": 0,
                })
            
            return services
            
        except Exception as e:
            logger.exception("Get all services error")
            return []
    
    async def create(self, data: Dict) -> Optional[Dict]:
        """
        Create a new service in service_prices table.
        """
        try:
            # ─── FIX: Map service fields to service_prices fields ───
            service_data = {
                "service_type": data.get("code"),
                "price": float(data.get("base_price", 0)),
                "currency": data.get("currency", "KES"),
                "description": data.get("description", ""),
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
            
            response = await self._run_sync(
                supabase.table("service_prices").insert(service_data).execute()
            )
            
            if response.data:
                self._clear_cache()
                row = response.data[0]
                return {
                    "id": row.get("id"),
                    "code": row.get("service_type"),
                    "base_price": Decimal(str(row.get("price", 0))),
                    "currency": row.get("currency", "KES"),
                }
            return None
            
        except Exception as e:
            logger.exception("Create service error")
            return None
    
    async def update(self, code: str, data: Dict) -> Optional[Dict]:
        """Update a service in service_prices table."""
        try:
            # ─── FIX: Map service fields to service_prices fields ───
            update_data = {}
            if "base_price" in data:
                update_data["price"] = float(data["base_price"])
            if "currency" in data:
                update_data["currency"] = data["currency"]
            if "description" in data:
                update_data["description"] = data["description"]
            
            if not update_data:
                return await self.get_by_code(code, include_inactive=True)
            
            update_data["updated_at"] = datetime.now(UTC).isoformat()
            
            response = await self._run_sync(
                supabase.table("service_prices")
                .update(update_data)
                .eq("service_type", code)
                .execute()
            )
            
            if response.data:
                self._clear_cache()
                row = response.data[0]
                return {
                    "id": row.get("id"),
                    "code": row.get("service_type"),
                    "base_price": Decimal(str(row.get("price", 0))),
                    "currency": row.get("currency", "KES"),
                }
            return None
            
        except Exception as e:
            logger.exception(f"Update service error: {code}")
            return None
    
    async def soft_delete(self, code: str, deleted_by: str) -> bool:
        """Soft delete - just remove from service_prices."""
        try:
            response = await self._run_sync(
                supabase.table("service_prices")
                .delete()
                .eq("service_type", code)
                .execute()
            )
            
            if response.data:
                self._clear_cache()
                return True
            return False
            
        except Exception as e:
            logger.exception(f"Delete service error: {code}")
            return False
    
    async def restore(self, code: str) -> bool:
        """Restore - not applicable for service_prices, would need to re-insert."""
        logger.warning(f"Restore not supported for service_prices table: {code}")
        return False
    
    def _clear_cache(self):
        """Clear the cache."""
        self._cache = None
        self._last_refresh = None
    
    async def _run_sync(self, func):
        """Run synchronous Supabase calls in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_db_executor, func)


class PaymentRepository:
    """Payment database operations."""
    
    async def create(self, data: Dict) -> Optional[Dict]:
        """Create a payment record."""
        try:
            data['id'] = str(uuid.uuid4())
            data['created_at'] = datetime.now(UTC).isoformat()
            data['updated_at'] = datetime.now(UTC).isoformat()
            
            response = await self._run_sync(
                supabase.table("payments").insert(data).execute()
            )
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.exception("Create payment error")
            return None
    
    async def get_by_checkout_id(self, checkout_id: str) -> Optional[Dict]:
        """Get payment by checkout request ID."""
        try:
            response = await self._run_sync(
                supabase.table("payments")
                .select("*")
                .eq("checkout_request_id", checkout_id)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.exception(f"Get payment error: {checkout_id}")
            return None
    
    async def update_with_optimistic_lock(
        self,
        checkout_id: str,
        data: Dict,
        expected_status: str = "pending"
    ) -> Optional[Dict]:
        """
        Update payment with optimistic locking.
        Only updates if status matches expected_status.
        """
        try:
            data['updated_at'] = datetime.now(UTC).isoformat()
            
            response = await self._run_sync(
                supabase.table("payments")
                .update(data)
                .eq("checkout_request_id", checkout_id)
                .eq("status", expected_status)
                .execute()
            )
            
            if response.data:
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
                supabase.table("payments")
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
                supabase.table("service_access")
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
                supabase.table("service_access").insert(data).execute()
            )
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.exception("Create service access error")
            return None
    
    async def get_user_services(self, user_id: str) -> List[Dict]:
        """Get all active services for a user."""
        try:
            response = await self._run_sync(
                supabase.table("service_access")
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
                supabase.table("notifications").insert(data).execute()
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
                supabase.table("payment_audit_log").insert(data).execute()
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
                supabase.table("service_price_history").insert(data).execute()
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
                supabase.table("failed_events").insert(data).execute()
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
                supabase.table("payments")
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
    
    async def _run_sync(self, func):
        """Run synchronous Supabase calls in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_db_executor, func)


# ============================================================
# PRICING ENGINE
# ============================================================

class PricingEngine:
    """Service pricing engine with calculations."""
    
    def __init__(self, service_repo: ServiceRepository):
        self.service_repo = service_repo
    
    async def calculate_price(
        self,
        service_id: str,
        user_id: Optional[str] = None,
        corporate_id: Optional[str] = None,
        apply_discounts: bool = True
    ) -> Optional[PricingResult]:
        """Calculate the final price for a service."""
        try:
            service = await self.service_repo.get_by_code(service_id)
            if not service:
                logger.error(f"Service not found: {service_id}")
                return None
            
            # ─── Use mapped fields from service_repo ───
            base_price = service.get("base_price", Decimal("0"))
            if isinstance(base_price, (int, float)):
                base_price = Decimal(str(base_price))
            
            vat_rate = service.get("vat_rate", Decimal("0.16"))
            if isinstance(vat_rate, (int, float)):
                vat_rate = Decimal(str(vat_rate))
            
            discount_value = service.get("discount_value", Decimal("0"))
            if isinstance(discount_value, (int, float)):
                discount_value = Decimal(str(discount_value))
            
            discount_type = service.get("discount_type")
            service_fee = service.get("service_fee", Decimal("0"))
            if isinstance(service_fee, (int, float)):
                service_fee = Decimal(str(service_fee))
            
            currency = service.get("currency", "KES")
            version = service.get("version", 1)
            
            vat = (base_price * vat_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            discount = Decimal("0")
            if apply_discounts and discount_value > 0:
                if discount_type == DiscountType.PERCENTAGE.value:
                    discount = (base_price * discount_value / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                elif discount_type == DiscountType.FIXED.value:
                    discount = discount_value
                elif corporate_id:
                    corporate_discount = await self._get_corporate_discount(corporate_id)
                    if corporate_discount:
                        discount = corporate_discount
            
            total = (base_price + vat + service_fee - discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            return PricingResult(
                base_price=base_price,
                vat=vat,
                discount=discount,
                service_fee=service_fee,
                total=total,
                currency=currency,
                pricing_version=version,
                breakdown={
                    "service_name": service.get("name", service_id),
                    "base_price": str(base_price),
                    "vat_rate": str(vat_rate),
                    "vat": str(vat),
                    "discount_type": discount_type,
                    "discount_value": str(discount_value),
                    "discount": str(discount),
                    "service_fee": str(service_fee),
                    "total": str(total),
                    "currency": currency,
                    "pricing_version": version
                }
            )
            
        except Exception as e:
            logger.exception("Price calculation error")
            return None
    
    async def _get_corporate_discount(self, corporate_id: str) -> Optional[Decimal]:
        """Get corporate discount for a customer."""
        try:
            response = await self._run_sync(
                supabase.table("corporate_discounts")
                .select("*")
                .eq("corporate_id", corporate_id)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            
            if response.data:
                return Decimal(str(response.data[0].get("discount_value", 0)))
            return None
            
        except Exception as e:
            logger.exception("Corporate discount error")
            return None
    
    async def _run_sync(self, func):
        """Run synchronous Supabase calls in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_db_executor, func)


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
    
    def __init__(self, auth_service: MpesaAuthService, pricing_engine: PricingEngine):
        self.auth_service = auth_service
        self.pricing_engine = pricing_engine
        
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
    
    async def initiate_stk_push(self, request: STKPushRequest) -> STKPushResponse:
        """Initiate STK Push - AMOUNT FROM PRICING ENGINE."""
        try:
            pricing = await self.pricing_engine.calculate_price(
                service_id=request.service_id,
                user_id=request.user_id,
                corporate_id=request.corporate_id,
                apply_discounts=True
            )
            
            if not pricing:
                return STKPushResponse(
                    success=False,
                    error=f"Service '{request.service_id}' not found or inactive"
                )
            
            amount = pricing.total
            logger.info(f"Calculated price: {amount} {pricing.currency}")
            
            phone = request.phone
            if not any(phone.startswith(f"254{p}") for p in self.safaricom_prefixes):
                return STKPushResponse(
                    success=False,
                    error="Invalid Safaricom number"
                )
            
            token = await self.auth_service.get_access_token()
            if not token:
                return STKPushResponse(success=False, error="Authentication failed")
            
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            password = base64.b64encode(
                f"{self.shortcode}{self.passkey}{timestamp}".encode()
            ).decode()
            
            description = request.description or f"Auto-D: {request.service_id}"
            
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
                "AccountReference": request.service_id[:12],
                "TransactionDesc": description[:36],
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
                        
                        if data.get("ResponseCode") == "0":
                            return STKPushResponse(
                                success=True,
                                checkout_request_id=data.get("CheckoutRequestID"),
                                customer_message=data.get("CustomerMessage"),
                                response_description=data.get("ResponseDescription")
                            )
                        else:
                            return STKPushResponse(
                                success=False,
                                error=data.get("ResponseDescription", "STK Push failed")
                            )
                            
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in [500, 502, 503, 504] and attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    return STKPushResponse(success=False, error=str(e))
                    
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    return STKPushResponse(success=False, error=str(e))
            
            return STKPushResponse(success=False, error="Max retries exceeded")
            
        except Exception as e:
            logger.exception("STK Push error")
            return STKPushResponse(success=False, error=str(e))


# ============================================================
# EVENT BUS
# ============================================================

class EventType(str, Enum):
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    SERVICE_UNLOCKED = "service.unlocked"
    PAYMENT_REFUNDED = "payment.refunded"


class EventBus:
    """Simple event bus for event-driven architecture."""
    
    _handlers = {}
    
    @classmethod
    def register(cls, event_type: EventType, handler):
        if event_type not in cls._handlers:
            cls._handlers[event_type] = []
        cls._handlers[event_type].append(handler)
    
    @classmethod
    async def publish(cls, event_type: EventType, data: Dict):
        if event_type not in cls._handlers:
            return
        
        logger.info(f"Event published: {event_type}")
        
        for handler in cls._handlers[event_type]:
            try:
                await handler(data)
            except Exception as e:
                logger.exception(f"Event handler error: {event_type}")


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
        """Process callback with idempotency and atomicity."""
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
            
            payment = await self.payment_repo.get_by_checkout_id(checkout_id)
            if not payment:
                logger.error(f"Payment not found: {checkout_id}")
                return False
            
            # ─── Idempotency ───
            if payment.get("status") == PaymentStatus.COMPLETED.value:
                logger.info(f"Already completed: {checkout_id}")
                return True
            
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
            
            callback_payload = {
                "result_code": result_code,
                "result_desc": result_desc,
                "receipt": receipt,
                "amount": paid_amount,
                "phone": paid_phone,
                "transaction_date": transaction_date_raw,
                "raw": callback_data
            }
            
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
                    callback_payload=callback_payload
                )
            else:
                return await self._handle_failure(
                    checkout_id=checkout_id,
                    result_code=result_code,
                    result_desc=result_desc,
                    callback_payload=callback_payload
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
        callback_payload: Dict
    ) -> bool:
        """Handle successful payment with atomicity."""
        try:
            user_id = payment.get("user_id")
            service_id = payment.get("service_id")
            
            if paid_amount:
                paid_dec = Decimal(str(paid_amount))
                expected_dec = Decimal(str(payment.get("amount", 0)))
                if paid_dec != expected_dec:
                    logger.error(f"Amount mismatch: expected {expected_dec}, got {paid_dec}")
                    return False
            
            update_data = {
                "status": PaymentStatus.COMPLETED.value,
                "updated_at": datetime.now(UTC).isoformat(),
                "result_code": str(result_code),
                "result_desc": result_desc,
                "callback_payload": callback_payload
            }
            if receipt:
                update_data["mpesa_receipt"] = receipt
            if paid_amount:
                update_data["paid_amount"] = float(paid_amount)
            if paid_phone:
                update_data["paid_phone"] = paid_phone
            if transaction_date:
                update_data["transaction_date"] = transaction_date.isoformat()
            
            updated = await self.payment_repo.update_with_optimistic_lock(
                checkout_id=checkout_id,
                data=update_data,
                expected_status=PaymentStatus.PENDING.value
            )
            
            if not updated:
                logger.info(f"Payment already processed: {checkout_id}")
                return True
            
            unlock_success = False
            if user_id and service_id:
                try:
                    unlock_success = await self._unlock_service(user_id, service_id, checkout_id)
                    if unlock_success:
                        await EventBus.publish(
                            EventType.PAYMENT_COMPLETED,
                            {
                                "checkout_id": checkout_id,
                                "user_id": user_id,
                                "service_id": service_id,
                                "amount": payment.get("amount"),
                                "receipt": receipt
                            }
                        )
                        await EventBus.publish(
                            EventType.SERVICE_UNLOCKED,
                            {
                                "user_id": user_id,
                                "service_id": service_id,
                                "payment_ref": checkout_id
                            }
                        )
                    else:
                        logger.error(f"Failed to unlock service {service_id}")
                        await self.payment_repo.create_failed_event(
                            event_type="service_unlock_failed",
                            payload={
                                "user_id": user_id,
                                "service_id": service_id,
                                "payment_ref": checkout_id
                            },
                            error="Service unlock failed after successful payment"
                        )
                except Exception as e:
                    logger.exception(f"Unlock service error: {service_id}")
                    await self.payment_repo.create_failed_event(
                        event_type="service_unlock_error",
                        payload={
                            "user_id": user_id,
                            "service_id": service_id,
                            "payment_ref": checkout_id
                        },
                        error=str(e)
                    )
            
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
            
            if user_id and service_id:
                try:
                    await self._create_notification(user_id, service_id)
                except Exception as e:
                    logger.warning(f"Notification failed: {e}")
            
            logger.info(f"Payment completed: {checkout_id}")
            return True
            
        except Exception as e:
            logger.exception("Success handler error")
            return False
    
    async def _handle_failure(
        self,
        checkout_id: str,
        result_code: int,
        result_desc: str,
        callback_payload: Dict
    ) -> bool:
        """Handle failed payment."""
        try:
            update_data = {
                "status": PaymentStatus.FAILED.value,
                "updated_at": datetime.now(UTC).isoformat(),
                "result_code": str(result_code),
                "result_desc": result_desc,
                "callback_payload": callback_payload
            }
            
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
            
            await EventBus.publish(
                EventType.PAYMENT_FAILED,
                {"checkout_id": checkout_id, "reason": result_desc}
            )
            
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
# MAIN MPESA SERVICE
# ============================================================

class MpesaService:
    """Main M-Pesa service orchestrator."""
    
    def __init__(self):
        self.service_repo = ServiceRepository()
        self.payment_repo = PaymentRepository()
        self.pricing_engine = PricingEngine(self.service_repo)
        self.auth_service = MpesaAuthService()
        self.stk_service = MpesaSTKService(self.auth_service, self.pricing_engine)
        self.callback_service = MpesaCallbackService(self.payment_repo, self.service_repo)
        
        logger.info("M-Pesa Service initialized (Enterprise Grade v5)")
        logger.info(f"  Environment: {self.auth_service.environment}")
        logger.info(f"  Shortcode: {self.stk_service.shortcode}")
        logger.info(f"  Configured: {self.is_configured()}")
    
    def is_configured(self) -> bool:
        """Check configuration."""
        return all([
            settings.MPESA_CONSUMER_KEY,
            settings.MPESA_CONSUMER_SECRET,
            settings.MPESA_SHORTCODE,
            settings.MPESA_PASSKEY,
            settings.CALLBACK_BASE_URL
        ])
    
    async def initiate_stk_push(
        self,
        phone: str,
        service_id: str,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        corporate_id: Optional[str] = None
    ) -> Dict:
        """Initiate STK Push - NO AMOUNT FROM FRONTEND."""
        try:
            request = STKPushRequest(
                phone=phone,
                service_id=service_id,
                description=description,
                user_id=user_id,
                corporate_id=corporate_id
            )
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            return {"success": False, "error": str(e)}
        
        logger.info(f"Initiating STK Push for service: {request.service_id}")
        
        pricing = await self.pricing_engine.calculate_price(
            service_id=request.service_id,
            user_id=request.user_id,
            corporate_id=request.corporate_id
        )
        
        if not pricing:
            return {
                "success": False,
                "error": f"Service '{request.service_id}' not found or inactive"
            }
        
        logger.info(f"Total price: {pricing.total} {pricing.currency}")
        
        response = await self.stk_service.initiate_stk_push(request)
        
        if response.success and response.checkout_request_id:
            payment_data = {
                "user_id": request.user_id,
                "service_id": request.service_id,
                "service_name": pricing.breakdown.get("service_name", request.service_id),
                "amount": float(pricing.total),
                "phone": request.phone,
                "checkout_request_id": response.checkout_request_id,
                "status": PaymentStatus.PENDING.value,
                "pricing_version": pricing.pricing_version,
                "pricing_snapshot": pricing.breakdown
            }
            
            saved = await self.payment_repo.create(payment_data)
            if saved:
                logger.info(f"Payment record saved: {response.checkout_request_id}")
            else:
                logger.warning("Payment record not saved, but STK was sent")
        
        return {
            "success": response.success,
            "checkout_request_id": response.checkout_request_id,
            "customer_message": response.customer_message,
            "response_description": response.response_description,
            "error": response.error,
            "service_name": pricing.breakdown.get("service_name", request.service_id),
            "amount": float(pricing.total),
            "pricing_breakdown": pricing.breakdown
        }
    
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
                "pricing_snapshot": payment.get("pricing_snapshot")
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
            
            if payment.get("status") == PaymentStatus.COMPLETED.value:
                service_id = payment.get("service_id")
                if service_id:
                    await self.callback_service._unlock_service(user_id, service_id, checkout_request_id)
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
                await self.callback_service._create_audit_log(
                    payment_id=payment.get("id"),
                    action="manual_confirm",
                    old_status=payment.get("status"),
                    new_status=PaymentStatus.COMPLETED.value,
                    payload=update_data
                )
                
                return {"success": True, "message": "Payment confirmed and service unlocked"}
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
                if 'base_price' in data:
                    await self.payment_repo.create_price_history({
                        "service_id": current.get("id"),
                        "old_price": current.get("base_price"),
                        "new_price": data["base_price"],
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
                supabase.table("service_price_history")
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
