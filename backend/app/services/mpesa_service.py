"""
M-Pesa Service - Enterprise Grade
3 Services: mileage (100), valuation (150), ownership (200)
ALL FIXES APPLIED
"""

import base64
import json
import logging
import asyncio
import httpx
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, List, Set
from enum import Enum
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
import uuid

from pydantic import BaseModel, Field, field_validator
from app.core.config import settings
from app.core.database import supabase

logger = logging.getLogger(__name__)
_db_executor = ThreadPoolExecutor(max_workers=10)


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class STKPushRequest(BaseModel):
    phone: str
    service_id: str
    description: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = ''.join(filter(str.isdigit, v))
        if cleaned.startswith('0'):
            cleaned = cleaned[1:]
        if cleaned.startswith('254'):
            cleaned = cleaned[3:]
        if len(cleaned) != 9:
            raise ValueError("Phone must be 9 digits")
        if not cleaned.startswith(('7', '11')):
            raise ValueError("Invalid Safaricom prefix")
        return f"254{cleaned}"

    @field_validator('service_id')
    @classmethod
    def validate_service_id(cls, v: str) -> str:
        return v.strip().lower()


class ServiceRepository:
    """Service database operations - converts between code and ID."""
    
    async def _run_sync(self, operation):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_db_executor, operation)

    async def get_by_code(self, code: str) -> Optional[Dict]:
        """Get service by code (e.g., 'mileage')."""
        try:
            code = code.strip().lower()
            logger.info(f"🔍 [SERVICE] Looking up by code: '{code}'")

            response = await self._run_sync(
                lambda: supabase.table("services")
                .select("*")
                .eq("code", code)
                .eq("active", True)
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.warning(f"❌ [SERVICE] Not found by code: '{code}'")
                all_services = await self._run_sync(
                    lambda: supabase.table("services")
                    .select("id, code, name, price, active")
                    .execute()
                )
                logger.info(f"📋 Available services: {[s.get('code') for s in (all_services.data or [])]}")
                return None

            row = response.data[0]
            logger.info(f"✅ [SERVICE] Found by code: {row.get('code')} (id={row.get('id')}) = {row.get('price')} KES")
            
            return {
                "id": row.get("id"),
                "code": row.get("code"),
                "name": row.get("name"),
                "price": Decimal(str(row.get("price", 0))),
                "currency": row.get("currency", "KES"),
                "active": row.get("active", True),
            }

        except Exception as e:
            logger.exception(f"❌ [SERVICE] Lookup by code error: {code}")
            raise

    async def get_by_id(self, service_id: int) -> Optional[Dict]:
        """Get service by integer ID."""
        try:
            if not isinstance(service_id, int):
                raise ValueError(f"service_id must be int, got {type(service_id)}: {service_id}")
            
            logger.info(f"🔍 [SERVICE] Looking up by ID: {service_id}")

            response = await self._run_sync(
                lambda: supabase.table("services")
                .select("*")
                .eq("id", service_id)
                .eq("active", True)
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.warning(f"❌ [SERVICE] Not found by ID: {service_id}")
                return None

            row = response.data[0]
            logger.info(f"✅ [SERVICE] Found by ID: {row.get('id')} = {row.get('code')} ({row.get('price')} KES)")
            
            return {
                "id": row.get("id"),
                "code": row.get("code"),
                "name": row.get("name"),
                "price": Decimal(str(row.get("price", 0))),
                "currency": row.get("currency", "KES"),
                "active": row.get("active", True),
            }

        except Exception as e:
            logger.exception(f"❌ [SERVICE] Lookup by ID error: {service_id}")
            raise

    async def get_all(self, include_inactive: bool = False) -> List[Dict]:
        """Get all services."""
        try:
            query = supabase.table("services").select("*")
            if not include_inactive:
                query = query.eq("active", True)
            
            response = await self._run_sync(
                lambda: query.order("display_order").execute()
            )
            
            services = response.data or []
            logger.info(f"📋 [SERVICE] Loaded {len(services)} services")
            for s in services:
                logger.info(f"   ✅ {s.get('id')}: {s.get('code')} = {s.get('price')} KES (active: {s.get('active')})")
            return services
            
        except Exception as e:
            logger.exception("❌ [SERVICE] Get all error")
            raise


class PaymentRepository:
    """Payment database operations."""
    
    ALLOWED_PAYMENT_COLUMNS: Set[str] = {
        "id", "user_id", "request_id", "service_id", "service_name",
        "amount", "currency", "phone", "checkout_request_id",
        "merchant_request_id", "status", "result_code", "result_desc",
        "mpesa_receipt", "paid_amount", "paid_phone", "transaction_date",
        "callback_payload", "created_at", "updated_at",
    }
    
    async def _run_sync(self, operation):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_db_executor, operation)

    async def create(self, data: Dict) -> Dict:
        """Create a payment record with validation."""
        try:
            invalid = set(data.keys()) - self.ALLOWED_PAYMENT_COLUMNS
            if invalid:
                raise ValueError(f"Unknown columns for payments table: {invalid}")
            
            logger.info("📝 [PAYMENT] Data being inserted:")
            logger.info(json.dumps(data, default=str, indent=2))
            
            if 'id' not in data:
                data['id'] = str(uuid.uuid4())
            data['created_at'] = datetime.now(UTC).isoformat()
            data['updated_at'] = datetime.now(UTC).isoformat()

            response = await self._run_sync(
                lambda: supabase.table("payments").insert(data).execute()
            )
            
            if not response.data:
                raise Exception("Insert succeeded but no data returned")
            
            logger.info(f"✅ [PAYMENT] Created: {response.data[0].get('id')}")
            return response.data[0]
            
        except Exception as e:
            logger.exception(f"❌ [PAYMENT] Create error")
            raise

    async def get_by_checkout_id(self, checkout_id: str) -> Optional[Dict]:
        try:
            logger.info(f"🔍 [PAYMENT] Looking up by checkout_id: {checkout_id}")
            response = await self._run_sync(
                lambda: supabase.table("payments")
                .select("*")
                .eq("checkout_request_id", checkout_id)
                .limit(1)
                .execute()
            )
            
            if response.data:
                logger.info(f"✅ [PAYMENT] Found: {response.data[0].get('id')}")
                return response.data[0]
            
            logger.warning(f"❌ [PAYMENT] Not found: {checkout_id}")
            return None
            
        except Exception as e:
            logger.exception(f"❌ [PAYMENT] Get by checkout_id error: {checkout_id}")
            raise

    async def update_with_lock(self, checkout_id: str, data: Dict, expected_status: str = "pending") -> Optional[Dict]:
        """Update payment with optimistic locking."""
        try:
            logger.info(f"🔄 [PAYMENT] Updating {checkout_id} with lock (expected: {expected_status})")
            data['updated_at'] = datetime.now(UTC).isoformat()
            
            response = await self._run_sync(
                lambda: supabase.table("payments")
                .update(data)
                .eq("checkout_request_id", checkout_id)
                .eq("status", expected_status)
                .execute()
            )

            if response.data:
                logger.info(f"✅ [PAYMENT] Updated: {checkout_id}")
                return response.data[0]
            
            logger.warning(f"⚠️ [PAYMENT] Update failed (optimistic lock) for {checkout_id}")
            return None
            
        except Exception as e:
            logger.exception(f"❌ [PAYMENT] Update error: {checkout_id}")
            raise

    async def get_user_payments(self, user_id: str, limit: int = 50) -> List[Dict]:
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
            logger.exception(f"❌ [PAYMENT] Get user payments error")
            raise

    async def create_service_access(self, data: Dict) -> Dict:
        """Create service access record."""
        try:
            user_id = data.get("user_id")
            service_id = data.get("service_id")
            
            if user_id and service_id:
                existing = await self.check_service_access_by_id(user_id, service_id)
                if existing:
                    logger.info(f"ℹ️ [ACCESS] Service already unlocked: {service_id}")
                    return existing
            
            data['id'] = str(uuid.uuid4())
            data['created_at'] = datetime.now(UTC).isoformat()
            
            logger.info(f"🔓 [ACCESS] Creating: user={user_id}, service_id={service_id}")
            
            response = await self._run_sync(
                lambda: supabase.table("service_access").insert(data).execute()
            )
            
            if not response.data:
                raise Exception("Insert succeeded but no data returned")
            
            logger.info(f"✅ [ACCESS] Created: {response.data[0].get('id')}")
            return response.data[0]
            
        except Exception as e:
            logger.exception(f"❌ [ACCESS] Create error")
            raise

    async def get_user_service_access(self, user_id: str) -> List[Dict]:
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
            logger.exception(f"❌ [ACCESS] Get user access error")
            raise

    async def check_service_access_by_id(self, user_id: str, service_id: int) -> Optional[Dict]:
        """Check access using INTEGER service ID."""
        try:
            logger.info(f"🔍 [ACCESS] Checking: user={user_id}, service_id={service_id}")
            
            response = await self._run_sync(
                lambda: supabase.table("service_access")
                .select("*")
                .eq("user_id", user_id)
                .eq("service_id", service_id)
                .eq("status", "active")
                .limit(1)
                .execute()
            )
            
            if response.data:
                logger.info(f"✅ [ACCESS] Found existing access")
                return response.data[0]
            
            logger.info(f"ℹ️ [ACCESS] No existing access found")
            return None
            
        except Exception as e:
            logger.exception(f"❌ [ACCESS] Check error")
            raise

    async def update_request_status(self, request_id: str, status: str) -> bool:
        try:
            logger.info(f"🔄 [REQUEST] Updating {request_id} to {status}")
            
            response = await self._run_sync(
                lambda: supabase.table("requests")
                .update({"status": status, "updated_at": datetime.now(UTC).isoformat()})
                .eq("id", request_id)
                .execute()
            )
            
            if response.data:
                logger.info(f"✅ [REQUEST] Updated: {request_id} → {status}")
                return True
            
            logger.warning(f"⚠️ [REQUEST] Not found: {request_id}")
            return False
            
        except Exception as e:
            logger.exception(f"❌ [REQUEST] Update error: {request_id}")
            raise


class MpesaAuthService:
    def __init__(self):
        self.environment = settings.MPESA_ENV
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.base_url = "https://api.safaricom.co.ke" if self.environment == "production" else "https://sandbox.safaricom.co.ke"
        self._cached_token = None
        self._token_expiry = None
        self._lock = asyncio.Lock()

    async def get_access_token(self) -> str:
        async with self._lock:
            if self._cached_token and self._token_expiry and datetime.now(UTC) < self._token_expiry:
                logger.debug("🔑 Using cached token")
                return self._cached_token

            try:
                logger.info("🔑 Refreshing access token")
                auth = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
                headers = {"Authorization": f"Basic {auth}"}
                url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"

                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    token = data.get("access_token")

                    if not token:
                        raise Exception("No access_token in response")

                    self._cached_token = token
                    self._token_expiry = datetime.now(UTC) + timedelta(minutes=50)
                    logger.info("✅ Token cached")
                    return token
                    
            except Exception as e:
                logger.exception("❌ Token error")
                raise


class MpesaSTKService:
    def __init__(self, auth_service: MpesaAuthService):
        self.auth_service = auth_service
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.callback_url = f"{settings.CALLBACK_BASE_URL}/api/v1/mpesa/callback"
        self.base_url = "https://api.safaricom.co.ke" if settings.MPESA_ENV == "production" else "https://sandbox.safaricom.co.ke"

    async def initiate(self, phone: str, amount: float, account_ref: str, desc: str) -> Dict:
        try:
            logger.info(f"📱 [STK] Initiating: amount={amount}, ref={account_ref}")
            
            token = await self.auth_service.get_access_token()
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            password = base64.b64encode(f"{self.shortcode}{self.passkey}{timestamp}".encode()).decode()

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
                "AccountReference": account_ref[:12],
                "TransactionDesc": desc[:36],
            }

            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"

            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                if data.get("ResponseCode") != "0":
                    logger.error(f"❌ [STK] Error: {data.get('ResponseDescription')}")
                    raise Exception(f"STK Push failed: {data.get('ResponseDescription')}")

                logger.info(f"✅ [STK] Initiated: {data.get('CheckoutRequestID')}")
                return {
                    "checkout_request_id": data.get("CheckoutRequestID"),
                    "merchant_request_id": data.get("MerchantRequestID"),
                    "customer_message": data.get("CustomerMessage"),
                }

        except Exception as e:
            logger.exception("❌ [STK] Initiate error")
            raise


class MpesaService:
    def __init__(self):
        self._verify_settings()
        
        self.service_repo = ServiceRepository()
        self.payment_repo = PaymentRepository()
        self.auth_service = MpesaAuthService()
        self.stk_service = MpesaSTKService(self.auth_service)

        logger.info("=" * 60)
        logger.info("🚗 M-Pesa Service Initialized")
        logger.info(f"   Environment: {settings.MPESA_ENV}")
        logger.info(f"   Shortcode: {settings.MPESA_SHORTCODE}")
        
        self._verify_services_sync()

    def _verify_settings(self):
        required = {
            "MPESA_CONSUMER_KEY": settings.MPESA_CONSUMER_KEY,
            "MPESA_CONSUMER_SECRET": settings.MPESA_CONSUMER_SECRET,
            "MPESA_SHORTCODE": settings.MPESA_SHORTCODE,
            "MPESA_PASSKEY": settings.MPESA_PASSKEY,
            "CALLBACK_BASE_URL": settings.CALLBACK_BASE_URL,
            "SUPABASE_URL": settings.SUPABASE_URL,
            "SUPABASE_KEY": settings.SUPABASE_KEY,
        }
        
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise RuntimeError(f"Missing required settings: {', '.join(missing)}")
        
        logger.info("✅ All required settings verified")

    def _verify_services_sync(self):
        try:
            response = supabase.table("services").select("id, code, name, price, active").execute()
            services = response.data or []
            
            if not services:
                raise RuntimeError("No active services configured in database!")
            
            logger.info("📋 Services Available:")
            for s in services:
                logger.info(f"   ✅ {s.get('id')}: {s.get('code')} = {s.get('price')} KES")
                
            expected = ["mileage", "valuation", "ownership"]
            found = [s.get('code') for s in services]
            missing = [e for e in expected if e not in found]
            if missing:
                logger.warning(f"⚠️ Missing expected services: {missing}")
                
        except Exception as e:
            logger.error(f"❌ Service verification failed: {e}")
            raise

    async def get_services(self) -> List[Dict]:
        return await self.service_repo.get_all()

    async def get_service_by_code(self, service_code: str) -> Optional[Dict]:
        return await self.service_repo.get_by_code(service_code)

    async def get_service_by_id(self, service_id: int) -> Optional[Dict]:
        return await self.service_repo.get_by_id(service_id)

    async def initiate_payment(
        self, 
        phone: str, 
        service_code: str, 
        description: Optional[str] = None,
        user_id: Optional[str] = None, 
        request_id: Optional[str] = None
    ) -> Dict:
        try:
            request = STKPushRequest(
                phone=phone,
                service_id=service_code,
                description=description,
                user_id=user_id,
                request_id=request_id
            )
            
            logger.info("=" * 60)
            logger.info("💰 [PAYMENT] Initiating payment")
            logger.info(f"   Phone: {request.phone}")
            logger.info(f"   Service: {request.service_id}")
            logger.info(f"   User: {request.user_id}")
            logger.info(f"   Request: {request.request_id}")

            service = await self.service_repo.get_by_code(request.service_id)
            if not service:
                raise Exception(f"Service '{request.service_id}' not found")

            service_id = service.get("id")
            amount = float(service["price"])
            
            if not isinstance(service_id, int):
                raise ValueError(f"service_id must be int, got {type(service_id)}")
            
            if amount <= 0:
                raise Exception(f"Invalid price for '{request.service_id}': {amount}")
            
            logger.info(f"✅ Service found: {service.get('name')} (ID: {service_id}) = {amount} KES")

            stk_result = await self.stk_service.initiate(
                phone=request.phone,
                amount=amount,
                account_ref=request.service_id,
                desc=description or service.get("name", request.service_id)
            )

            checkout_id = stk_result.get("checkout_request_id")
            logger.info(f"✅ STK Push sent: {checkout_id}")

            payment_data = {
                "user_id": request.user_id,
                "service_id": service_id,
                "service_name": service.get("name"),
                "amount": amount,
                "currency": service.get("currency", "KES"),
                "phone": request.phone,
                "checkout_request_id": checkout_id,
                "merchant_request_id": stk_result.get("merchant_request_id"),
                "status": PaymentStatus.PENDING.value,
                "request_id": request.request_id,
            }

            saved = await self.payment_repo.create(payment_data)
            logger.info(f"✅ Payment record created: {saved.get('id')}")

            return {
                "success": True,
                "checkout_request_id": checkout_id,
                "merchant_request_id": stk_result.get("merchant_request_id"),
                "customer_message": stk_result.get("customer_message"),
                "service_name": service.get("name"),
                "amount": amount,
                "currency": service.get("currency", "KES"),
            }

        except Exception as e:
            logger.exception("❌ [PAYMENT] Initiate error")
            return {"success": False, "error": str(e)}

    async def process_callback(self, callback_data: Dict) -> bool:
        try:
            logger.info("=" * 60)
            logger.info("📞 [CALLBACK] Received")

            stk = callback_data.get("Body", {}).get("stkCallback", {})
            checkout_id = stk.get("CheckoutRequestID")
            result_code = stk.get("ResultCode")
            result_desc = stk.get("ResultDesc", "")

            logger.info(f"   Checkout ID: {checkout_id}")
            logger.info(f"   Result Code: {result_code}")
            logger.info(f"   Result Desc: {result_desc}")

            if not checkout_id:
                raise Exception("No CheckoutRequestID in callback")

            payment = await self.payment_repo.get_by_checkout_id(checkout_id)
            if not payment:
                raise Exception(f"Payment not found for checkout_id: {checkout_id}")

            logger.info(f"   Payment ID: {payment.get('id')}")
            logger.info(f"   Current Status: {payment.get('status')}")

            if payment.get("status") == PaymentStatus.COMPLETED.value:
                logger.info(f"✅ Payment already completed: {checkout_id}")
                return True

            if result_code == "0":
                return await self._handle_success(payment, checkout_id, stk)
            else:
                return await self._handle_failure(checkout_id, result_code, result_desc)

        except Exception as e:
            logger.exception("❌ [CALLBACK] Error")
            return False

    async def _handle_success(self, payment: Dict, checkout_id: str, stk: Dict) -> bool:
        try:
            logger.info("✅ [CALLBACK] Processing success")
            
            metadata = stk.get("CallbackMetadata", {}).get("Item", [])
            meta = {item.get("Name"): item.get("Value") for item in metadata}

            receipt = meta.get("MpesaReceiptNumber")
            amount = float(meta.get("Amount", 0))
            phone = meta.get("PhoneNumber")
            
            logger.info(f"   Receipt: {receipt}")
            logger.info(f"   Amount: {amount}")
            logger.info(f"   Phone: {phone}")

            update_data = {
                "status": PaymentStatus.COMPLETED.value,
                "updated_at": datetime.now(UTC).isoformat(),
                "mpesa_receipt": receipt,
                "paid_amount": amount,
                "paid_phone": phone,
                "result_code": "0",
                "result_desc": "Payment successful",
                "transaction_date": datetime.now(UTC).isoformat(),
                "callback_payload": stk,
            }

            updated = await self.payment_repo.update_with_lock(checkout_id, update_data)
            if not updated:
                logger.warning(f"⚠️ Payment already processed: {checkout_id}")
                return True

            logger.info(f"✅ Payment updated: {checkout_id}")

            user_id = payment.get("user_id")
            service_id = payment.get("service_id")

            if user_id and service_id:
                try:
                    service = await self.service_repo.get_by_id(service_id)
                    if not service:
                        raise Exception(f"Service with ID {service_id} not found")
                    
                    expires_at = datetime.now(UTC) + timedelta(days=365)
                    await self.payment_repo.create_service_access({
                        "user_id": user_id,
                        "service_id": service_id,
                        "status": "active",
                        "expires_at": expires_at.isoformat(),
                        "payment_ref": checkout_id,
                    })
                    
                    logger.info(f"🔓 Service unlocked: {service.get('code')} (ID: {service_id})")
                except Exception as e:
                    logger.error(f"❌ Failed to unlock service: {e}")

            request_id = payment.get("request_id")
            if request_id:
                try:
                    await self.payment_repo.update_request_status(request_id, "paid")
                    logger.info(f"✅ Request updated: {request_id} → paid")
                except Exception as e:
                    logger.error(f"❌ Failed to update request: {e}")

            logger.info(f"✅ Payment completed successfully: {checkout_id}")
            return True

        except Exception as e:
            logger.exception("❌ [CALLBACK] Success handler error")
            return False

    async def _handle_failure(self, checkout_id: str, result_code: str, result_desc: str) -> bool:
        try:
            logger.warning(f"❌ [CALLBACK] Processing failure: {result_code} - {result_desc}")
            
            update_data = {
                "status": PaymentStatus.FAILED.value,
                "updated_at": datetime.now(UTC).isoformat(),
                "result_code": str(result_code),
                "result_desc": result_desc,
                "callback_payload": {"result_code": result_code, "result_desc": result_desc},
            }
            
            updated = await self.payment_repo.update_with_lock(checkout_id, update_data)
            if updated:
                logger.info(f"✅ Payment marked as failed: {checkout_id}")
            else:
                logger.warning(f"⚠️ Could not update payment: {checkout_id}")
            
            return True
            
        except Exception as e:
            logger.exception("❌ [CALLBACK] Failure handler error")
            return False

    async def get_payment_status(self, checkout_id: str) -> Dict:
        try:
            payment = await self.payment_repo.get_by_checkout_id(checkout_id)
            if not payment:
                return {"success": False, "error": "Payment not found"}
            
            service_id = payment.get("service_id")
            service_code = None
            if service_id:
                service = await self.service_repo.get_by_id(service_id)
                if service:
                    service_code = service.get("code")
            
            return {
                "success": True,
                "checkout_request_id": payment.get("checkout_request_id"),
                "status": payment.get("status"),
                "amount": payment.get("amount"),
                "service_id": service_code,
                "service_name": payment.get("service_name"),
                "mpesa_receipt": payment.get("mpesa_receipt"),
                "created_at": payment.get("created_at"),
            }
            
        except Exception as e:
            logger.exception("❌ Get payment status error")
            return {"success": False, "error": str(e)}

    async def get_user_services(self, user_id: str) -> List[Dict]:
        try:
            records = await self.payment_repo.get_user_service_access(user_id)
            services = []
            
            for record in records:
                service_id = record.get("service_id")
                service = await self.service_repo.get_by_id(service_id)
                if service:
                    services.append({
                        "service_id": service.get("code"),
                        "service_name": service.get("name"),
                        "status": record.get("status"),
                        "expires_at": record.get("expires_at"),
                    })
            
            return services
            
        except Exception as e:
            logger.exception("❌ Get user services error")
            return []

    async def check_service_access(self, user_id: str, service_code: str) -> Dict:
        try:
            service = await self.service_repo.get_by_code(service_code)
            if not service:
                return {
                    "service_id": service_code,
                    "unlocked": False,
                    "error": "Service not found"
                }
            
            service_id = service.get("id")
            access = await self.payment_repo.check_service_access_by_id(user_id, service_id)
            
            if access:
                return {
                    "service_id": service_code,
                    "unlocked": True,
                    "status": access.get("status"),
                    "expires_at": access.get("expires_at"),
                }
            
            return {
                "service_id": service_code,
                "unlocked": False,
            }
            
        except Exception as e:
            logger.exception("❌ Check service access error")
            return {"service_id": service_code, "unlocked": False, "error": str(e)}

    async def get_payment_history(self, user_id: str) -> List[Dict]:
        try:
            payments = await self.payment_repo.get_user_payments(user_id)
            
            for payment in payments:
                service_id = payment.get("service_id")
                if service_id:
                    service = await self.service_repo.get_by_id(service_id)
                    if service:
                        payment["service_code"] = service.get("code")
            
            return payments
            
        except Exception as e:
            logger.exception("❌ Get payment history error")
            return []

    # ─── Admin Methods ───

    async def admin_get_service(self, service_id: int) -> Optional[Dict]:
        return await self.service_repo.get_by_id(service_id)

    async def admin_get_all_services(self, include_inactive: bool = False) -> List[Dict]:
        return await self.service_repo.get_all(include_inactive)

    async def admin_update_service(self, service_id: int, data: Dict, changed_by: str) -> Optional[Dict]:
        try:
            current = await self.service_repo.get_by_id(service_id)
            if not current:
                logger.error(f"Service with ID {service_id} not found")
                return None

            data['updated_at'] = datetime.now(UTC).isoformat()
            
            response = await self.service_repo._run_sync(
                lambda: supabase.table("services")
                .update(data)
                .eq("id", service_id)
                .execute()
            )
            
            if response.data:
                logger.info(f"✅ Service {service_id} updated by {changed_by}")
                return response.data[0]
            return None

        except Exception as e:
            logger.exception(f"❌ Admin update service error: {service_id}")
            return None

    async def admin_delete_service(self, service_id: int, deleted_by: str) -> bool:
        try:
            data = {
                "active": False,
                "deleted_at": datetime.now(UTC).isoformat(),
                "deleted_by": deleted_by
            }
            response = await self.service_repo._run_sync(
                lambda: supabase.table("services")
                .update(data)
                .eq("id", service_id)
                .execute()
            )
            if response.data:
                logger.info(f"🗑️ Service {service_id} deleted by {deleted_by}")
                return True
            return False

        except Exception as e:
            logger.exception(f"❌ Admin delete service error: {service_id}")
            return False

    async def admin_restore_service(self, service_id: int) -> bool:
        try:
            data = {
                "active": True,
                "deleted_at": None,
                "deleted_by": None
            }
            response = await self.service_repo._run_sync(
                lambda: supabase.table("services")
                .update(data)
                .eq("id", service_id)
                .execute()
            )
            return bool(response.data)

        except Exception as e:
            logger.exception(f"❌ Admin restore service error: {service_id}")
            return False

    async def admin_get_price_history(self, service_id: int) -> List[Dict]:
        try:
            service = await self.service_repo.get_by_id(service_id)
            if not service:
                return []

            response = await self.service_repo._run_sync(
                lambda: supabase.table("service_price_history")
                .select("*")
                .eq("service_id", service_id)
                .order("created_at", desc=True)
                .execute()
            )
            return response.data or []

        except Exception as e:
            logger.exception(f"❌ Admin get price history error: {service_id}")
            return []

    async def expire_stale_payments(self, minutes: int = 30) -> int:
        try:
            cutoff = (datetime.now(UTC) - timedelta(minutes=minutes)).isoformat()

            response = await self.payment_repo._run_sync(
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
            logger.exception(f"❌ Expire stale payments error")
            return 0


mpesa_service = MpesaService()
