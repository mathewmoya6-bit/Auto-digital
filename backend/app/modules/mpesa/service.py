# app/modules/mpesa/service.py
# ================================================================
# Auto-D Kenya - M-Pesa Service
# ================================================================

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from supabase import Client

from app.core.config import settings
from app.core.database import get_supabase
from app.core.exceptions import (
    AppException,
    NotFoundException,
    ValidationException,
)
from app.core.security import mask_sensitive
from app.modules.mpesa.stk_push import StkPushService
from app.modules.mpesa.repository import MpesaRepository

logger = logging.getLogger(__name__)


class MpesaService:
    """M-Pesa payment service orchestrator."""

    # Status constants
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    
    # Access constants
    ACCESS_ACTIVE = "active"
    ACCESS_EXPIRED = "expired"
    ACCESS_INACTIVE = "inactive"
    
    DEFAULT_ACCESS_DAYS = 365

    def __init__(self):
        """Initialize the M-Pesa service."""
        # Use singleton Supabase client from database module
        self.supabase: Client = get_supabase()
        self.stk_push = StkPushService() if settings.mpesa_configured else None
        self.repository = MpesaRepository()
        self._services_cache = None
        self._cache_time = None
        self._cache_ttl = 300  # 5 minutes

    # ================================================================
    # HELPERS
    # ================================================================

    async def _get_service_active_column(self) -> str:
        """
        Get the active column name for services.
        """
        return "active"

    # ================================================================
    # SERVICE LOOKUP
    # ================================================================

    async def _get_service(
        self,
        service_id: Union[int, str],
    ) -> Dict[str, Any]:
        """
        Retrieve an active service by numeric ID or service code.

        Raises:
            NotFoundException
            ValidationException
        """

        active_column = await self._get_service_active_column()

        query = (
            self.supabase
            .table("services")
            .select("*")
            .eq(active_column, True)
        )

        if isinstance(service_id, int):
            query = query.eq("id", service_id)

        elif isinstance(service_id, str):

            if service_id.isdigit():
                query = query.eq("id", int(service_id))
            else:
                query = query.eq("code", service_id.lower())

        response = query.maybe_single().execute()

        if not response or not response.data:
            raise NotFoundException(
                f"Service '{service_id}' not found."
            )

        service = response.data

        price = float(service.get("price") or 0)

        if price <= 0:
            raise ValidationException(
                f"Invalid service price for '{service.get('name')}'."
            )

        return service

    async def get_service_by_id(
        self,
        service_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Return service by numeric ID.
        """

        try:
            return await self._get_service(service_id)
        except Exception:
            return None

    async def get_service_by_code(
        self,
        service_code: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Return service by code.
        """

        try:
            return await self._get_service(service_code)
        except Exception:
            return None

    # ================================================================
    # PAYMENT INITIATION
    # ================================================================

    async def initiate_payment(
        self,
        phone: str,
        service_id: Union[int, str],
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Initiate an M-Pesa STK Push.

        The amount supplied by the client is ignored.
        Billing always uses the price stored in the services table.
        """

        service = await self._get_service(service_id)

        db_amount = float(service["price"])

        if amount is not None and amount != db_amount:
            logger.warning(
                "Ignoring client amount %.2f. Using database price %.2f.",
                amount,
                db_amount,
            )

        description = description or service["name"]

        logger.info(
            "Initiating payment | user=%s service=%s amount=%s phone=%s",
            user_id,
            service["code"],
            db_amount,
            mask_sensitive(phone),
        )

        # Create payment record
        payment_data = {
            "user_id": user_id,
            "service_id": service["id"],
            "amount": db_amount,
            "currency": service.get("currency", "KES"),
            "status": self.STATUS_PENDING,
            "description": description,
            "phone": phone,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Insert payment record (synchronous)
            payment_result = (
                self.supabase
                .table("payments")
                .insert(payment_data)
                .execute()
            )

            if not payment_result.data:
                raise AppException("Failed to create payment record")

            payment = payment_result.data[0]
            payment_id = payment.get("id")

            # Initiate STK Push (asynchronous)
            if not self.stk_push:
                raise AppException("M-Pesa service is not configured")

            response = await self.stk_push.initiate_push(
                phone=phone,
                amount=db_amount,
                description=description,
                user_id=user_id,
                service_id=service["id"],
            )

            if not response:
                raise AppException("STK Push returned no response.")

            checkout_request_id = response.get("checkout_request_id")

            if not checkout_request_id:
                raise AppException(
                    response.get(
                        "error",
                        "CheckoutRequestID missing.",
                    )
                )

            # Update payment with checkout request ID (synchronous)
            (
                self.supabase
                .table("payments")
                .update({
                    "checkout_request_id": checkout_request_id,
                    "mpesa_response": response,
                })
                .eq("id", payment_id)
                .execute()
            )

            logger.info(
                "STK Push sent successfully | checkout=%s",
                mask_sensitive(checkout_request_id),
            )

            return {
                "success": True,
                "checkout_request_id": checkout_request_id,
                "payment_id": payment_id,
                "merchant_request_id": response.get(
                    "merchant_request_id"
                ),
                "customer_message": response.get(
                    "customer_message",
                    "STK Push sent successfully.",
                ),
                "status": response.get(
                    "status",
                    self.STATUS_PENDING,
                ),
                "response_code": response.get(
                    "response_code"
                ),
                "response_description": response.get(
                    "response_description"
                ),
            }

        except Exception as e:
            logger.error(f"Payment initiation failed: {e}")
            raise AppException(f"Payment initiation failed: {str(e)}")

    # ================================================================
    # PAYMENT STATUS
    # ================================================================

    async def get_payment_status(
        self,
        checkout_request_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get payment status for a user.
        """

        payment = await self.repository.get_payment_by_checkout_id(
            checkout_request_id
        )

        if not payment:
            raise NotFoundException("Payment not found.")

        if payment.get("user_id") != user_id:
            raise NotFoundException("Payment not found.")

        # If payment is still pending and STK Push is available, check with M-Pesa
        if payment.get("status") == self.STATUS_PENDING and self.stk_push:
            try:
                stk_status = await self.stk_push.query_payment(
                    checkout_request_id
                )

                # Update payment if status changed (synchronous)
                if stk_status.get("status") != self.STATUS_PENDING:
                    (
                        self.supabase
                        .table("payments")
                        .update({
                            "status": stk_status.get("status"),
                            "result_code": stk_status.get("result_code"),
                            "result_desc": stk_status.get("result_desc"),
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        })
                        .eq("id", payment["id"])
                        .execute()
                    )

                    payment["status"] = stk_status.get("status")
                    payment["result_desc"] = stk_status.get("result_desc")

            except Exception as e:
                logger.warning(f"Failed to check STK status: {e}")

        return {
            "checkout_request_id": checkout_request_id,
            "status": payment.get("status"),
            "amount": payment.get("amount"),
            "phone": payment.get("phone"),
            "receipt": payment.get("receipt_number"),
            "created_at": payment.get("created_at"),
            "updated_at": payment.get("updated_at"),
        }

    # ================================================================
    # USER SERVICE LOOKUP
    # ================================================================

    async def _get_user_service(
        self,
        user_id: str,
        service_id: int,
    ) -> Optional[Dict[str, Any]]:

        try:
            result = (
                self.supabase
                .table("user_services")
                .select("*")
                .eq("user_id", user_id)
                .eq("service_id", service_id)
                .maybe_single()
                .execute()
            )

            return result.data if result else None

        except Exception:
            logger.exception(
                "Unable to load user service."
            )
            return None

    # ================================================================
    # MANUAL CONFIRMATION
    # ================================================================

    async def confirm_payment(
        self,
        checkout_request_id: str,
        user_id: str,
    ) -> Dict[str, Any]:

        payment = await self.repository.get_payment_by_checkout_id(
            checkout_request_id
        )

        if not payment:
            raise NotFoundException("Payment not found.")

        if payment.get("user_id") != user_id:
            raise NotFoundException("Payment not found.")

        if payment.get("status") != self.STATUS_COMPLETED:
            raise AppException(
                f"Payment status is '{payment.get('status')}'.",
                status_code=409,
            )

        existing = await self._get_user_service(
            payment["user_id"],
            payment["service_id"],
        )

        if existing and existing.get("status") == self.ACCESS_ACTIVE:
            return {
                "status": self.STATUS_COMPLETED,
                "message": "Service already active.",
            }

        await self._unlock_service_atomic(
            user_id=payment["user_id"],
            service_id=payment["service_id"],
            payment_id=payment.get("id"),
            expected_amount=payment.get("amount"),
        )

        return {
            "status": self.STATUS_COMPLETED,
            "message": "Service unlocked.",
        }

    # ================================================================
    # ATOMIC SERVICE UNLOCK
    # ================================================================

    def _unlock_service_atomic_sync(
        self,
        supabase,
        user_id: str,
        service_id: int,
        payment_id: Optional[str] = None,
        expires_at: Optional[str] = None,
    ) -> Dict[str, Any]:

        now = datetime.now(timezone.utc)

        expiry = expires_at or (
            now + timedelta(days=self.DEFAULT_ACCESS_DAYS)
        ).isoformat()

        row = {
            "user_id": user_id,
            "service_id": service_id,
            "status": self.ACCESS_ACTIVE,
            "expires_at": expiry,
            "updated_at": now.isoformat(),
            "created_at": now.isoformat(),
        }

        if payment_id:
            row["payment_id"] = payment_id

        result = (
            supabase
            .table("user_services")
            .upsert(
                row,
                on_conflict="user_id,service_id",
            )
            .execute()
        )

        if result and result.data:
            return result.data[0]

        return row

    async def _unlock_service_atomic(
        self,
        user_id: str,
        service_id: int,
        payment_id: Optional[str] = None,
        callback_amount: Optional[float] = None,
        expected_amount: Optional[float] = None,
        expires_at: Optional[str] = None,
    ) -> None:

        if (
            callback_amount is not None
            and expected_amount is not None
        ):

            callback_value = Decimal(
                str(callback_amount)
            ).quantize(
                Decimal("0.01")
            )

            expected_value = Decimal(
                str(expected_amount)
            ).quantize(
                Decimal("0.01")
            )

            if callback_value != expected_value:
                raise ValidationException(
                    "Callback amount does not match payment amount."
                )

        loop = asyncio.get_running_loop()

        await loop.run_in_executor(
            None,
            self._unlock_service_atomic_sync,
            self.supabase,
            user_id,
            service_id,
            payment_id,
            expires_at,
        )

        logger.info(
            "Service unlocked | user=%s service=%s",
            user_id,
            service_id,
        )

    async def unlock_service(
        self,
        user_id: str,
        service_id: int,
        payment_id: Optional[str] = None,
        callback_amount: Optional[float] = None,
        expected_amount: Optional[float] = None,
        expires_at: Optional[str] = None,
    ) -> None:

        await self._unlock_service_atomic(
            user_id=user_id,
            service_id=service_id,
            payment_id=payment_id,
            callback_amount=callback_amount,
            expected_amount=expected_amount,
            expires_at=expires_at,
        )

    # ================================================================
    # CALLBACK PROCESSING
    # ================================================================

    async def handle_callback(
        self,
        checkout_request_id: str,
        result_code: str,
        result_desc: str,
        receipt: Optional[str] = None,
        amount: Optional[float] = None,
        phone: Optional[str] = None,
        transaction_date: Optional[str] = None,
        callback_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process Safaricom callback.

        This is the ONLY place where purchased services
        are unlocked.
        """

        payment = await self.repository.get_payment_by_checkout_id(
            checkout_request_id
        )

        if not payment:
            logger.warning(
                "Unknown checkout request %s",
                checkout_request_id,
            )
            return {
                "status": "not_found",
                "message": "Payment not found.",
            }

        # --------------------------------------------------------
        # Validate phone
        # --------------------------------------------------------

        if phone and payment.get("phone"):
            callback_phone = self._normalize_phone(phone)
            stored_phone = self._normalize_phone(
                payment["phone"]
            )

            if callback_phone != stored_phone:
                logger.error(
                    "Phone mismatch callback=%s stored=%s",
                    mask_sensitive(callback_phone),
                    mask_sensitive(stored_phone),
                )

                return {
                    "status": "rejected",
                    "message": "Phone mismatch.",
                }

        # --------------------------------------------------------
        # Validate amount
        # --------------------------------------------------------

        if amount is not None:
            callback_amount = Decimal(
                str(amount)
            ).quantize(
                Decimal("0.01")
            )

            expected_amount = Decimal(
                str(payment["amount"])
            ).quantize(
                Decimal("0.01")
            )

            if callback_amount != expected_amount:
                logger.error(
                    "Amount mismatch callback=%s expected=%s",
                    callback_amount,
                    expected_amount,
                )

                return {
                    "status": "rejected",
                    "message": "Amount mismatch.",
                }

        # --------------------------------------------------------
        # Update payment
        # --------------------------------------------------------

        updated = await self.repository.update_payment_from_callback(
            checkout_request_id=checkout_request_id,
            result_code=result_code,
            result_desc=result_desc,
            receipt=receipt,
            amount=amount,
            phone=phone,
            transaction_date=transaction_date,
            callback_payload=callback_payload,
        )

        if updated is None or isinstance(updated, bool):
            updated = await self.repository.get_payment_by_checkout_id(
                checkout_request_id
            )

        if updated is None:
            raise AppException(
                "Unable to reload payment."
            )

        # --------------------------------------------------------
        # Unlock purchased service
        # --------------------------------------------------------

        if (
            str(result_code) == "0"
            and updated.get("status") == self.STATUS_COMPLETED
        ):

            existing = await self._get_user_service(
                updated["user_id"],
                updated["service_id"],
            )

            if not existing or existing.get("status") != self.ACCESS_ACTIVE:

                await self.unlock_service(
                    user_id=updated["user_id"],
                    service_id=updated["service_id"],
                    payment_id=updated.get("id"),
                    callback_amount=amount,
                    expected_amount=updated["amount"],
                )

                logger.info(
                    "Service unlocked for payment %s",
                    checkout_request_id,
                )

        return {
            "status": "updated",
            "payment": updated,
        }

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number for comparison."""
        if not phone:
            return ""
        cleaned = ''.join(filter(str.isdigit, phone))
        if cleaned.startswith('0'):
            cleaned = '254' + cleaned[1:]
        elif cleaned.startswith('7'):
            cleaned = '254' + cleaned
        elif not cleaned.startswith('254'):
            cleaned = '254' + cleaned
        return cleaned

    # ================================================================
    # SERVICE ACCESS
    # ================================================================

    async def check_service_access(
        self,
        user_id: str,
        service_code: str,
    ) -> Dict[str, Any]:

        service = await self.get_service_by_code(
            service_code
        )

        if not service:
            return {
                "has_access": False,
                "status": "service_not_found",
            }

        return await self.check_service_access_by_id(
            user_id,
            service["id"],
        )

    async def check_service_access_by_id(
        self,
        user_id: str,
        service_id: int,
    ) -> Dict[str, Any]:

        result = (
            self.supabase
            .table("user_services")
            .select("*")
            .eq("user_id", user_id)
            .eq("service_id", service_id)
            .maybe_single()
            .execute()
        )

        return self._evaluate_service_access(
            result.data if result else None
        )

    def _evaluate_service_access(
        self,
        access_record: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:

        if not access_record:
            return {
                "has_access": False,
                "status": "no_access",
                "message": "No access to this service",
            }

        status = access_record.get("status")
        expires_at = access_record.get("expires_at")

        # Check if expired
        if expires_at:
            try:
                expires = datetime.fromisoformat(
                    expires_at.replace("Z", "+00:00")
                )
                if expires < datetime.now(timezone.utc):
                    return {
                        "has_access": False,
                        "status": "expired",
                        "expires_at": expires_at,
                        "message": "Access has expired",
                    }
            except Exception:
                pass

        is_active = status == self.ACCESS_ACTIVE

        return {
            "has_access": is_active,
            "status": status or "unknown",
            "expires_at": expires_at,
            "message": "Access granted" if is_active else "Access inactive",
        }

    # ================================================================
    # USER SERVICES
    # ================================================================

    async def get_user_services(
        self,
        user_id: str,
    ) -> Dict[str, bool]:

        services = {}

        response = (
            self.supabase
            .table("user_services")
            .select(
                "status,expires_at,services(code)"
            )
            .eq("user_id", user_id)
            .execute()
        )

        now = datetime.now(timezone.utc)

        if response.data:
            for row in response.data:
                service = row.get("services") or {}
                code = service.get("code")

                if not code:
                    continue

                active = row.get("status") == self.ACCESS_ACTIVE
                expires = row.get("expires_at")

                if expires:
                    try:
                        expiry = datetime.fromisoformat(
                            expires.replace("Z", "+00:00")
                        )
                        active = active and expiry > now
                    except Exception:
                        pass

                services[code] = active

        return services

    async def get_user_payments(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:

        return await self.repository.get_user_payments(
            user_id
        )

    # ================================================================
    # AVAILABLE SERVICES
    # ================================================================

    async def get_available_services(
        self,
    ) -> List[Dict[str, Any]]:

        active = await self._get_service_active_column()

        # Check cache
        if self._services_cache and self._cache_time:
            if (datetime.now(timezone.utc) - self._cache_time).seconds < self._cache_ttl:
                return self._services_cache

        try:
            response = (
                self.supabase
                .table("services")
                .select("*")
                .eq(active, True)
                .order("display_order")
                .execute()
            )
        except Exception:
            response = (
                self.supabase
                .table("services")
                .select("*")
                .eq(active, True)
                .order("id")
                .execute()
            )

        services = response.data or []

        # Update cache
        self._services_cache = services
        self._cache_time = datetime.now(timezone.utc)

        return services

    # ================================================================
    # CLEANUP
    # ================================================================

    async def cleanup_stale_payments(
        self,
    ) -> int:

        if self.stk_push:
            return await self.stk_push.cleanup_stale_payments()
        return 0

    # ================================================================
    # HEALTH CHECK
    # ================================================================

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check.
        """

        status = {
            "database": False,
            "stk_push": False,
        }

        # Check database
        try:
            self.supabase.table("services") \
                .select("id") \
                .limit(1) \
                .execute()
            status["database"] = True
        except Exception:
            pass

        # Check STK Push
        if self.stk_push:
            try:
                status["stk_push"] = True
            except Exception:
                pass

        overall = "healthy" if status["database"] and status["stk_push"] else "unhealthy"

        return {
            "status": overall,
            "checks": status,
        }
