"""
import base64
import json
import logging
import asyncio
import httpx
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, List
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
    service_id: str  # This is the CODE (e.g., "mileage") from frontend
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
        """
        Get service by code (e.g., 'mileage') from services table.
        Used by: Frontend API calls (they send codes).
        """
        try:
            code = code.strip().lower()
            logger.info(f"🔍 Looking for service by code: '{code}'")

            response = await self._run_sync(
                lambda: supabase.table("services")
                .select("*")
                .eq("code", code)
                .eq("active", True)
                .limit(1)
                .execute()
            )

            if not response.data:
                # Log all available services for debugging
                all_services = await self._run_sync(
                    lambda: supabase.table("services")
                    .select("id, code, name, price, active")
                    .execute()
                )
                logger.info(f"📋 Available services: {[s.get('code') for s in (all_services.data or [])]}")
                return None

            row = response.data[0]
            logger.info(f"✅ Found by code: {row.get('code')} (id={row.get('id')}) = {row.get('price')} KES")
            
            return {
                "id": row.get("id"),           # INTEGER
                "code": row.get("code"),
                "name": row.get("name"),
                "price": Decimal(str(row.get("price", 0))),
                "currency": row.get("currency", "KES"),
                "active": row.get("active", True),
                "version": row.get("version", 1),
            }

        except Exception as e:
            logger.exception(f"Service lookup by code error: {code}")
            return None

    async def get_by_id(self, service_id: int) -> Optional[Dict]:
        """
        Get service by integer ID from services table.
        Used by: Callback processing (payments store integer IDs).
        """
        try:
            logger.info(f"🔍 Looking for service by ID: {service_id}")

            response = await self._run_sync(
                lambda: supabase.table("services")
                .select("*")
                .eq("id", service_id)
                .eq("active", True)
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.warning(f"Service with ID {service_id} not found")
                return None

            row = response.data[0]
            logger.info(f"✅ Found by ID: {row.get('id')} = {row.get('code')} ({row.get('price')} KES)")
            
            return {
                "id": row.get("id"),           # INTEGER
                "code": row.get("code"),
                "name": row.get("name"),
                "price": Decimal(str(row.get("price", 0))),
                "currency": row.get("currency", "KES"),
                "active": row.get("active", True),
                "version": row.get("version", 1),
            }

        except Exception as e:
            logger.exception(f"Service lookup by ID error: {service_id}")
            return None

    async def get_all(self) -> List[Dict]:
        """Get all active services."""
        try:
            response = await self._run_sync(
                lambda: supabase.table("services")
                .select("*")
                .eq("active", True)
                .order("display_order")
                .execute()
            )
            services = response.data or []
            logger.info(f"📋 Loaded {len(services)} services")
            for s in services:
                logger.info(f"   ✅ {s.get('id')}: {s.get('code')} = {s.get('price')} KES")
            return services
        except Exception as e:
            logger.exception("Get all services error")
            return []

    async def get_service_with_price(self, code: str) -> Optional[Dict]:
        """Get service by code with price validation."""
        service = await self.get_by_code(code)
        if not service:
            return None
        if Decimal(str(service["price"])) <= 0:
            logger.error(f"Invalid price for {code}: {service['price']}")
            return None
        return service


class PaymentRepository:
    async def _run_sync(self, operation):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_db_executor, operation)

    async def create(self, data: Dict) -> Optional[Dict]:
        try:
            if 'id' not in data:
                data['id'] = str(uuid.uuid4())
            data['created_at'] = datetime.now(UTC).isoformat()
            data['updated_at'] = datetime.now(UTC).isoformat()

            # Log exactly what's being inserted
            logger.info("📝 PAYMENT DATA BEING INSERTED:")
            logger.info(json.dumps(data, default=str, indent=2))

            response = await self._run_sync(
                lambda: supabase.table("payments").insert(data).execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.exception(f"Create payment error: {e}")
            return None

    async def get_by_checkout_id(self, checkout_id: str) -> Optional[Dict]:
        try:
            response = await self._run_sync(
                lambda: supabase.table("payments")
                .select("*")
                .eq("checkout_request_id", checkout_id)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.exception(f"Get payment error: {checkout_id}")
            return None

    async def update_with_lock(self, checkout_id: str, data: Dict, expected_status: str = "pending") -> Optional[Dict]:
        try:
            data['updated_at'] = datetime.now(UTC).isoformat()
            response = await self._run_sync(
                lambda: supabase.table("payments")
                .update(data)
                .eq("checkout_request_id", checkout_id)
                .eq("status", expected_status)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.exception(f"Update payment error: {checkout_id}")
            return None

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
            logger.exception("Get user payments error")
            return []

    async def create_service_access(self, data: Dict) -> Optional[Dict]:
        """Create service access record with INTEGER service_id."""
        try:
            data['id'] = str(uuid.uuid4())
            data['created_at'] = datetime.now(UTC).isoformat()
            
            logger.info(f"🔓 Creating service_access: service_id={data.get('service_id')} (INTEGER)")
            
            response = await self._run_sync(
                lambda: supabase.table("service_access").insert(data).execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.exception("Create service access error")
            return None

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
            logger.exception("Get user service access error")
            return []

    async def check_service_access_by_id(self, user_id: str, service_id: int) -> Optional[Dict]:
        """Check access using INTEGER service ID."""
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
            logger.exception("Check service access error")
            return None

    async def update_request_status(self, request_id: str, status: str) -> bool:
        try:
            response = await self._run_sync(
                lambda: supabase.table("requests")
                .update({"status": status, "updated_at": datetime.now(UTC).isoformat()})
                .eq("id", request_id)
                .execute()
            )
            return bool(response.data)
        except Exception as e:
            logger.exception(f"Update request status error: {request_id}")
            return False


class MpesaAuthService:
    def __init__(self):
        self.environment = settings.MPESA_ENV
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.base_url = "https://api.safaricom.co.ke" if self.environment == "production" else "https://sandbox.safaricom.co.ke"
        self._cached_token = None
        self._token_expiry = None
        self._lock = asyncio.Lock()

    async def get_access_token(self) -> Optional[str]:
        async with self._lock:
            if self._cached_token and self._token_expiry and datetime.now(UTC) < self._token_expiry:
                return self._cached_token

            try:
                auth = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
                headers = {"Authorization": f"Basic {auth}"}
                url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"

                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    token = data.get("access_token")

                    if token:
                        self._cached_token = token
                        self._token_expiry = datetime.now(UTC) + timedelta(minutes=50)
                        return token
            except Exception as e:
                logger.exception("Token error")
            return None


class MpesaSTKService:
    def __init__(self, auth_service: MpesaAuthService):
        self.auth_service = auth_service
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.callback_url = f"{settings.CALLBACK_BASE_URL}/api/v1/mpesa/callback"
        self.base_url = "https://api.safaricom.co.ke" if settings.MPESA_ENV == "production" else "https://sandbox.safaricom.co.ke"

    async def initiate(self, phone: str, amount: float, account_ref: str, desc: str) -> Optional[Dict]:
        try:
            token = await self.auth_service.get_access_token()
            if not token:
                return None

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

                if data.get("ResponseCode") == "0":
                    return {
                        "checkout_request_id": data.get("CheckoutRequestID"),
                        "merchant_request_id": data.get("MerchantRequestID"),
                        "customer_message": data.get("CustomerMessage"),
                    }
                return None

        except Exception as e:
            logger.exception("STK Push error")
            return None


class MpesaService:
    def __init__(self):
        self.service_repo = ServiceRepository()
        self.payment_repo = PaymentRepository()
        self.auth_service = MpesaAuthService()
        self.stk_service = MpesaSTKService(self.auth_service)

        logger.info("=" * 60)
        logger.info("🚗 M-Pesa Service Initialized")
        logger.info(f"   Environment: {settings.MPESA_ENV}")
        logger.info(f"   Shortcode: {settings.MPESA_SHORTCODE}")
        
        # Verify services on startup
        asyncio.create_task(self._verify_services())

    async def _verify_services(self):
        """Verify services exist in database."""
        try:
            response = await self.service_repo._run_sync(
                lambda: supabase.table("services")
                .select("id, code, name, price, active")
                .order("display_order")
                .execute()
            )
            services = response.data or []
            logger.info("📋 Services Available:")
            for s in services:
                logger.info(f"   ✅ {s.get('id')}: {s.get('code')} = {s.get('price')} KES")
            if not services:
                logger.warning("⚠️ No services found! Please insert the 3 services.")
        except Exception as e:
            logger.error(f"Could not verify services: {e}")

    async def get_services(self) -> List[Dict]:
        """Get all active services."""
        return await self.service_repo.get_all()

    async def get_service_by_code(self, service_code: str) -> Optional[Dict]:
        """Get a single service by code."""
        return await self.service_repo.get_by_code(service_code)

    async def get_service_by_id(self, service_id: int) -> Optional[Dict]:
        """Get a single service by ID."""
        return await self.service_repo.get_by_id(service_id)

    async def initiate_payment(
        self, 
        phone: str, 
        service_code: str, 
        description: Optional[str] = None,
        user_id: Optional[str] = None, 
        request_id: Optional[str] = None
    ) -> Dict:
        """Initiate an STK Push payment."""
        try:
            request = STKPushRequest(
                phone=phone,
                service_id=service_code,
                description=description,
                user_id=user_id,
                request_id=request_id
            )
        except ValueError as e:
            return {"success": False, "error": str(e)}

        # ─── Step 1: Get service by CODE from frontend ───
        service = await self.service_repo.get_by_code(request.service_id)
        if not service:
            return {"success": False, "error": f"Service '{request.service_id}' not found"}

        amount = float(service["price"])
        if amount <= 0:
            return {"success": False, "error": f"Invalid price for '{request.service_id}'"}

        service_id = service.get("id")  # This is the INTEGER ID (1, 2, or 3)
        logger.info(f"💰 {service.get('name')}: {amount} KES (ID: {service_id})")

        # ─── Step 2: Send STK Push ───
        stk_result = await self.stk_service.initiate(
            phone=request.phone,
            amount=amount,
            account_ref=request.service_id,
            desc=description or service.get("name", request.service_id)
        )

        if not stk_result:
            return {"success": False, "error": "Failed to initiate STK Push"}

        checkout_id = stk_result.get("checkout_request_id")

        # ─── Step 3: Create payment with INTEGER service_id ───
        payment_data = {
            "user_id": request.user_id,
            "service_id": service_id,           # ✅ INTEGER (1, 2, or 3)
            "service_name": service.get("name"),
            "amount": amount,
            "currency": service.get("currency", "KES"),
            "phone": request.phone,
            "checkout_request_id": checkout_id,
            "merchant_request_id": stk_result.get("merchant_request_id"),
            "status": PaymentStatus.PENDING.value,
            "pricing_version": service.get("version", 1),
            "request_id": request.request_id,
        }

        # Log the payment data before saving
        logger.info("📝 PAYMENT DATA BEING INSERTED:")
        logger.info(json.dumps(payment_data, default=str, indent=2))

        saved = await self.payment_repo.create(payment_data)
        if not saved:
            return {"success": False, "error": "Failed to save payment record"}

        return {
            "success": True,
            "checkout_request_id": checkout_id,
            "merchant_request_id": stk_result.get("merchant_request_id"),
            "customer_message": stk_result.get("customer_message"),
            "service_name": service.get("name"),
            "amount": amount,
            "currency": service.get("currency", "KES"),
        }

    async def process_callback(self, callback_data: Dict) -> bool:
        """Process M-Pesa callback."""
        try:
            stk = callback_data.get("Body", {}).get("stkCallback", {})
            checkout_id = stk.get("CheckoutRequestID")
            result_code = stk.get("ResultCode")
            result_desc = stk.get("ResultDesc", "")

            if not checkout_id:
                logger.error("No CheckoutRequestID in callback")
                return False

            payment = await self.payment_repo.get_by_checkout_id(checkout_id)
            if not payment:
                logger.error(f"Payment not found: {checkout_id}")
                return False

            if payment.get("status") == PaymentStatus.COMPLETED.value:
                logger.info(f"Payment already completed: {checkout_id}")
                return True

            if result_code == "0":
                return await self._handle_success(payment, checkout_id, stk)
            else:
                return await self._handle_failure(checkout_id, result_code, result_desc)

        except Exception as e:
            logger.exception("Callback error")
            return False

    async def _handle_success(self, payment: Dict, checkout_id: str, stk: Dict) -> bool:
        """Handle successful payment."""
        try:
            metadata = stk.get("CallbackMetadata", {}).get("Item", [])
            meta = {item.get("Name"): item.get("Value") for item in metadata}

            update_data = {
                "status": PaymentStatus.COMPLETED.value,
                "updated_at": datetime.now(UTC).isoformat(),
                "mpesa_receipt": meta.get("MpesaReceiptNumber"),
                "paid_amount": float(meta.get("Amount", 0)),
                "paid_phone": meta.get("PhoneNumber"),
                "result_code": "0",
                "result_desc": "Payment successful",
            }

            updated = await self.payment_repo.update_with_lock(checkout_id, update_data)
            if not updated:
                logger.info(f"Payment already processed: {checkout_id}")
                return True

            # ─── Step 4: Unlock service using INTEGER service_id ───
            user_id = payment.get("user_id")
            service_id = payment.get("service_id")  # ✅ This is now an INTEGER

            if user_id and service_id:
                # Verify the service exists
                service = await self.service_repo.get_by_id(service_id)
                if service:
                    expires_at = datetime.now(UTC) + timedelta(days=365)
                    
                    # Store INTEGER service_id in service_access
                    access_data = {
                        "user_id": user_id,
                        "service_id": service_id,      # ✅ INTEGER (1, 2, or 3)
                        "status": "active",
                        "expires_at": expires_at.isoformat(),
                        "payment_ref": checkout_id,
                    }
                    
                    await self.payment_repo.create_service_access(access_data)
                    logger.info(f"🔓 Service unlocked: {service.get('code')} (ID: {service_id}) for {user_id}")
                else:
                    logger.error(f"❌ Service with ID {service_id} not found")

            # Update request status if linked
            request_id = payment.get("request_id")
            if request_id:
                await self.payment_repo.update_request_status(request_id, "paid")
                logger.info(f"✅ Request {request_id} marked as paid")

            logger.info(f"✅ Payment completed: {checkout_id}")
            return True

        except Exception as e:
            logger.exception("Success handler error")
            return False

    async def _handle_failure(self, checkout_id: str, result_code: str, result_desc: str) -> bool:
        """Handle failed payment."""
        try:
            update_data = {
                "status": PaymentStatus.FAILED.value,
                "updated_at": datetime.now(UTC).isoformat(),
                "result_code": str(result_code),
                "result_desc": result_desc,
            }
            await self.payment_repo.update_with_lock(checkout_id, update_data)
            logger.warning(f"❌ Payment failed: {checkout_id} - {result_desc}")
            return True
        except Exception as e:
            logger.exception("Failure handler error")
            return False

    async def get_payment_status(self, checkout_id: str) -> Dict:
        """Get payment status."""
        payment = await self.payment_repo.get_by_checkout_id(checkout_id)
        if not payment:
            return {"success": False, "error": "Payment not found"}
        return {
            "success": True,
            "checkout_request_id": payment.get("checkout_request_id"),
            "status": payment.get("status"),
            "amount": payment.get("amount"),
            "service_id": payment.get("service_id"),  # Returns INTEGER
            "service_name": payment.get("service_name"),
            "mpesa_receipt": payment.get("mpesa_receipt"),
            "created_at": payment.get("created_at"),
        }

    async def get_user_services(self, user_id: str) -> List[Dict]:
        """Get unlocked services for a user."""
        records = await self.payment_repo.get_user_service_access(user_id)
        services = []
        for record in records:
            # record["service_id"] is an INTEGER
            service_id = record.get("service_id")
            service = await self.service_repo.get_by_id(service_id)
            if service:
                # Return the code to frontend (they expect "mileage", not 1)
                services.append({
                    "service_id": service.get("code"),  # Convert to code for frontend
                    "service_name": service.get("name"),
                    "status": record.get("status"),
                    "expires_at": record.get("expires_at"),
                })
        return services

    async def check_service_access(self, user_id: str, service_code: str) -> Dict:
        """
        Check if user has access to a service.
        Input: service_code (e.g., "mileage") from frontend.
        """
        # ─── Step 1: Convert code to ID ───
        service = await self.service_repo.get_by_code(service_code)
        if not service:
            return {
                "service_id": service_code,
                "unlocked": False,
                "error": "Service not found"
            }
        
        service_id = service.get("id")  # INTEGER
        
        # ─── Step 2: Check access using INTEGER ID ───
        access = await self.payment_repo.check_service_access_by_id(user_id, service_id)
        
        if access:
            return {
                "service_id": service_code,  # Return code to frontend
                "unlocked": True,
                "status": access.get("status"),
                "expires_at": access.get("expires_at"),
            }
        return {
            "service_id": service_code,
            "unlocked": False,
        }

    async def get_payment_history(self, user_id: str) -> List[Dict]:
        """Get user's payment history."""
        payments = await self.payment_repo.get_user_payments(user_id)
        
        # Convert service_id back to code for frontend
        for payment in payments:
            service_id = payment.get("service_id")
            if service_id:
                service = await self.service_repo.get_by_id(service_id)
                if service:
                    payment["service_code"] = service.get("code")
        return payments

    # ─── Admin Methods ───
    # IMPORTANT: Admin methods use INTEGER service_id, not code

    async def admin_get_service(self, service_id: int) -> Optional[Dict]:
        """Admin: Get a service by ID."""
        return await self.service_repo.get_by_id(service_id)

    async def admin_get_all_services(self, include_inactive: bool = False) -> List[Dict]:
        """Admin: Get all services."""
        try:
            query = supabase.table("services").select("*")
            if not include_inactive:
                query = query.eq("active", True)
            response = await self.service_repo._run_sync(
                lambda: query.order("display_order").execute()
            )
            return response.data or []
        except Exception as e:
            logger.exception("Admin get all services error")
            return []

    async def admin_update_service(self, service_id: int, data: Dict, changed_by: str) -> Optional[Dict]:
        """Admin: Update a service by INTEGER ID."""
        try:
            # Verify service exists using ID
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
            logger.exception(f"Admin update service error: {service_id}")
            return None

    async def admin_delete_service(self, service_id: int, deleted_by: str) -> bool:
        """Admin: Soft delete a service by INTEGER ID."""
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
            logger.exception(f"Admin delete service error: {service_id}")
            return False

    async def admin_restore_service(self, service_id: int) -> bool:
        """Admin: Restore a service by INTEGER ID."""
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
            logger.exception(f"Admin restore service error: {service_id}")
            return False


mpesa_service = MpesaService()
