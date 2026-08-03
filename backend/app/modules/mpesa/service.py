# app/modules/mpesa/service.py
"""
Auto-D Kenya - M-Pesa Service
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List, Union

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException, AppException, ValidationException
from app.modules.mpesa.repository import MpesaRepository
from app.modules.mpesa.stk_push import StkPushService, mask_sensitive, normalize_phone

logger = logging.getLogger(__name__)


class MpesaService:
    """M-Pesa service for payment processing."""

    def __init__(self):
        self.repository = MpesaRepository()
        self.stk_push = StkPushService()
        # Cache for service active column detection
        self._service_active_column: Optional[str] = None

    @property
    def supabase(self):
        """Get fresh Supabase client instance."""
        client = get_supabase()
        if client is None:
            raise AppException("Supabase client is not initialized")
        return client

    # ─── SERVICE ACTIVE COLUMN DETECTION ──────────────────────────

    async def _get_service_active_column(self) -> str:
        """
        Detect whether the services table uses 'active' or 'is_active'.
        Reuses the same logic as StkPushService.
        """
        if self._service_active_column:
            return self._service_active_column

        try:
            supabase = self.supabase
            result = supabase.table("services").select("*").limit(1).execute()
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
            logger.warning(f"Could not detect services active-column, defaulting to 'active' | error={e}")
            self._service_active_column = "active"

        return self._service_active_column

    # ─── SHARED SERVICE ACCESS EVALUATOR ──────────────────────────

    def _evaluate_service_access(self, record: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fix #1: Shared helper for evaluating service access from a user_services record.
        This avoids code duplication between check_service_access and check_service_access_by_id.
        """
        if not record:
            return {
                "has_access": False,
                "status": "no_record",
                "message": "No access record found"
            }
        
        status = record.get("status")
        expires_at = record.get("expires_at")
        
        # Check if expired
        if expires_at:
            try:
                expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if datetime.now(timezone.utc) > expires:
                    return {
                        "has_access": False,
                        "status": "expired",
                        "message": "Access has expired"
                    }
            except (ValueError, TypeError):
                pass
        
        # Only "active" status grants access
        if status == "active":
            return {
                "has_access": True,
                "status": status,
                "expires_at": expires_at,
                "message": "Access granted"
            }
        else:
            return {
                "has_access": False,
                "status": status,
                "message": f"Access status: {status}"
            }

    # ─── INITIATE PAYMENT ──────────────────────────────────────────

    async def initiate_payment(
        self,
        phone: str,
        service_id: Union[int, str],
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Initiate M-Pesa payment.
        
        Args:
            phone: Phone number (with country code)
            service_id: Service ID (int) or service code (str)
            description: Transaction description (optional)
            user_id: User ID
            amount: Amount to charge (overrides service price if provided)
            
        Returns:
            Dict with checkout_request_id, message, and status
        """
        # Get fresh Supabase client
        supabase = self.supabase

        logger.info(
            f"Initiating payment: service={service_id} "
            f"({type(service_id).__name__}), phone={mask_sensitive(phone)}"
        )

        # ─── STEP 1: Build query to find service ──────────────────────
        active_column = await self._get_service_active_column()
        
        query = supabase.table("services").select("*").eq(active_column, True)

        # Handle both numeric ID and string code
        if isinstance(service_id, int):
            query = query.eq("id", service_id)
        elif isinstance(service_id, str) and service_id.isdigit():
            query = query.eq("id", int(service_id))
        else:
            query = query.eq("code", str(service_id).lower())

        response = query.maybe_single().execute()

        if response is None:
            raise AppException("Supabase returned no response")

        if response.data is None:
            raise NotFoundException(f"Service '{service_id}' not found")

        service = response.data

        # ─── STEP 2: Extract service data ────────────────────────────
        service_db_id = service.get("id")
        service_name = service.get("name")
        
        if service_db_id is None:
            raise AppException("Service ID missing")
        if not service_name:
            raise AppException("Service name missing")

        price = float(service.get("price") or 0)
        currency = service.get("currency", "KES")

        # Validate service price - prevent KES 0 transactions
        if price <= 0:
            raise ValidationException(f"Invalid service price: {price}. Service '{service_name}' has an invalid price.")

        # Amount override - only allow if explicitly enabled
        if amount is not None:
            logger.warning(
                f"Amount override attempted but ignored | service={service_name} "
                f"requested_amount={amount} database_price={price}"
            )

        # Use description if provided, otherwise use service name
        final_description = description if description else service_name

        logger.info(
            "Service found",
            extra={
                "service_id": service_db_id,
                "service": service_name,
                "price": price,
                "currency": currency,
                "user_id": user_id
            }
        )

        # ─── STEP 3: Initiate STK Push ──────────────────────────────────
        try:
            result = await self.stk_push.initiate_push(
                phone=phone,
                amount=price,
                description=final_description,
                user_id=user_id,
                service_id=service_db_id,
            )
        except Exception as e:
            logger.exception("STK Push failed")
            raise AppException(f"Unable to initiate STK Push: {str(e)}", 500)

        # ─── STEP 4: Validate the response ─────────────────────────────
        if result is None:
            logger.error("initiate_push() returned None")
            raise AppException("Unable to initiate STK Push - no response")

        if not isinstance(result, dict):
            logger.error(f"Unexpected STK response: {result}")
            raise AppException("Invalid STK response")

        checkout_request_id = result.get("checkout_request_id")
        merchant_request_id = result.get("merchant_request_id")

        if not checkout_request_id:
            logger.error(f"STK Push did not return CheckoutRequestID: {result}")
            raise AppException(
                result.get("error", "M-Pesa did not accept the request.")
            )

        logger.info(
            "STK Push initiated",
            extra={
                "service": service_name,
                "amount": price,
                "checkout_request_id": mask_sensitive(checkout_request_id),
                "user_id": user_id
            }
        )

        # ─── STEP 5: Return response ──────────────────────────────────
        return {
            "success": True,
            "checkout_request_id": checkout_request_id,
            "merchant_request_id": merchant_request_id,
            "customer_message": result.get(
                "customer_message",
                "STK Push sent successfully."
            ),
            "status": result.get("status", "pending"),
            "response_code": result.get("response_code"),
            "response_description": result.get("response_description"),
        }

    # ─── PAYMENT STATUS ─────────────────────────────────────────────

    async def get_payment_status(self, checkout_request_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get payment status.
        
        Args:
            checkout_request_id: Checkout request ID
            user_id: User ID
            
        Returns:
            Dict with payment details
        """
        payment = await self.repository.get_payment_by_checkout_id(checkout_request_id)
        if not payment or payment.get("user_id") != user_id:
            raise NotFoundException("Payment not found")
        
        return {
            "status": payment.get("status"),
            "amount": payment.get("amount"),
            "phone": payment.get("phone"),
            "created_at": payment.get("created_at")
        }

    # ─── CONFIRM PAYMENT ────────────────────────────────────────────

    async def confirm_payment(self, checkout_request_id: str, user_id: str) -> Dict[str, Any]:
        """
        Confirm payment and unlock service.
        This is primarily for manual confirmation when callback fails.
        """
        payment = await self.repository.get_payment_by_checkout_id(checkout_request_id)
        if not payment or payment.get("user_id") != user_id:
            raise NotFoundException("Payment not found")
        
        status = payment.get("status")
        
        # Only "paid" can be confirmed
        if status != "paid":
            raise AppException(f"Payment not yet confirmed by M-Pesa. Current status: {status}", status_code=409)
        
        # Payment is paid, unlock service if needed
        if payment.get("user_id") and payment.get("service_id"):
            existing = await self._get_user_service(payment["user_id"], payment["service_id"])
            if existing and existing.get("status") == "active":
                return {"status": "paid", "message": "Service already active"}
            
            await self._unlock_service_atomic(
                user_id=payment["user_id"],
                service_id=payment["service_id"],
                payment_id=payment.get("id"),
            )
            logger.info(f"Service unlocked via manual confirmation: {checkout_request_id}")
            return {"status": "paid", "message": "Payment confirmed and service unlocked"}
        
        return {"status": "error", "message": "Missing user_id or service_id"}

    async def _get_user_service(self, user_id: str, service_id: int) -> Optional[Dict[str, Any]]:
        """Get a user's service record if it exists."""
        try:
            supabase = self.supabase
            result = (
                supabase
                .table("user_services")
                .select("*")
                .eq("user_id", user_id)
                .eq("service_id", service_id)
                .maybe_single()
                .execute()
            )
            return result.data if result and result.data else None
        except Exception:
            return None

    # ─── SERVICE ACCESS ─────────────────────────────────────────────

    async def check_service_access(self, user_id: str, service_code: str) -> Dict[str, Any]:
        """
        Check if a user has access to a service by code.
        
        Args:
            user_id: User ID
            service_code: Service code (e.g., "valuation", "mileage")
            
        Returns:
            Dict with has_access boolean and details
        """
        try:
            supabase = self.supabase
            active_column = await self._get_service_active_column()
            
            # First get the service ID from code
            service = (
                supabase
                .table("services")
                .select("id")
                .eq("code", service_code)
                .eq(active_column, True)
                .maybe_single()
                .execute()
            )
            
            if not service or not service.data:
                return {
                    "has_access": False,
                    "status": "service_not_found",
                    "message": f"Service '{service_code}' not found"
                }
            
            service_id = service.data["id"]
            
            # Check user_services table
            response = (
                supabase
                .table("user_services")
                .select("*")
                .eq("user_id", user_id)
                .eq("service_id", service_id)
                .maybe_single()
                .execute()
            )
            
            # Use shared evaluator
            return self._evaluate_service_access(response.data if response else None)
                
        except Exception as e:
            logger.error(f"Error checking service access: {e}")
            return {
                "has_access": False,
                "status": "error",
                "message": str(e)
            }

    async def check_service_access_by_id(self, user_id: str, service_id: int) -> Dict[str, Any]:
        """
        Fix #1: Check if a user has access to a service by ID.
        Uses shared _evaluate_service_access() helper.
        
        Args:
            user_id: User ID
            service_id: Service ID (numeric)
            
        Returns:
            Dict with has_access boolean and details
        """
        try:
            supabase = self.supabase
            
            # Check user_services table directly by service_id
            response = (
                supabase
                .table("user_services")
                .select("*")
                .eq("user_id", user_id)
                .eq("service_id", service_id)
                .maybe_single()
                .execute()
            )
            
            # Use shared evaluator
            return self._evaluate_service_access(response.data if response else None)
            
        except Exception as e:
            logger.error(f"Error checking service access by ID: {e}")
            return {
                "has_access": False,
                "status": "error",
                "message": str(e)
            }

    # ─── ATOMIC UNLOCK SERVICE ──────────────────────────────────────

    def _unlock_service_atomic_sync(
        self,
        supabase,
        user_id: str,
        service_id: int,
        payment_id: Optional[int] = None,
        expires_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        TRUE ATOMIC UPSERT using PostgreSQL ON CONFLICT.
        This is the CORRECT atomic operation - no race conditions.
        
        REQUIRES: UNIQUE(user_id, service_id) constraint on user_services.
        
        ALTER TABLE user_services 
        ADD CONSTRAINT user_services_unique 
        UNIQUE(user_id, service_id);
        """
        now = datetime.now(timezone.utc).isoformat()
        if expires_at is None:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()

        # TRUE atomic UPSERT - single operation, no race condition
        row = {
            "user_id": user_id,
            "service_id": service_id,
            "status": "active",
            "expires_at": expires_at,
            "created_at": now,  # Only used for new records (ignored on update)
            "updated_at": now,
        }
        if payment_id:
            row["payment_id"] = payment_id

        # Atomic UPSERT with ON CONFLICT
        result = supabase.table("user_services").upsert(
            row,
            on_conflict="user_id,service_id"
        ).execute()
        
        return result.data[0] if result and result.data else row

    async def _unlock_service_atomic(
        self,
        user_id: str,
        service_id: int,
        payment_id: Optional[int] = None,
        callback_amount: Optional[float] = None,
        expected_amount: Optional[float] = None,
        expires_at: Optional[str] = None,
    ) -> None:
        """
        Atomic unlock service with executor to avoid blocking event loop.
        
        Args:
            user_id: User ID
            service_id: Service ID
            payment_id: Payment ID (optional)
            callback_amount: Amount from callback (for validation)
            expected_amount: Expected amount from payment record
            expires_at: Expiry date (optional, defaults to 365 days)
        """
        try:
            supabase = self.supabase
            
            # Amount validation - strict equality
            if callback_amount is not None and expected_amount is not None:
                callback_dec = Decimal(str(callback_amount)).quantize(Decimal('0.01'))
                expected_dec = Decimal(str(expected_amount)).quantize(Decimal('0.01'))
                
                if callback_dec != expected_dec:
                    logger.error(
                        f"Amount mismatch - rejecting unlock | "
                        f"callback_amount={callback_dec} expected={expected_dec}"
                    )
                    raise ValidationException(
                        f"Amount mismatch: callback {callback_dec} != expected {expected_dec}"
                    )

            # Run in executor to avoid blocking event loop
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                self._unlock_service_atomic_sync,
                supabase,
                user_id,
                service_id,
                payment_id,
                expires_at,
            )

            logger.info(
                "Service unlocked atomically",
                extra={
                    "user_id": user_id,
                    "service_id": service_id,
                    "payment_id": payment_id,
                    "expires_at": expires_at
                }
            )
            
        except Exception as e:
            logger.exception(f"Error unlocking service: {str(e)}")
            raise

    # ─── UNLOCK SERVICE (PUBLIC) ────────────────────────────────────

    async def unlock_service(
        self, 
        user_id: str, 
        service_id: int, 
        payment_id: Optional[int] = None,
        callback_amount: Optional[float] = None,
        expected_amount: Optional[float] = None,
        expires_at: Optional[str] = None,
    ) -> None:
        """
        Public wrapper for atomic unlock service.
        
        Args:
            user_id: User ID
            service_id: Service ID
            payment_id: Payment ID (optional)
            callback_amount: Amount from callback (for validation)
            expected_amount: Expected amount from payment record
            expires_at: Expiry date (optional)
        """
        await self._unlock_service_atomic(
            user_id=user_id,
            service_id=service_id,
            payment_id=payment_id,
            callback_amount=callback_amount,
            expected_amount=expected_amount,
            expires_at=expires_at,
        )

    # ─── USER SERVICES ──────────────────────────────────────────────

    async def _load_user_services(self, user_id: str, include_details: bool = False) -> Dict[str, Any]:
        """
        Common method for loading user services.
        Avoids code duplication between get_user_services and get_user_services_details.
        """
        try:
            supabase = self.supabase
            
            response = (
                supabase
                .table("user_services")
                .select("""
                    expires_at,
                    status,
                    services(
                        code,
                        name,
                        price,
                        description,
                        icon
                    )
                """)
                .eq("user_id", user_id)
                .eq("status", "active")
                .execute()
            )
            
            services = {}
            now = datetime.now(timezone.utc)
            
            if response and response.data:
                for record in response.data:
                    service = record.get("services", {})
                    code = service.get("code")
                    if code:
                        expires_at = record.get("expires_at")
                        is_expired = False
                        if expires_at:
                            try:
                                expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                                if now > expires:
                                    is_expired = True
                            except (ValueError, TypeError):
                                pass
                        
                        if include_details:
                            services[code] = {
                                "has_access": not is_expired,
                                "expires_at": expires_at,
                                "status": record.get("status"),
                                "name": service.get("name"),
                                "price": service.get("price"),
                                "description": service.get("description"),
                                "icon": service.get("icon"),
                            }
                        else:
                            services[code] = not is_expired
            
            return services
            
        except Exception as e:
            logger.exception(f"Error loading user services: {e}")
            return {}

    async def get_user_services(self, user_id: str) -> Dict[str, bool]:
        """
        Get all services a user has access to.
        Returns Dict[str, bool] - key is service code, value is access boolean.
        """
        return await self._load_user_services(user_id, include_details=False)

    async def get_user_services_details(self, user_id: str) -> Dict[str, Any]:
        """
        Get all services a user has access to with full details.
        """
        return await self._load_user_services(user_id, include_details=True)

    async def get_user_payments(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all payments for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of payments
        """
        return await self.repository.get_user_payments(user_id)

    async def get_user_paid_services(self, user_id: str) -> List[str]:
        """
        Get all paid service codes for a user.
        Includes expires_at to properly filter expired services.
        """
        try:
            supabase = self.supabase
            
            response = (
                supabase
                .table("user_services")
                .select("""
                    expires_at,
                    services(code)
                """)
                .eq("user_id", user_id)
                .eq("status", "active")
                .execute()
            )
            
            services = []
            now = datetime.now(timezone.utc)
            
            if response and response.data:
                for item in response.data:
                    expires_at = item.get("expires_at")
                    is_expired = False
                    if expires_at:
                        try:
                            expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                            if now > expires:
                                is_expired = True
                        except (ValueError, TypeError):
                            pass
                    
                    if not is_expired and item.get("services") and item["services"].get("code"):
                        services.append(item["services"]["code"])
            
            logger.info(f"User {user_id} has {len(services)} paid services")
            return services
            
        except Exception as e:
            logger.exception(f"Error getting user paid services: {str(e)}")
            return []

    # ─── AVAILABLE SERVICES ─────────────────────────────────────────

    async def get_available_services(self) -> List[Dict[str, Any]]:
        """
        Fix #4: Get all available services.
        Uses correct Supabase order() syntax without 'ascending' parameter.
        """
        try:
            supabase = self.supabase
            active_column = await self._get_service_active_column()
            
            try:
                # Fix #4: Correct order() syntax - no 'ascending' parameter
                response = (
                    supabase
                    .table("services")
                    .select("*")
                    .eq(active_column, True)
                    .order("display_order")
                    .execute()
                )
            except Exception:
                # Fallback to ordering by id if display_order doesn't exist
                response = (
                    supabase
                    .table("services")
                    .select("*")
                    .eq(active_column, True)
                    .order("id")
                    .execute()
                )
            
            if response and response.data:
                logger.info(f"Found {len(response.data)} available services")
                return response.data
            
            return []
            
        except Exception as e:
            logger.exception(f"Error getting available services: {str(e)}")
            return []

    async def get_service_by_code(self, service_code: str) -> Optional[Dict[str, Any]]:
        """
        Get a service by its code.
        
        Args:
            service_code: Service code (e.g., "valuation", "mileage")
            
        Returns:
            Service data or None if not found
        """
        try:
            supabase = self.supabase
            active_column = await self._get_service_active_column()
            
            response = (
                supabase
                .table("services")
                .select("*")
                .eq("code", service_code)
                .eq(active_column, True)
                .maybe_single()
                .execute()
            )
            
            return response.data if response and response.data else None
            
        except Exception as e:
            logger.exception(f"Error getting service by code {service_code}: {str(e)}")
            return None

    # ─── CALLBACK HANDLING ──────────────────────────────────────────

    async def handle_callback(
        self,
        checkout_request_id: str,
        result_code: str,
        result_desc: str,
        receipt: Optional[str] = None,
        amount: Optional[float] = None,
        phone: Optional[str] = None,
        transaction_date: Optional[str] = None,
        callback_payload: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Handle M-Pesa callback with proper validation.
        This is the ONLY place where services should be unlocked.
        """
        try:
            # Get payment
            payment = await self.repository.get_payment_by_checkout_id(checkout_request_id)
            if not payment:
                logger.warning(f"Payment not found for callback: {checkout_request_id}")
                return {"status": "not_found", "message": "Payment not found"}
            
            # Normalize phone numbers before comparison
            if phone and payment.get("phone"):
                callback_phone = normalize_phone(phone)
                stored_phone = normalize_phone(payment.get("phone"))
                if callback_phone != stored_phone:
                    logger.error(
                        f"Phone mismatch - rejecting callback | "
                        f"callback_phone={mask_sensitive(callback_phone)} "
                        f"payment_phone={mask_sensitive(stored_phone)}"
                    )
                    return {"status": "rejected", "message": "Phone number mismatch"}
            
            # Use Decimal for money comparison - strict equality
            if amount is not None and payment.get("amount"):
                callback_dec = Decimal(str(amount)).quantize(Decimal('0.01'))
                expected_dec = Decimal(str(payment.get("amount", 0))).quantize(Decimal('0.01'))
                
                if callback_dec != expected_dec:
                    logger.error(
                        f"Amount mismatch - rejecting callback | "
                        f"callback_amount={callback_dec} expected={expected_dec}"
                    )
                    return {"status": "rejected", "message": "Amount mismatch"}
            
            # Update payment and ensure repository returns the updated row
            updated_payment = await self.repository.update_payment_from_callback(
                checkout_request_id=checkout_request_id,
                result_code=result_code,
                result_desc=result_desc,
                receipt=receipt,
                amount=amount,
                phone=phone,
                transaction_date=transaction_date,
                callback_payload=callback_payload
            )
            
            # Handle case where repository returns bool or None
            if updated_payment is None or isinstance(updated_payment, bool):
                updated_payment = await self.repository.get_payment_by_checkout_id(checkout_request_id)
                if not updated_payment:
                    logger.error(f"Failed to fetch updated payment: {checkout_request_id}")
                    return {"status": "error", "message": "Failed to fetch updated payment"}
            
            # Only unlock after payment is paid
            if str(result_code) == "0" and updated_payment.get("status") == "paid":
                if updated_payment.get("user_id") and updated_payment.get("service_id"):
                    # Check if already unlocked
                    existing = await self._get_user_service(
                        updated_payment["user_id"], 
                        updated_payment["service_id"]
                    )
                    
                    if not existing or existing.get("status") != "active":
                        await self._unlock_service_atomic(
                            user_id=updated_payment["user_id"],
                            service_id=updated_payment["service_id"],
                            payment_id=updated_payment.get("id"),
                            callback_amount=amount,
                            expected_amount=updated_payment.get("amount"),
                        )
                        logger.info(f"✅ Service unlocked via callback for {checkout_request_id}")
                    else:
                        logger.info(f"Service already active, skipping unlock: {checkout_request_id}")
                else:
                    logger.warning(f"Payment missing user_id or service_id: {checkout_request_id}")
            elif str(result_code) == "0":
                logger.warning(
                    f"Payment status not 'paid' after update: {updated_payment.get('status')} | "
                    f"checkout_request_id={checkout_request_id}"
                )
            else:
                logger.warning(f"Callback failed: {result_code} - {result_desc}")
            
            return {
                "status": "updated",
                "message": "Callback processed successfully",
                "payment": updated_payment
            }
            
        except ValidationException as e:
            logger.error(f"Validation error in callback: {str(e)}")
            return {"status": "rejected", "message": str(e)}
        except Exception as e:
            logger.exception(f"Error handling callback: {str(e)}")
            raise

    # ─── CHECK PAYMENT ACCESS ───────────────────────────────────────

    async def check_payment_access(self, user_id: str, service_code: str) -> Dict[str, Any]:
        """
        Check payment access for a service.
        
        Args:
            user_id: User ID
            service_code: Service code
            
        Returns:
            Dict with has_access boolean
        """
        return await self.check_service_access(user_id, service_code)

    # ─── CLEANUP ─────────────────────────────────────────────────────

    async def cleanup_stale_payments(self) -> int:
        """
        Clean up stale pending payments.
        
        Returns:
            Number of payments marked as expired
        """
        return await self.stk_push.cleanup_stale_payments()
