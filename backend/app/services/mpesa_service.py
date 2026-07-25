"""
Auto-D Kenya - M-Pesa Service (FIXED)
USES: services table with code column
"""

import base64
import json
import logging
import asyncio
import httpx
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any, List
from enum import Enum
from decimal import Decimal, getcontext
from concurrent.futures import ThreadPoolExecutor
import uuid

from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.core.config import settings
from app.core.database import supabase

getcontext().prec = 28
logger = logging.getLogger(__name__)
_db_executor = ThreadPoolExecutor(max_workers=10)


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ServiceAccessStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class STKPushRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    phone: str
    service_id: str
    description: Optional[str] = None
    user_id: Optional[str] = None
    corporate_id: Optional[str] = None
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
            raise ValueError(f"Phone must be 9 digits")
        valid_prefixes = ('7', '11')
        if not any(cleaned.startswith(p) for p in valid_prefixes):
            raise ValueError(f"Invalid Safaricom prefix")
        return f"254{cleaned}"

    @field_validator('service_id')
    @classmethod
    def validate_service_id(cls, v: str) -> str:
        return v.strip().lower()


class ServiceRepository:
    """Queries the 'services' table using the 'code' column."""

    async def _run_sync(self, operation):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_db_executor, operation)

    async def get_by_code(self, code: str) -> Optional[Dict]:
        """CRITICAL: Query services table by code column."""
        try:
            code = code.strip().lower()
            logger.info(f"🔍 Looking for service: '{code}'")

            # ─── DIRECT QUERY: services table, code column ───
            response = await self._run_sync(
                lambda: supabase.table("services")
                .select("*")
                .eq("code", code)
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.error(f"❌ Service '{code}' NOT FOUND")
                # Log all services for debugging
                all_services = await self._run_sync(
                    lambda: supabase.table("services").select("code, price").execute()
                )
                logger.info(f"📋 Available services: {[s.get('code') for s in (all_services.data or [])]}")
                return None

            row = response.data[0]
            logger.info(f"✅ Found: {row.get('code')} = {row.get('price')} KES")

            return {
                "id": row.get("id"),
                "code": row.get("code"),
                "name": row.get("name", code.title()),
                "price": Decimal(str(row.get("price", 0))),
                "currency": row.get("currency", "KES"),
                "active": row.get("active", True),
            }

        except Exception as e:
            logger.exception(f"Service lookup error: {code}")
            return None


class PaymentRepository:
    async def _run_sync(self, operation):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_db_executor, operation)

    async def create(self, data: Dict) -> Optional[Dict]:
        try:
            if 'id' not in data or not data['id']:
                data['id'] = str(uuid.uuid4())
            data['created_at'] = datetime.now(UTC).isoformat()
            data['updated_at'] = datetime.now(UTC).isoformat()

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

    async def update_with_optimistic_lock(self, checkout_id: str, data: Dict, expected_status: str = "pending") -> Optional[Dict]:
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

    async def create_service_access(self, data: Dict) -> Optional[Dict]:
        try:
            data['id'] = str(uuid.uuid4())
            data['created_at'] = datetime.now(UTC).isoformat()
            response = await self._run_sync(
                lambda: supabase.table("service_access").insert(data).execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.exception(f"Create service access error: {e}")
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
        self._token_lock = asyncio.Lock()

    async def get_access_token(self) -> Optional[str]:
        async with self._token_lock:
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
        self.environment = settings.MPESA_ENV
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.callback_url = f"{settings.CALLBACK_BASE_URL}/api/v1/mpesa/callback"
        self.base_url = "https://api.safaricom.co.ke" if self.environment == "production" else "https://sandbox.safaricom.co.ke"
        self.max_retries = 3
        self.timeout = 60

    async def initiate_stk_push(self, phone: str, amount: float, account_reference: str, transaction_desc: str) -> Optional[Dict]:
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
                "AccountReference": account_reference[:12],
                "TransactionDesc": transaction_desc[:36],
            }

            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"

            for attempt in range(self.max_retries):
                try:
                    async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
                        response = await client.post(url, json=payload, headers=headers)
                        response.raise_for_status()
                        data = response.json()
                        if data.get("ResponseCode") == "0":
                            return {
                                "success": True,
                                "checkout_request_id": data.get("CheckoutRequestID"),
                                "merchant_request_id": data.get("MerchantRequestID"),
                                "customer_message": data.get("CustomerMessage"),
                                "response_description": data.get("ResponseDescription"),
                            }
                        return None
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    logger.error(f"STK Push error: {e}")
            return None
        except Exception as e:
            logger.exception("STK Push error")
            return None


class MpesaCallbackService:
    def __init__(self, payment_repo: PaymentRepository, service_repo: ServiceRepository):
        self.payment_repo = payment_repo
        self.service_repo = service_repo
        self.service_access_days = 365

    async def process_callback(self, callback_data: Dict) -> bool:
        try:
            stk = callback_data.get("Body", {}).get("stkCallback", {})
            checkout_id = stk.get("CheckoutRequestID")
            result_code = stk.get("ResultCode")
            result_desc = stk.get("ResultDesc", "")

            if not checkout_id:
                return False

            payment = await self.payment_repo.get_by_checkout_id(checkout_id)
            if not payment:
                logger.error(f"Payment not found: {checkout_id}")
                return False

            if payment.get("status") == PaymentStatus.COMPLETED.value:
                return True

            metadata = stk.get("CallbackMetadata", {}).get("Item", [])
            metadata_dict = {item.get("Name"): item.get("Value") for item in metadata}

            if result_code == 0:
                return await self._handle_success(payment, checkout_id, result_code, result_desc, metadata_dict, callback_data)
            else:
                return await self._handle_failure(checkout_id, result_code, result_desc, callback_data)

        except Exception as e:
            logger.exception("Callback error")
            return False

    async def _handle_success(self, payment, checkout_id, result_code, result_desc, metadata, callback_data):
        try:
            user_id = payment.get("user_id")
            service_id = payment.get("service_id")
            request_id = payment.get("request_id")

            update_data = {
                "status": PaymentStatus.COMPLETED.value,
                "updated_at": datetime.now(UTC).isoformat(),
                "result_code": str(result_code),
                "result_desc": result_desc,
                "mpesa_receipt": metadata.get("MpesaReceiptNumber"),
                "paid_amount": float(metadata.get("Amount", 0)),
                "paid_phone": metadata.get("PhoneNumber"),
                "callback_payload": callback_data,
            }

            updated = await self.payment_repo.update_with_optimistic_lock(checkout_id, update_data)
            if not updated:
                return True

            # Unlock service
            if user_id and service_id:
                expires_at = datetime.now(UTC) + timedelta(days=self.service_access_days)
                await self.payment_repo.create_service_access({
                    "user_id": user_id,
                    "service_id": service_id,
                    "status": ServiceAccessStatus.ACTIVE.value,
                    "expires_at": expires_at.isoformat(),
                    "payment_ref": checkout_id,
                })

            # Update request status
            if request_id:
                await self.payment_repo.update_request_status(request_id, "paid")

            logger.info(f"✅ Payment completed: {checkout_id}")
            return True

        except Exception as e:
            logger.exception("Success handler error")
            return False

    async def _handle_failure(self, checkout_id, result_code, result_desc, callback_data):
        try:
            update_data = {
                "status": PaymentStatus.FAILED.value,
                "updated_at": datetime.now(UTC).isoformat(),
                "result_code": str(result_code),
                "result_desc": result_desc,
                "callback_payload": callback_data,
            }
            await self.payment_repo.update_with_optimistic_lock(checkout_id, update_data)
            logger.warning(f"Payment failed: {result_code} - {result_desc}")
            return True
        except Exception as e:
            logger.exception("Failure handler error")
            return False


class MpesaService:
    def __init__(self):
        self.service_repo = ServiceRepository()
        self.payment_repo = PaymentRepository()
        self.auth_service = MpesaAuthService()
        self.stk_service = MpesaSTKService(self.auth_service)
        self.callback_service = MpesaCallbackService(self.payment_repo, self.service_repo)

        logger.info("=" * 70)
        logger.info("🚗 M-Pesa Service initialized")
        self._verify_services()
        logger.info("=" * 70)

    def _verify_services(self):
        try:
            response = supabase.table("services").select("code, price, active").execute()
            logger.info("📋 SERVICES IN DATABASE:")
            for s in (response.data or []):
                logger.info(f"   ✅ {s.get('code')}: {s.get('price')} KES (active: {s.get('active')})")
        except Exception as e:
            logger.error(f"Could not verify services: {e}")

    async def get_service(self, service_id: str) -> Optional[Dict]:
        return await self.service_repo.get_by_code(service_id)

    async def initiate_stk_push(self, phone: str, service_id: str, description: Optional[str] = None,
                                user_id: Optional[str] = None, corporate_id: Optional[str] = None,
                                request_id: Optional[str] = None) -> Dict:
        try:
            request = STKPushRequest(
                phone=phone, service_id=service_id, description=description,
                user_id=user_id, corporate_id=corporate_id, request_id=request_id
            )
        except ValueError as e:
            return {"success": False, "error": str(e)}

        try:
            # ─── GET SERVICE FROM services TABLE ───
            service = await self.service_repo.get_by_code(request.service_id)
            if not service:
                logger.error(f"❌ Service '{request.service_id}' not found")
                return {"success": False, "error": f"Service '{request.service_id}' not found"}

            amount = float(service["price"])
            if amount <= 0:
                return {"success": False, "error": f"Invalid price for '{request.service_id}'"}

            logger.info(f"💰 Service: {service.get('name')}, Price: {amount} KES")

            # ─── SEND STK PUSH ───
            stk_result = await self.stk_service.initiate_stk_push(
                phone=request.phone,
                amount=amount,
                account_reference=request.service_id,
                transaction_desc=description or service.get("name", request.service_id)
            )

            if not stk_result:
                return {"success": False, "error": "Failed to initiate STK Push"}

            checkout_id = stk_result.get("checkout_request_id")
            if not checkout_id:
                return {"success": False, "error": "No checkout ID from M-Pesa"}

            # ─── CREATE PAYMENT ───
            payment_data = {
                "user_id": request.user_id,
                "service_id": request.service_id,
                "service_name": service.get("name", request.service_id),
                "amount": amount,
                "phone": request.phone,
                "checkout_request_id": checkout_id,
                "status": PaymentStatus.PENDING.value,
                "request_id": request.request_id,
            }

            saved = await self.payment_repo.create(payment_data)
            if not saved:
                return {"success": False, "error": "Failed to save payment record"}

            return {
                "success": True,
                "checkout_request_id": checkout_id,
                "merchant_request_id": stk_result.get("merchant_request_id"),
                "customer_message": stk_result.get("customer_message"),
                "service_name": service.get("name", request.service_id),
                "amount": amount,
            }

        except Exception as e:
            logger.exception("STK Push error")
            return {"success": False, "error": str(e)}

    async def process_callback(self, callback_data: Dict) -> bool:
        return await self.callback_service.process_callback(callback_data)

    async def get_payment_status(self, checkout_request_id: str) -> Dict:
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
        }

    async def confirm_payment_manually(self, checkout_request_id: str, user_id: str) -> Dict:
        payment = await self.payment_repo.get_by_checkout_id(checkout_request_id)
        if not payment:
            return {"success": False, "error": "Payment not found"}
        if payment.get("user_id") != user_id:
            return {"success": False, "error": "Unauthorized"}

        # Just trigger the callback handler again with a synthetic success
        callback_data = {
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": checkout_request_id,
                    "ResultCode": "0",
                    "ResultDesc": "Confirmed manually",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": payment.get("amount", 0)},
                            {"Name": "MpesaReceiptNumber", "Value": f"MANUAL-{checkout_request_id[:8]}"},
                        ]
                    }
                }
            }
        }
        success = await self.process_callback(callback_data)
        if success:
            return {"success": True, "message": "Payment confirmed"}
        return {"success": False, "error": "Failed to confirm"}


mpesa_service = MpesaService()
