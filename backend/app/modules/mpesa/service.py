# app/modules/mpesa/service.py
# ================================================================
# Auto-D Kenya - M-Pesa Service
# ================================================================

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.exceptions import (
    AppException,
    NotFoundException,
    ValidationException,
)
from app.core.security import mask_sensitive
from app.modules.mpesa.stk_push import StkPushService

logger = logging.getLogger(__name__)


class MpesaService:
    """M-Pesa payment service orchestrator."""

    def __init__(self):
        """Initialize the M-Pesa service."""
        self.supabase = settings.SUPABASE_CLIENT
        self.stk_push = StkPushService() if settings.MPESA_ENABLED else None
        self._services_cache = None
        self._cache_time = None
        self._cache_ttl = 300  # 5 minutes

    # ================================================================
    # PAYMENT INITIATION
    # ================================================================

    async def initiate_payment(
        self,
        phone: str,
        service_id: int,
        description: Optional[str],
        user_id: str,
        amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Initiate an STK Push payment.

        Args:
            phone: Customer phone number
            service_id: ID of the service being purchased
            description: Optional description
            user_id: ID of the user making the payment
            amount: Optional amount (overrides service price)

        Returns:
            Dict containing checkout_request_id and status

        Raises:
            ValidationException: If service not found or invalid
            AppException: If payment initiation fails
        """
        # Validate phone number
        if not phone or len(phone) < 10:
            raise ValidationException("Valid phone number is required")

        # Get service details
        service = await self._get_service_by_id(service_id)
        if not service:
            raise NotFoundException(f"Service {service_id} not found")

        # Determine amount
        final_amount = amount or service.get("price", 0)
        if final_amount <= 0:
            raise ValidationException("Invalid payment amount")

        # Create payment record
        payment_data = {
            "user_id": user_id,
            "service_id": service_id,
            "amount": final_amount,
            "currency": service.get("currency", "KES"),
            "status": "pending",
            "description": description or service.get("name", "Service payment"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Insert payment record
            payment_result = await self.supabase.table("payments") \
                .insert(payment_data) \
                .execute()

            if not payment_result.data:
                raise AppException("Failed to create payment record")

            payment = payment_result.data[0]
            payment_id = payment.get("id")

            # Initiate STK Push
            if not self.stk_push:
                raise AppException("M-Pesa service is not configured")

            stk_result = await self.stk_push.initiate_stk_push(
                phone=phone,
                amount=final_amount,
                account_reference=f"PAY-{payment_id}",
                transaction_desc=payment_data["description"],
                callback_url=settings.MPESA_CALLBACK_URL,
            )

            # Update payment with checkout request ID
            await self.supabase.table("payments") \
                .update({
                    "checkout_request_id": stk_result["checkout_request_id"],
                    "mpesa_response": stk_result,
                }) \
                .eq("id", payment_id) \
                .execute()

            return {
                "checkout_request_id": stk_result["checkout_request_id"],
                "payment_id": payment_id,
                "status": "pending",
                "customer_message": stk_result.get("customer_message", "STK Push sent successfully."),
            }

        except Exception as e:
            logger.error(f"Payment initiation failed: {e}")
            raise AppException(f"Payment initiation failed: {str(e)}")

    # ================================================================
    # CALLBACK HANDLING
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
        callback_payload: Optional[Dict] = None,
    ) -> None:
        """
        Handle M-Pesa callback from Safaricom.

        Args:
            checkout_request_id: M-Pesa checkout request ID
            result_code: Result code (0 = success)
            result_desc: Result description
            receipt: M-Pesa receipt number
            amount: Transaction amount
            phone: Customer phone number
            transaction_date: Transaction date
            callback_payload: Full callback payload
        """
        try:
            # Find payment by checkout_request_id
            payment_result = await self.supabase.table("payments") \
                .select("*") \
                .eq("checkout_request_id", checkout_request_id) \
                .execute()

            if not payment_result.data:
                logger.warning(f"Payment not found: {checkout_request_id}")
                return

            payment = payment_result.data[0]
            payment_id = payment.get("id")
            user_id = payment.get("user_id")
            service_id = payment.get("service_id")

            # Determine status
            is_success = result_code == "0"
            status = "completed" if is_success else "failed"

            # Update payment record
            update_data = {
                "status": status,
                "result_code": result_code,
                "result_desc": result_desc,
                "callback_payload": callback_payload,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            if receipt:
                update_data["receipt_number"] = receipt
            if amount:
                update_data["amount"] = amount
            if phone:
                update_data["phone"] = phone
            if transaction_date:
                update_data["transaction_date"] = transaction_date

            await self.supabase.table("payments") \
                .update(update_data) \
                .eq("id", payment_id) \
                .execute()

            # If payment was successful, grant service access
            if is_success and user_id and service_id:
                await self._grant_service_access(
                    user_id=user_id,
                    service_id=service_id,
                    payment_id=payment_id,
                )

            logger.info(
                f"Callback processed: {checkout_request_id} -> {status}"
            )

        except Exception as e:
            logger.exception(f"Callback processing failed: {e}")
            # Re-raise to ensure the callback returns 200 OK
            # The outer handler will log but not fail
            raise

    # ================================================================
    # SERVICE ACCESS MANAGEMENT
    # ================================================================

    async def _grant_service_access(
        self,
        user_id: str,
        service_id: int,
        payment_id: int,
    ) -> None:
        """
        Grant a user access to a service after successful payment.

        Args:
            user_id: User ID
            service_id: Service ID
            payment_id: Payment ID
        """
        try:
            # Check if access already exists
            existing = await self.supabase.table("user_services") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("service_id", service_id) \
                .execute()

            expires_at = datetime.now(timezone.utc) + timedelta(days=365)

            if existing.data:
                # Update existing access
                await self.supabase.table("user_services") \
                    .update({
                        "expires_at": expires_at.isoformat(),
                        "payment_id": payment_id,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }) \
                    .eq("id", existing.data[0]["id"]) \
                    .execute()
            else:
                # Create new access record
                await self.supabase.table("user_services") \
                    .insert({
                        "user_id": user_id,
                        "service_id": service_id,
                        "payment_id": payment_id,
                        "expires_at": expires_at.isoformat(),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }) \
                    .execute()

            logger.info(
                f"Service access granted: user={user_id}, service={service_id}"
            )

        except Exception as e:
            logger.error(f"Failed to grant service access: {e}")
            # Don't re-raise - the payment is already processed

    async def check_service_access_by_id(
        self,
        user_id: str,
        service_id: int,
    ) -> Dict[str, Any]:
        """
        Check if a user has access to a specific service.

        Args:
            user_id: User ID
            service_id: Service ID

        Returns:
            Dict with has_access, status, expires_at, and message
        """
        try:
            # Get service first to check if it exists
            service = await self._get_service_by_id(service_id)
            if not service:
                return {
                    "has_access": False,
                    "status": "error",
                    "message": "Service not found",
                }

            # Check access
            result = await self.supabase.table("user_services") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("service_id", service_id) \
                .execute()

            if not result.data:
                return {
                    "has_access": False,
                    "status": "no_access",
                    "message": "No access to this service",
                }

            access = result.data[0]
            expires_at = access.get("expires_at")

            # Check if expired
            if expires_at:
                expires = datetime.fromisoformat(expires_at)
                if expires < datetime.now(timezone.utc):
                    return {
                        "has_access": False,
                        "status": "expired",
                        "expires_at": expires_at,
                        "message": "Access has expired",
                    }

            return {
                "has_access": True,
                "status": "active",
                "expires_at": expires_at,
                "message": "Access granted",
            }

        except Exception as e:
            logger.error(f"Failed to check service access: {e}")
            return {
                "has_access": False,
                "status": "error",
                "message": f"Failed to check access: {str(e)}",
            }

    # ================================================================
    # GET USER SERVICES
    # ================================================================

    async def get_user_services(self, user_id: str) -> Dict[str, bool]:
        """
        Get all services a user has access to.

        Args:
            user_id: User ID

        Returns:
            Dict mapping service_code -> has_access (bool)
        """
        try:
            # Get all services the user has access to
            result = await self.supabase.table("user_services") \
                .select("services(code)") \
                .eq("user_id", user_id) \
                .execute()

            services = {}
            for item in result.data or []:
                service = item.get("services", {})
                code = service.get("code")
                if code:
                    services[code] = True

            return services

        except Exception as e:
            logger.error(f"Failed to get user services: {e}")
            return {}

    async def get_user_payments(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get a user's payment history.

        Args:
            user_id: User ID

        Returns:
            List of payment records
        """
        try:
            result = await self.supabase.table("payments") \
                .select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get user payments: {e}")
            return []

    # ================================================================
    # GET PAYMENT STATUS
    # ================================================================

    async def get_payment_status(
        self,
        checkout_request_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get the status of a payment.

        Args:
            checkout_request_id: M-Pesa checkout request ID
            user_id: User ID (for authorization)

        Returns:
            Dict with payment status

        Raises:
            NotFoundException: If payment not found
            AppException: If user not authorized
        """
        try:
            result = await self.supabase.table("payments") \
                .select("*") \
                .eq("checkout_request_id", checkout_request_id) \
                .execute()

            if not result.data:
                raise NotFoundException("Payment not found")

            payment = result.data[0]

            # Check authorization
            if payment.get("user_id") != user_id:
                raise AppException("Not authorized to view this payment")

            # If payment is still pending and STK Push is available, check with M-Pesa
            if payment.get("status") == "pending" and self.stk_push:
                try:
                    stk_status = await self.stk_push.check_payment_status(
                        checkout_request_id
                    )

                    # Update payment if status changed
                    if stk_status.get("status") != "pending":
                        await self.supabase.table("payments") \
                            .update({
                                "status": stk_status.get("status"),
                                "result_code": stk_status.get("result_code"),
                                "result_desc": stk_status.get("result_desc"),
                                "updated_at": datetime.now(timezone.utc).isoformat(),
                            }) \
                            .eq("id", payment["id"]) \
                            .execute()

                        payment["status"] = stk_status.get("status")
                        payment["result_desc"] = stk_status.get("result_desc")

                except Exception as e:
                    logger.warning(f"Failed to check STK status: {e}")

            # Get service details
            service = await self._get_service_by_id(payment.get("service_id"))

            return {
                "status": payment.get("status", "unknown"),
                "message": payment.get("result_desc", "Payment in progress"),
                "amount": payment.get("amount", 0),
                "currency": payment.get("currency", "KES"),
                "service": service.get("name") if service else None,
                "receipt_number": payment.get("receipt_number"),
                "created_at": payment.get("created_at"),
                "completed_at": payment.get("updated_at"),
            }

        except Exception as e:
            if isinstance(e, (NotFoundException, AppException)):
                raise
            logger.error(f"Failed to get payment status: {e}")
            raise AppException(f"Failed to get payment status: {str(e)}")

    # ================================================================
    # AVAILABLE SERVICES
    # ================================================================

    async def get_available_services(self) -> List[Dict[str, Any]]:
        """
        Get all available services.

        Returns:
            List of service records
        """
        try:
            # Check cache
            if self._services_cache and self._cache_time:
                if (datetime.now(timezone.utc) - self._cache_time).seconds < self._cache_ttl:
                    return self._services_cache

            result = await self.supabase.table("services") \
                .select("*") \
                .eq("active", True) \
                .order("display_order") \
                .execute()

            services = result.data or []

            # Update cache
            self._services_cache = services
            self._cache_time = datetime.now(timezone.utc)

            return services

        except Exception as e:
            logger.error(f"Failed to get available services: {e}")
            return []

    async def _get_service_by_id(self, service_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a service by ID.

        Args:
            service_id: Service ID

        Returns:
            Service record or None
        """
        try:
            # Try cache first
            if self._services_cache:
                for service in self._services_cache:
                    if service.get("id") == service_id:
                        return service

            result = await self.supabase.table("services") \
                .select("*") \
                .eq("id", service_id) \
                .execute()

            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(f"Failed to get service by ID: {e}")
            return None

    # ================================================================
    # HEALTH CHECK
    # ================================================================

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check.

        Returns:
            Dict with health status
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
