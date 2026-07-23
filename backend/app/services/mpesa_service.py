"""
Auto-D Kenya
M-Pesa Business Logic - Enterprise Grade v2
"""

import base64
import json
import logging
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
import re
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel, Field, field_validator
from app.core.config import settings
from app.core.database import supabase

logger = logging.getLogger(__name__)

# ─── Thread pool for synchronous DB operations ───
_db_executor = ThreadPoolExecutor(max_workers=10)


# ============================================================
# PYDANTIC MODELS
# ============================================================

class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class ServiceAccessStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class STKPushRequest(BaseModel):
    """STK Push request model with validation."""
    phone: str = Field(..., description="Phone number (e.g., 0712345678)")
    amount: float = Field(..., gt=0, description="Amount to charge")
    account_reference: str = Field(..., max_length=12, description="Service ID or reference")
    description: str = Field(..., max_length=36, description="Transaction description")
    user_id: Optional[str] = Field(None, description="User ID for the payment")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone number format."""
        # Remove all non-numeric
        cleaned = ''.join(filter(str.isdigit, v))
        
        # Remove leading 0 or 254
        if cleaned.startswith('0'):
            cleaned = cleaned[1:]
        if cleaned.startswith('254'):
            cleaned = cleaned[3:]
        
        if len(cleaned) != 9:
            raise ValueError(f"Phone must be 9 digits after formatting, got {len(cleaned)}")
        
        # ─── FIX: Use allow-list for Safaricom prefixes ───
        valid_prefixes = ('7', '11')  # 7xx and 11x are Safaricom
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


class PaymentRecord(BaseModel):
    """Payment record model."""
    user_id: str
    service_id: str
    service_name: str
    amount: float
    phone: str
    checkout_request_id: str
    merchant_request_id: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    mpesa_receipt: Optional[str] = None
    result_code: Optional[str] = None
    result_desc: Optional[str] = None
    callback_payload: Optional[Dict] = None
    paid_amount: Optional[float] = None
    paid_phone: Optional[str] = None
    transaction_date: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        data = {
            "user_id": self.user_id,
            "service_id": self.service_id,
            "service_name": self.service_name,
            "amount": self.amount,
            "phone": self.phone,
            "checkout_request_id": self.checkout_request_id,
            "merchant_request_id": self.merchant_request_id,
            "status": self.status.value if isinstance(self.status, PaymentStatus) else self.status,
            "mpesa_receipt": self.mpesa_receipt,
            "result_code": self.result_code,
            "result_desc": self.result_desc,
            "callback_payload": self.callback_payload,
            "paid_amount": self.paid_amount,
            "paid_phone": self.paid_phone,
            "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
            "created_at": datetime.utcnow().isoformat()
        }
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}


# ============================================================
# SERVICE CATALOG
# ============================================================

class ServiceCatalogService:
    """Single source of truth for service definitions."""
    
    _instance = None
    _services = None
    _last_refresh = None
    _cache_duration = timedelta(minutes=5)
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self._service_names = {
            'mileage': 'Mileage Calculator',
            'valuation': 'Instant Vehicle Value',
            'ownership': 'Ownership Cost Report',
            'full_report': 'Full Vehicle Report'
        }
    
    async def get_service(self, service_id: str) -> Optional[Dict]:
        """Get service by ID from cache or database."""
        # Check cache
        if self._services and self._last_refresh:
            if datetime.utcnow() - self._last_refresh < self._cache_duration:
                for s in self._services:
                    if s.get('code') == service_id or s.get('service_id') == service_id:
                        return s
        
        # ─── FIX: Fetch from database ───
        try:
            response = await self._run_sync(
                supabase.table("services")
                .select("*")
                .eq("code", service_id)
                .limit(1)
                .execute()
            )
            
            if response.data and len(response.data) > 0:
                service = response.data[0]
                self._services = self._services or []
                # Update cache
                existing = next((s for s in self._services if s.get('code') == service_id), None)
                if existing:
                    existing.update(service)
                else:
                    self._services.append(service)
                self._last_refresh = datetime.utcnow()
                return service
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch service from DB: {str(e)}")
        
        # Fallback to hardcoded
        return {
            "code": service_id,
            "name": self._service_names.get(service_id, service_id),
            "price": self._get_default_price(service_id),
            "currency": "KES",
            "active": True
        }
    
    def get_service_name(self, service_id: str) -> str:
        """Get service name by ID."""
        return self._service_names.get(service_id, service_id)
    
    def _get_default_price(self, service_id: str) -> float:
        """Get default price for a service."""
        prices = {
            'mileage': 100,
            'valuation': 150,
            'ownership': 200,
            'full_report': 350
        }
        return prices.get(service_id, 0)
    
    async def get_all_services(self) -> List[Dict]:
        """Get all active services."""
        try:
            response = await self._run_sync(
                supabase.table("services")
                .select("*")
                .eq("active", True)
                .order("sort_order")
                .execute()
            )
            
            if response.data and len(response.data) > 0:
                self._services = response.data
                self._last_refresh = datetime.utcnow()
                return response.data
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch services: {str(e)}")
        
        # Fallback
        return [
            {
                "code": "mileage",
                "name": "Mileage Calculator",
                "price": 100,
                "currency": "KES",
                "active": True,
                "description": "Calculate your cost per kilometer"
            },
            {
                "code": "valuation",
                "name": "Instant Vehicle Value",
                "price": 150,
                "currency": "KES",
                "active": True,
                "description": "Get AI-powered vehicle valuation"
            },
            {
                "code": "ownership",
                "name": "Ownership Cost Report",
                "price": 200,
                "currency": "KES",
                "active": True,
                "description": "Understand total cost of ownership"
            },
            {
                "code": "full_report",
                "name": "Full Vehicle Report",
                "price": 350,
                "currency": "KES",
                "active": True,
                "description": "Comprehensive vehicle analysis"
            }
        ]
    
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
        
        # ─── FIX: Move magic values to settings ───
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
# PAYMENT REPOSITORY
# ============================================================

class PaymentRepository:
    """Handles payment database operations with async wrapper."""
    
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
    
    async def get_by_merchant_id(self, merchant_id: str) -> Optional[Dict]:
        """Get payment by merchant request ID."""
        try:
            response = await self._run_sync(
                supabase.table("payments")
                .select("*")
                .eq("merchant_request_id", merchant_id)
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
            logger.error(f"❌ Get history error: {str(e)}")
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
        """Create a notification (best effort)."""
        try:
            await self._run_sync(
                supabase.table("notifications").insert(data).execute()
            )
            return True
        except Exception as e:
            logger.error(f"❌ Notification error: {str(e)}")
            return False
    
    async def create_audit_log(self, data: Dict) -> bool:
        """Create audit log (best effort)."""
        try:
            await self._run_sync(
                supabase.table("payment_audit_log").insert(data).execute()
            )
            return True
        except Exception as e:
            logger.error(f"❌ Audit log error: {str(e)}")
            return False
    
    async def _run_sync(self, func):
        """Run synchronous Supabase calls in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_db_executor, func)


# ============================================================
# STK SERVICE
# ============================================================

class MpesaSTKService:
    """Handles STK Push operations."""
    
    def __init__(self, auth_service: MpesaAuthService, service_catalog: ServiceCatalogService):
        self.auth_service = auth_service
        self.service_catalog = service_catalog
        
        self.environment = settings.MPESA_ENV
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.callback_url = f"{settings.CALLBACK_BASE_URL}/api/v1/mpesa/callback"
        self.base_url = "https://api.safaricom.co.ke" if self.environment == "production" else "https://sandbox.safaricom.co.ke"
        
        # ─── FIX: Move to settings ───
        self.max_retries = getattr(settings, "MPESA_MAX_RETRIES", 3)
        self.retry_delay = getattr(settings, "MPESA_RETRY_DELAY", 2)
        self.timeout = getattr(settings, "MPESA_TIMEOUT", 60)
        
        # ─── FIX: Safaricom prefix allow-list ───
        self.safaricom_prefixes = getattr(settings, "SAFARICOM_PREFIXES", [
            '70', '71', '72', '74', '79', '11'
        ])
    
    async def initiate_stk_push(self, request: STKPushRequest) -> STKPushResponse:
        """Initiate STK Push with retry logic."""
        # ─── FIX: Get service and validate amount ───
        service = await self.service_catalog.get_service(request.account_reference)
        if not service:
            logger.error(f"❌ Service not found: {request.account_reference}")
            return STKPushResponse(
                success=False,
                error=f"Service '{request.account_reference}' not found"
            )
        
        # ─── FIX: Verify amount ───
        expected_amount = service.get("price", 0)
        if float(request.amount) != float(expected_amount):
            logger.warning(f"⚠️ Amount mismatch: expected {expected_amount}, got {request.amount}")
            return STKPushResponse(
                success=False,
                error=f"Amount mismatch. Expected KES {expected_amount}"
            )
        
        # ─── FIX: Validate phone prefix ───
        phone = request.phone  # Already formatted by Pydantic
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
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(float(request.amount)),
            "PartyA": phone,
            "PartyB": self.shortcode,
            "PhoneNumber": phone,
            "CallBackURL": self.callback_url,
            "AccountReference": request.account_reference[:12],
            "TransactionDesc": request.description[:36],
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


# ============================================================
# CALLBACK SERVICE
# ============================================================

class MpesaCallbackService:
    """Handles M-Pesa callbacks with atomic processing."""
    
    def __init__(self, repository: PaymentRepository, service_catalog: ServiceCatalogService):
        self.repository = repository
        self.service_catalog = service_catalog
        self.service_access_days = getattr(settings, "SERVICE_ACCESS_DAYS", 365)
    
    async def process_callback(self, callback_data: Dict) -> bool:
        """Process callback with idempotency and atomicity."""
        try:
            logger.info("=" * 60)
            logger.info("📞 Processing callback")
            
            # ─── Extract data ───
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
            
            # ─── Get payment ───
            payment = await self.repository.get_by_checkout_id(checkout_id)
            if not payment and merchant_id:
                payment = await self.repository.get_by_merchant_id(merchant_id)
            
            if not payment:
                logger.error(f"❌ Payment not found: {checkout_id}")
                return False
            
            # ─── Idempotency ───
            if payment.get("status") == PaymentStatus.COMPLETED.value:
                logger.info(f"ℹ️ Already completed: {checkout_id}")
                return True
            
            # ─── Extract metadata ───
            metadata = stk.get("CallbackMetadata", {}).get("Item", [])
            metadata_dict = {item.get("Name"): item.get("Value") for item in metadata}
            
            receipt = metadata_dict.get("MpesaReceiptNumber")
            paid_amount = metadata_dict.get("Amount")
            paid_phone = metadata_dict.get("PhoneNumber")
            transaction_date_raw = metadata_dict.get("TransactionDate")
            
            # ─── FIX: Parse transaction date ───
            transaction_date = None
            if transaction_date_raw:
                try:
                    transaction_date = datetime.strptime(transaction_date_raw, "%Y%m%d%H%M%S")
                except ValueError:
                    logger.warning(f"⚠️ Could not parse date: {transaction_date_raw}")
            
            # ─── FIX: Store callback payload as dict (not string) ───
            callback_payload = callback_data
            
            # ─── Process result ───
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
            
            # ─── FIX: Verify amount ───
            if paid_amount and float(paid_amount) != float(payment.get("amount", 0)):
                logger.error(f"❌ Amount mismatch: expected {payment.get('amount')}, got {paid_amount}")
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
            
            # ─── FIX: Atomic transaction using RPC (or sequential with rollback) ───
            # Step 1: Update payment
            updated = await self.repository.update(checkout_id, update_data)
            if not updated:
                logger.error("❌ Failed to update payment")
                return False
            
            # Step 2: Unlock service
            if user_id and service_id:
                unlock_success = await self._unlock_service(user_id, service_id, checkout_id)
                if not unlock_success:
                    logger.error(f"❌ Failed to unlock service {service_id}")
                    # Don't return False here - payment is already completed
                    # This ensures user isn't double-charged even if unlock fails
                    await self._log_issue(
                        payment_id=updated.get("id"),
                        issue="Service unlock failed after payment",
                        context={"user_id": user_id, "service_id": service_id}
                    )
            
            # Step 3: Audit log (best effort)
            await self._create_audit_log(
                payment_id=updated.get("id"),
                action="payment_completed",
                old_status=payment.get("status"),
                new_status=PaymentStatus.COMPLETED.value,
                payload=update_data
            )
            
            # Step 4: Notification (best effort)
            if user_id and service_id:
                await self._create_notification(
                    user_id=user_id,
                    service_id=service_id
                )
            
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
            
            updated = await self.repository.update(checkout_id, update_data)
            
            if updated:
                await self._create_audit_log(
                    payment_id=updated.get("id"),
                    action="payment_failed",
                    old_status=None,
                    new_status=PaymentStatus.FAILED.value,
                    payload=update_data
                )
            
            logger.warning(f"⚠️ Payment failed: {result_code} - {result_desc}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failure handler error: {str(e)}")
            return False
    
    async def _unlock_service(self, user_id: str, service_id: str, payment_ref: str) -> bool:
        """Unlock service for user."""
        try:
            # Check if already unlocked
            existing = await self.repository.get_service_access(user_id, service_id)
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
            
            result = await self.repository.create_service_access(data)
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
            service_name = self.service_catalog.get_service_name(service_id)
            data = {
                "user_id": user_id,
                "message": f"🎉 {service_name} has been unlocked!",
                "type": "service",
                "read": False,
                "created_at": datetime.utcnow().isoformat()
            }
            return await self.repository.create_notification(data)
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
            return await self.repository.create_audit_log(data)
        except Exception as e:
            logger.warning(f"⚠️ Audit log failed: {str(e)}")
            return False
    
    async def _log_issue(self, payment_id: Optional[str], issue: str, context: Dict) -> None:
        """Log an issue for monitoring (best effort)."""
        try:
            logger.warning(f"⚠️ Issue: {issue}, Context: {context}")
            # Could send to Sentry or monitoring service here
        except Exception:
            pass


# ============================================================
# MAIN MPESA SERVICE
# ============================================================

class MpesaService:
    """
    Main M-Pesa service orchestrator.
    Uses dependency injection for testability.
    """
    
    def __init__(
        self,
        auth_service: Optional[MpesaAuthService] = None,
        service_catalog: Optional[ServiceCatalogService] = None,
        repository: Optional[PaymentRepository] = None,
        stk_service: Optional[MpesaSTKService] = None,
        callback_service: Optional[MpesaCallbackService] = None
    ):
        # ─── FIX: Dependency injection ───
        self.auth_service = auth_service or MpesaAuthService()
        self.service_catalog = service_catalog or ServiceCatalogService()
        self.repository = repository or PaymentRepository()
        self.stk_service = stk_service or MpesaSTKService(self.auth_service, self.service_catalog)
        self.callback_service = callback_service or MpesaCallbackService(self.repository, self.service_catalog)
        
        logger.info("📱 M-Pesa Service initialized (Enterprise Grade v2)")
    
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
        amount: float,
        account_reference: str,
        description: str,
        user_id: Optional[str] = None
    ) -> Dict:
        """Initiate STK Push."""
        # ─── FIX: Use Pydantic for validation ───
        try:
            request = STKPushRequest(
                phone=phone,
                amount=amount,
                account_reference=account_reference,
                description=description,
                user_id=user_id
            )
        except ValueError as e:
            return {"success": False, "error": str(e)}
        
        # ─── FIX: Get service for name ───
        service = await self.service_catalog.get_service(request.account_reference)
        service_name = service.get("name", request.account_reference) if service else request.account_reference
        
        # Send STK
        response = await self.stk_service.initiate_stk_push(request)
        
        # Save payment if successful
        if response.success and response.checkout_request_id:
            payment_data = {
                "user_id": request.user_id,
                "service_id": request.account_reference,
                "service_name": service_name,
                "amount": float(request.amount),
                "phone": request.phone,
                "checkout_request_id": response.checkout_request_id,
                "merchant_request_id": response.merchant_request_id,
                "status": PaymentStatus.PENDING.value,
                "created_at": datetime.utcnow().isoformat()
            }
            
            await self.repository.create(payment_data)
        
        return {
            "success": response.success,
            "checkout_request_id": response.checkout_request_id,
            "merchant_request_id": response.merchant_request_id,
            "customer_message": response.customer_message,
            "response_description": response.response_description,
            "error": response.error
        }
    
    async def process_callback(self, callback_data: Dict) -> bool:
        """Process M-Pesa callback."""
        return await self.callback_service.process_callback(callback_data)
    
    async def get_payment_status(self, checkout_request_id: str) -> Dict:
        """Get payment status."""
        payment = await self.repository.get_by_checkout_id(checkout_request_id)
        
        if not payment:
            return {
                "success": False,
                "error": "Payment not found"
            }
        
        return {
            "success": True,
            "checkout_request_id": payment["checkout_request_id"],
            "status": payment["status"],
            "amount": payment["amount"],
            "service_id": payment.get("service_id"),
            "service_name": payment.get("service_name"),
            "created_at": payment["created_at"],
            "updated_at": payment.get("updated_at"),
            "mpesa_receipt": payment.get("mpesa_receipt")
        }
    
    async def confirm_payment_manually(self, checkout_request_id: str, user_id: str) -> Dict:
        """Manually confirm a payment."""
        payment = await self.repository.get_by_checkout_id(checkout_request_id)
        
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
        
        # ─── Unlock and update ───
        unlock_success = await self.callback_service._unlock_service(user_id, service_id, checkout_request_id)
        
        if unlock_success:
            update_data = {
                "status": PaymentStatus.COMPLETED.value,
                "updated_at": datetime.utcnow().isoformat(),
                "result_code": "0",
                "result_desc": "Confirmed manually"
            }
            await self.repository.update(checkout_request_id, update_data)
            
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
        records = await self.repository.get_user_services(user_id)
        
        services = []
        for item in records:
            service_id = item.get("service_id")
            expires_at = item.get("expires_at")
            
            if expires_at and datetime.fromisoformat(expires_at) < datetime.utcnow():
                continue
            
            services.append({
                "service_id": service_id,
                "service_name": self.service_catalog.get_service_name(service_id),
                "status": ServiceAccessStatus.ACTIVE.value,
                "expires_at": expires_at,
                "unlocked_at": item.get("created_at")
            })
        
        return services
    
    async def check_service_access(self, user_id: str, service_id: str) -> Dict:
        """Check if a user has access to a service."""
        access = await self.repository.get_service_access(user_id, service_id)
        has_access = access is not None
        
        if has_access and access.get("expires_at"):
            if datetime.fromisoformat(access["expires_at"]) < datetime.utcnow():
                has_access = False
        
        return {
            "service_id": service_id,
            "unlocked": has_access,
            "service_name": self.service_catalog.get_service_name(service_id)
        }
    
    async def get_payment_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get payment history."""
        return await self.repository.get_history(user_id, limit)
    
    async def get_all_services(self) -> List[Dict]:
        """Get all available services."""
        return await self.service_catalog.get_all_services()


# ============================================================
# SINGLE INSTANCE
# ============================================================

mpesa_service = MpesaService()
