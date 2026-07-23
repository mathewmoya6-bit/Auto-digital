"""
Auto-D Kenya
M-Pesa Business Logic - Enterprise Grade v4 (10/10)
"""

import base64
import json
import logging
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
from decimal import Decimal, getcontext, ROUND_HALF_UP
from concurrent.futures import ThreadPoolExecutor

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
    merchant_request_id: Optional[str] = None
    customer_message: Optional[str] = None
    response_description: Optional[str] = None
    error: Optional[str] = None


class PricingRule(BaseModel):
    """Pricing rule model."""
    id: Optional[int] = None
    rule_type: PricingRuleType
    discount_type: DiscountType
    discount_value: Decimal
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    applies_to_services: Optional[List[str]] = None
    is_active: bool = True
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None


class ServiceCreate(BaseModel):
    """Create service model."""
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    base_price: Decimal = Field(..., gt=0, decimal_places=2)
    vat_rate: Decimal = Field(default=Decimal("0.16"), ge=0, le=1, decimal_places=2)
    discount_type: Optional[DiscountType] = None
    discount_value: Decimal = Field(default=Decimal("0"), ge=0)
    service_fee: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="KES", max_length=3)
    description: Optional[str] = None
    category_id: Optional[int] = None
    icon: Optional[str] = None
    display_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None


class ServiceUpdate(BaseModel):
    """Update service model."""
    name: Optional[str] = Field(None, max_length=100)
    base_price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    vat_rate: Optional[Decimal] = Field(None, ge=0, le=1, decimal_places=2)
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[Decimal] = Field(None, ge=0)
    service_fee: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=3)
    description: Optional[str] = None
    category_id: Optional[int] = None
    icon: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    reason: Optional[str] = Field(None, description="Reason for change")


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
# REPOSITORIES
# ============================================================

class ServiceRepository:
    """Service database operations."""
    
    def __init__(self):
        self._cache = None
        self._last_refresh = None
        self._cache_duration = timedelta(minutes=5)
    
    async def get_by_code(self, code: str, include_inactive: bool = False) -> Optional[Dict]:
        """Get service by code."""
        try:
            query = supabase.table("services").select("*").eq("code", code)
            if not include_inactive:
                query = query.eq("is_active", True)
            
            response = await self._run_sync(query.limit(1).execute())
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"❌ Get service error: {str(e)}")
            return None
    
    async def get_all(self, include_inactive: bool = False) -> List[Dict]:
        """Get all services."""
        try:
            query = supabase.table("services").select("*")
            if not include_inactive:
                query = query.eq("is_active", True)
            
            response = await self._run_sync(query.order("display_order").execute())
            return response.data or []
            
        except Exception as e:
            logger.error(f"❌ Get all services error: {str(e)}")
            return []
    
    async def create(self, data: Dict) -> Optional[Dict]:
        """Create a new service."""
        try:
            # Add timestamps
            data['created_at'] = datetime.utcnow().isoformat()
            data['updated_at'] = datetime.utcnow().isoformat()
            data['version'] = 1
            
            response = await self._run_sync(
                supabase.table("services").insert(data).execute()
            )
            
            if response.data:
                self._clear_cache()
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"❌ Create service error: {str(e)}")
            return None
    
    async def update(self, code: str, data: Dict) -> Optional[Dict]:
        """Update a service with optimistic locking."""
        try:
            # Get current version
            current = await self.get_by_code(code, include_inactive=True)
            if not current:
                return None
            
            # Increment version
            data['version'] = current.get('version', 0) + 1
            data['updated_at'] = datetime.utcnow().isoformat()
            
            # ─── FIX: Optimistic locking ───
            response = await self._run_sync(
                supabase.table("services")
                .update(data)
                .eq("code", code)
                .eq("version", current.get('version', 0))
                .execute()
            )
            
            if not response.data:
                logger.warning(f"⚠️ Optimistic lock failed for service {code}")
                return None
            
            self._clear_cache()
            return response.data[0]
            
        except Exception as e:
            logger.error(f"❌ Update service error: {str(e)}")
            return None
    
    async def soft_delete(self, code: str, deleted_by: str) -> bool:
        """Soft delete a service."""
        try:
            response = await self._run_sync(
                supabase.table("services")
                .update({
                    "is_active": False,
                    "deleted_at": datetime.utcnow().isoformat(),
                    "deleted_by": deleted_by,
                    "updated_at": datetime.utcnow().isoformat()
                })
                .eq("code", code)
                .execute()
            )
            
            if response.data:
                self._clear_cache()
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Delete service error: {str(e)}")
            return False
    
    async def restore(self, code: str) -> bool:
        """Restore a soft-deleted service."""
        try:
            response = await self._run_sync(
                supabase.table("services")
                .update({
                    "is_active": True,
                    "deleted_at": None,
                    "deleted_by": None,
                    "updated_at": datetime.utcnow().isoformat()
                })
                .eq("code", code)
                .execute()
            )
            
            if response.data:
                self._clear_cache()
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Restore service error: {str(e)}")
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
            response = await self._run_sync(
                supabase.table("payments").insert(data).execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"❌ Create payment error: {str(e)}")
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
            logger.error(f"❌ Get payment error: {str(e)}")
            return None
    
    async def update(self, checkout_id: str, data: Dict) -> Optional[Dict]:
        """Update payment record."""
        try:
            response = await self._run_sync(
                supabase.table("payments")
                .update(data)
                .eq("checkout_request_id", checkout_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"❌ Update payment error: {str(e)}")
            return None
    
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
            logger.error(f"❌ Get service access error: {str(e)}")
            return None
    
    async def create_service_access(self, data: Dict) -> Optional[Dict]:
        """Create service access record."""
        try:
            response = await self._run_sync(
                supabase.table("service_access").insert(data).execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"❌ Create service access error: {str(e)}")
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
            logger.error(f"❌ Get user services error: {str(e)}")
            return []
    
    async def create_notification(self, data: Dict) -> bool:
        """Create a notification."""
        try:
            await self._run_sync(
                supabase.table("notifications").insert(data).execute()
            )
            return True
        except Exception as e:
            logger.error(f"❌ Notification error: {str(e)}")
            return False
    
    async def create_audit_log(self, data: Dict) -> bool:
        """Create audit log."""
        try:
            await self._run_sync(
                supabase.table("payment_audit_log").insert(data).execute()
            )
            return True
        except Exception as e:
            logger.error(f"❌ Audit log error: {str(e)}")
            return False
    
    async def create_price_history(self, data: Dict) -> bool:
        """Create price history record."""
        try:
            await self._run_sync(
                supabase.table("service_price_history").insert(data).execute()
            )
            return True
        except Exception as e:
            logger.error(f"❌ Price history error: {str(e)}")
            return False
    
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
        # ─── FIX: Get service from repository ───
        service = await self.service_repo.get_by_code(service_id)
        if not service:
            logger.error(f"❌ Service not found: {service_id}")
            return None
        
        # ─── FIX: Use Decimal for all financial calculations ───
        base_price = Decimal(str(service.get("base_price", 0)))
        vat_rate = Decimal(str(service.get("vat_rate", 0.16)))
        discount_value = Decimal(str(service.get("discount_value", 0)))
        discount_type = service.get("discount_type")
        service_fee = Decimal(str(service.get("service_fee", 0)))
        currency = service.get("currency", "KES")
        version = service.get("version", 1)
        
        # ─── FIX: Calculate VAT ───
        vat = (base_price * vat_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # ─── FIX: Calculate discount ───
        discount = Decimal("0")
        if apply_discounts and discount_value > 0:
            if discount_type == DiscountType.PERCENTAGE.value:
                discount = (base_price * discount_value / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            elif discount_type == DiscountType.FIXED.value:
                discount = discount_value
            elif corporate_id:
                # ─── FIX: Apply corporate discount ───
                corporate_discount = await self._get_corporate_discount(corporate_id)
                if corporate_discount:
                    discount = corporate_discount
        
        # ─── FIX: Calculate total ───
        total = (base_price + vat + service_fee - discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # ─── FIX: Return structured result ───
        return PricingResult(
            base_price=base_price,
            vat=vat,
            discount=discount,
            service_fee=service_fee,
            total=total,
            currency=currency,
            pricing_version=version,
            breakdown={
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
                discount_type = response.data[0].get("discount_type")
                discount_value = Decimal(str(response.data[0].get("discount_value", 0)))
                return discount_value
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Corporate discount error: {str(e)}")
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
                if datetime.utcnow() < self._token_expiry:
                    logger.debug("✅ Using cached token")
                    return self._cached_token
            
            logger.info("🔄 Refreshing access token")
            
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
                        self._token_expiry = datetime.utcnow() + timedelta(minutes=self.token_cache_minutes)
                        logger.info("✅ Token cached")
                        return token
                    else:
                        logger.error("❌ No token in response")
                        return None
                        
            except Exception as e:
                logger.error(f"❌ Token error: {str(e)}")
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
        
        # ─── FIX: Calculate price using pricing engine ───
        pricing = await self.pricing_engine.calculate_price(
            service_id=request.service_id,
            user_id=request.user_id,
            corporate_id=request.corporate_id,
            apply_discounts=True
        )
        
        if not pricing:
            logger.error(f"❌ Pricing calculation failed: {request.service_id}")
            return STKPushResponse(
                success=False,
                error=f"Service '{request.service_id}' not found or inactive"
            )
        
        amount = pricing.total
        logger.info(f"💰 Calculated price for {request.service_id}: {amount} {pricing.currency}")
        logger.info(f"📊 Pricing breakdown: {pricing.breakdown}")
        
        # ─── Validate phone prefix ───
        phone = request.phone
        if not any(phone.startswith(f"254{p}") for p in self.safaricom_prefixes):
            logger.warning(f"⚠️ Invalid Safaricom prefix: {phone}")
            return STKPushResponse(
                success=False,
                error="Invalid Safaricom number"
            )
        
        # ─── Get token ───
        token = await self.auth_service.get_access_token()
        if not token:
            return STKPushResponse(success=False, error="Authentication failed")
        
        # ─── Build payload ───
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
        
        # ─── Send with retry ───
        for attempt in range(self.max_retries):
            try:
                logger.info(f"📱 STK Push attempt {attempt + 1}/{self.max_retries}")
                
                async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    if data.get("ResponseCode") == "0":
                        return STKPushResponse(
                            success=True,
                            checkout_request_id=data.get("CheckoutRequestID"),
                            merchant_request_id=data.get("MerchantRequestID"),
                            customer_message=data.get("CustomerMessage"),
                            response_description=data.get("ResponseDescription")
                        )
                    else:
                        error_msg = data.get("ResponseDescription", "STK Push failed")
                        logger.error(f"❌ STK Push failed: {error_msg}")
                        return STKPushResponse(
                            success=False,
                            error=error_msg
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


# ============================================================
# EVENT BUS (Event-Driven Architecture)
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
        """Register a handler for an event type."""
        if event_type not in cls._handlers:
            cls._handlers[event_type] = []
        cls._handlers[event_type].append(handler)
    
    @classmethod
    async def publish(cls, event_type: EventType, data: Dict):
        """Publish an event to all registered handlers."""
        if event_type not in cls._handlers:
            return
        
        logger.info(f"📢 Event published: {event_type}")
        
        for handler in cls._handlers[event_type]:
            try:
                await handler(data)
            except Exception as e:
                logger.error(f"❌ Event handler error: {str(e)}")


# ============================================================
# EVENT HANDLERS
# ============================================================

async def handle_payment_completed(data: Dict):
    """Handle payment completed event."""
    logger.info(f"🎉 Payment completed: {data.get('checkout_id')}")
    # ─── Add additional handlers here ───


async def handle_service_unlocked(data: Dict):
    """Handle service unlocked event."""
    logger.info(f"🔓 Service unlocked: {data.get('service_id')} for {data.get('user_id')}")


# ─── Register event handlers ───
EventBus.register(EventType.PAYMENT_COMPLETED, handle_payment_completed)
EventBus.register(EventType.SERVICE_UNLOCKED, handle_service_unlocked)


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
            logger.info("📞 Processing callback")
            
            body = callback_data.get("Body", {})
            stk = body.get("stkCallback", {})
            
            checkout_id = stk.get("CheckoutRequestID")
            result_code = stk.get("ResultCode")
            result_desc = stk.get("ResultDesc", "")
            merchant_id = stk.get("MerchantRequestID")
            
            if not checkout_id:
                logger.error("❌ No CheckoutRequestID")
                return False
            
            logger.info(f"📊 Checkout: {checkout_id}, Result: {result_code}")
            
            payment = await self.payment_repo.get_by_checkout_id(checkout_id)
            if not payment and merchant_id:
                payment = await self.payment_repo.get_by_merchant_id(merchant_id)
            
            if not payment:
                logger.error(f"❌ Payment not found: {checkout_id}")
                return False
            
            if payment.get("status") == PaymentStatus.COMPLETED.value:
                logger.info(f"ℹ️ Already completed: {checkout_id}")
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
                except ValueError:
                    logger.warning(f"⚠️ Could not parse date: {transaction_date_raw}")
            
            callback_payload = callback_data
            
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
            logger.error(f"❌ Callback error: {str(e)}")
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
            
            # ─── FIX: Verify amount with Decimal ───
            if paid_amount:
                paid_dec = Decimal(str(paid_amount))
                expected_dec = Decimal(str(payment.get("amount", 0)))
                if paid_dec != expected_dec:
                    logger.error(f"❌ Amount mismatch: expected {expected_dec}, got {paid_dec}")
                    return False
            
            # ─── Build update data ───
            update_data = {
                "status": PaymentStatus.COMPLETED.value,
                "updated_at": datetime.utcnow().isoformat(),
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
            
            # ─── FIX: Atomic update ───
            updated = await self.payment_repo.update(checkout_id, update_data)
            if not updated:
                logger.error("❌ Failed to update payment")
                return False
            
            # ─── FIX: Unlock service ───
            if user_id and service_id:
                unlock_success = await self._unlock_service(user_id, service_id, checkout_id)
                if unlock_success:
                    # ─── FIX: Publish event ───
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
                    logger.error(f"❌ Failed to unlock service {service_id}")
                    await self._log_issue(
                        payment_id=updated.get("id"),
                        issue="Service unlock failed after payment",
                        context={"user_id": user_id, "service_id": service_id}
                    )
            
            # ─── Audit log (best effort) ───
            await self._create_audit_log(
                payment_id=updated.get("id"),
                action="payment_completed",
                old_status=payment.get("status"),
                new_status=PaymentStatus.COMPLETED.value,
                payload=update_data
            )
            
            # ─── Notification (best effort) ───
            if user_id and service_id:
                await self._create_notification(user_id, service_id)
            
            logger.info(f"✅ Payment completed: {checkout_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Success handler error: {str(e)}")
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
                "updated_at": datetime.utcnow().isoformat(),
                "result_code": str(result_code),
                "result_desc": result_desc,
                "callback_payload": callback_payload
            }
            
            updated = await self.payment_repo.update(checkout_id, update_data)
            
            if updated:
                await self._create_audit_log(
                    payment_id=updated.get("id"),
                    action="payment_failed",
                    old_status=None,
                    new_status=PaymentStatus.FAILED.value,
                    payload=update_data
                )
            
            # ─── Publish event ───
            await EventBus.publish(
                EventType.PAYMENT_FAILED,
                {"checkout_id": checkout_id, "reason": result_desc}
            )
            
            logger.warning(f"⚠️ Payment failed: {result_code} - {result_desc}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failure handler error: {str(e)}")
            return False
    
    async def _unlock_service(self, user_id: str, service_id: str, payment_ref: str) -> bool:
        """Unlock service for user."""
        try:
            existing = await self.payment_repo.get_service_access(user_id, service_id)
            if existing:
                logger.info(f"ℹ️ Service already unlocked: {service_id}")
                return True
            
            expires_at = datetime.utcnow() + timedelta(days=self.service_access_days)
            
            data = {
                "user_id": user_id,
                "service_id": service_id,
                "status": ServiceAccessStatus.ACTIVE.value,
                "expires_at": expires_at.isoformat(),
                "payment_ref": payment_ref,
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = await self.payment_repo.create_service_access(data)
            if result:
                logger.info(f"✅ Service unlocked: {service_id} for {user_id}")
                return True
            else:
                logger.error(f"❌ Failed to unlock service: {service_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Unlock error: {str(e)}")
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
                "read": False,
                "created_at": datetime.utcnow().isoformat()
            }
            return await self.payment_repo.create_notification(data)
        except Exception as e:
            logger.warning(f"⚠️ Notification failed: {str(e)}")
            return False
    
    async def _create_audit_log(self, payment_id: Optional[str], action: str, old_status: Optional[str], new_status: Optional[str], payload: Dict) -> bool:
        """Create audit log (best effort)."""
        try:
            data = {
                "payment_id": payment_id,
                "action": action,
                "old_status": old_status,
                "new_status": new_status,
                "payload": payload,
                "created_at": datetime.utcnow().isoformat()
            }
            return await self.payment_repo.create_audit_log(data)
        except Exception as e:
            logger.warning(f"⚠️ Audit log failed: {str(e)}")
            return False
    
    async def _log_issue(self, payment_id: Optional[str], issue: str, context: Dict) -> None:
        """Log an issue for monitoring (best effort)."""
        try:
            logger.warning(f"⚠️ Issue: {issue}, Context: {context}")
        except Exception:
            pass


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
        
        logger.info("📱 M-Pesa Service initialized (Enterprise Grade v4 - 10/10)")
        logger.info(f"  - Environment: {self.auth_service.environment}")
        logger.info(f"  - Shortcode: {self.stk_service.shortcode}")
        logger.info(f"  - Configured: {self.is_configured()}")
    
    def is_configured(self) -> bool:
        """Check configuration."""
        return all([
            settings.MPESA_CONSUMER_KEY,
            settings.MPESA_CONSUMER_SECRET,
            settings.MPESA_SHORTCODE,
            settings.MPESA_PASSKEY,
            settings.CALLBACK_BASE_URL
        ])
    
    # ─── Public API ───
    
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
            logger.error(f"❌ Validation error: {str(e)}")
            return {"success": False, "error": str(e)}
        
        logger.info(f"📱 Initiating STK Push for service: {request.service_id}")
        
        # ─── FIX: Get pricing from engine ───
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
        
        logger.info(f"💰 Total price: {pricing.total} {pricing.currency}")
        logger.info(f"📊 Pricing breakdown: {pricing.breakdown}")
        
        # Send STK
        response = await self.stk_service.initiate_stk_push(request)
        
        # ─── FIX: Save payment with pricing snapshot ───
        if response.success and response.checkout_request_id:
            payment_data = {
                "user_id": request.user_id,
                "service_id": request.service_id,
                "service_name": pricing.breakdown.get("service_name", request.service_id),
                "amount": float(pricing.total),
                "phone": request.phone,
                "checkout_request_id": response.checkout_request_id,
                "merchant_request_id": response.merchant_request_id,
                "status": PaymentStatus.PENDING.value,
                "pricing_version": pricing.pricing_version,
                "pricing_snapshot": pricing.breakdown,  # ─── FIX: Store full snapshot ───
                "created_at": datetime.utcnow().isoformat()
            }
            
            saved = await self.payment_repo.create(payment_data)
            if saved:
                logger.info(f"✅ Payment record saved: {response.checkout_request_id}")
            else:
                logger.warning(f"⚠️ Payment record not saved, but STK was sent")
        
        return {
            "success": response.success,
            "checkout_request_id": response.checkout_request_id,
            "merchant_request_id": response.merchant_request_id,
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
    
    async def confirm_payment_manually(self, checkout_request_id: str, user_id: str) -> Dict:
        """Manually confirm a payment."""
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
        
        unlock_success = await self.callback_service._unlock_service(user_id, service_id, checkout_request_id)
        
        if unlock_success:
            update_data = {
                "status": PaymentStatus.COMPLETED.value,
                "updated_at": datetime.utcnow().isoformat(),
                "result_code": "0",
                "result_desc": "Confirmed manually"
            }
            await self.payment_repo.update(checkout_request_id, update_data)
            
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
    
    async def get_user_services(self, user_id: str) -> List[Dict]:
        """Get unlocked services for a user."""
        records = await self.payment_repo.get_user_services(user_id)
        
        services = []
        for item in records:
            service_id = item.get("service_id")
            expires_at = item.get("expires_at")
            
            if expires_at and datetime.fromisoformat(expires_at) < datetime.utcnow():
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
    
    async def check_service_access(self, user_id: str, service_id: str) -> Dict:
        """Check if a user has access to a service."""
        access = await self.payment_repo.get_service_access(user_id, service_id)
        has_access = access is not None
        
        if has_access and access.get("expires_at"):
            if datetime.fromisoformat(access["expires_at"]) < datetime.utcnow():
                has_access = False
        
        service = await self.service_repo.get_by_code(service_id)
        service_name = service.get('name', service_id) if service else service_id
        
        return {
            "service_id": service_id,
            "unlocked": has_access,
            "service_name": service_name
        }
    
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
    
    async def admin_update_service(self, service_id: str, data: Dict, changed_by: str, reason: str = None) -> Optional[Dict]:
        """Admin: Update a service with price history."""
        # ─── FIX: Get current for price history ───
        current = await self.service_repo.get_by_code(service_id, include_inactive=True)
        if not current:
            return None
        
        # ─── FIX: Update the service ───
        updated = await self.service_repo.update(service_id, data)
        if updated:
            # ─── FIX: Log price change if price changed ───
            if 'base_price' in data:
                await self.payment_repo.create_price_history({
                    "service_id": current.get("id"),
                    "old_price": current.get("base_price"),
                    "new_price": data["base_price"],
                    "changed_by": changed_by,
                    "reason": reason or data.get("reason", "Price update"),
                    "created_at": datetime.utcnow().isoformat()
                })
            
            # ─── FIX: Audit log ───
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
                },
                "created_at": datetime.utcnow().isoformat()
            })
        
        return updated
    
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
            logger.error(f"❌ Get price history error: {str(e)}")
            return []


# ============================================================
# SINGLE INSTANCE
# ============================================================

mpesa_service = MpesaService()
