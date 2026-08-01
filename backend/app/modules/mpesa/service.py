# app/modules/mpesa/service.py
# Auto-D Kenya - M-Pesa Service
# ================================================================
# TYPE: MODULE - M-Pesa business logic

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException, AppException
from app.modules.mpesa.repository import MpesaRepository
from app.modules.mpesa.stk_push import StkPushService

logger = logging.getLogger(__name__)


class MpesaService:
    """M-Pesa service for payment processing."""
    
    def __init__(self):
        self.repository = MpesaRepository()
        self.stk_push = StkPushService()
        self.supabase = get_supabase()

    # ─── INITIATE PAYMENT ──────────────────────────────────────────

    async def initiate_payment(
        self,
        phone: str,
        service_id: str,
        description: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        amount: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Initiate M-Pesa payment.
        
        Args:
            phone: Phone number (without country code)
            service_id: Service code (e.g., "valuation", "mileage", "ownership")
            description: Transaction description (ignored - uses service name from DB)
            user_id: User ID (optional)
            request_id: Request ID (optional)
            amount: Amount to charge (optional, overrides service price if provided)
            
        Returns:
            Dict with checkout_request_id, message, and status
        """
        # ─── STEP 1: Look up service in the services table ──────────────
        service = (
            self.supabase
            .table("services")
            .select("*")
            .eq("code", service_id)
            .eq("active", True)
            .single()
            .execute()
        )
        
        if not service.data:
            raise NotFoundException(f"Service '{service_id}' not found")
        
        service_data = service.data
        
        # ─── STEP 2: Extract all data from the service record ──────────
        service_db_id = service_data["id"]
        service_name = service_data["name"]
        price = float(service_data["price"])
        currency = service_data.get("currency", "KES")
        
        # Allow amount override if provided
        if amount is not None:
            price = float(amount)
            logger.info(f"Amount override: using {price} instead of database price {service_data['price']}")
        
        logger.info(f"Service found: {service_name} (ID: {service_db_id}) - Price: {currency} {price}")
        
        # Generate checkout ID
        checkout_id = f"CHK-{service_id[:4]}-{str(int(datetime.utcnow().timestamp()))[-6:]}"
        
        # ─── STEP 3: Initiate STK Push ──────────────────────────────────
        result = await self.stk_push.initiate_push(
            phone=phone,
            amount=price,
            description=service_name,
            checkout_request_id=checkout_id,
            user_id=user_id,
            service_id=service_id
        )
        
        # ─── STEP 4: Save the payment record ────────────────────────────
        await self.repository.create_payment({
            "user_id": user_id,
            "request_id": request_id,
            "service_id": service_db_id,
            "service_name": service_name,
            "amount": price,
            "currency": currency,
            "phone": phone,
            "checkout_request_id": result["checkout_request_id"],
            "merchant_request_id": result.get("merchant_request_id"),
            "status": "pending",
        })
        
        logger.info(f"Payment initiated: {result['checkout_request_id']} for service {service_id} ({service_name}) - Amount: {currency} {price}")
        
        return {
            "checkout_request_id": result["checkout_request_id"],
            "message": result.get("customer_message", "STK push sent successfully"),
            "status": "pending"
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
        
        Args:
            checkout_request_id: Checkout request ID
            user_id: User ID
            
        Returns:
            Dict with confirmation status
        """
        payment = await self.repository.get_payment_by_checkout_id(checkout_request_id)
        if not payment or payment.get("user_id") != user_id:
            raise NotFoundException("Payment not found")
        
        if payment.get("status") == "completed":
            return {"status": "completed", "message": "Payment already confirmed"}
        
        if payment.get("status") != "paid":
            raise AppException("Payment not yet confirmed by M-Pesa", status_code=409)
        
        # Update payment status
        await self.repository.update_payment_status(checkout_request_id, "completed")
        
        # Unlock service
        if payment.get("user_id") and payment.get("service_id"):
            await self.unlock_service(payment["user_id"], payment["service_id"])
        
        logger.info(f"Payment confirmed: {checkout_request_id} for user {user_id}")
        
        return {"status": "completed", "message": "Payment confirmed"}

    # ─── SERVICE ACCESS ─────────────────────────────────────────────

    async def check_service_access(self, user_id: str, service_code: str) -> Dict[str, Any]:
        """
        Check if a user has access to a service.
        
        Args:
            user_id: User ID
            service_code: Service code (e.g., "valuation", "mileage")
            
        Returns:
            Dict with has_access boolean and details
        """
        try:
            # First get the service ID from code
            service = (
                self.supabase
                .table("services")
                .select("id")
                .eq("code", service_code)
                .eq("active", True)
                .single()
                .execute()
            )
            
            if not service.data:
                return {
                    "has_access": False,
                    "status": "service_not_found",
                    "message": f"Service '{service_code}' not found"
                }
            
            service_id = service.data["id"]
            
            # Check user_services table
            response = (
                self.supabase
                .table("user_services")
                .select("*")
                .eq("user_id", user_id)
                .eq("service_id", service_id)
                .execute()
            )
            
            if not response.data or len(response.data) == 0:
                return {
                    "has_access": False,
                    "status": "no_record",
                    "message": "No access record found"
                }
            
            record = response.data[0]
            status = record.get("status")
            expires_at = record.get("expires_at")
            
            # Check if expired
            if expires_at:
                try:
                    expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    if datetime.utcnow() > expires:
                        return {
                            "has_access": False,
                            "status": "expired",
                            "message": "Access has expired"
                        }
                except:
                    pass
            
            # Check if active
            if status in ["active", "completed", "paid", "success"]:
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
                
        except Exception as e:
            logger.error(f"Error checking service access: {e}")
            return {
                "has_access": False,
                "status": "error",
                "message": str(e)
            }

    async def unlock_service(self, user_id: str, service_id: str, payment_id: Optional[int] = None) -> None:
        """
        Unlock a service for a user.
        
        Args:
            user_id: User ID
            service_id: Service ID (numeric - the id from the services table)
            payment_id: Payment ID (optional)
        """
        try:
            # Check if user already has this service
            existing = (
                self.supabase
                .table("user_services")
                .select("*")
                .eq("user_id", user_id)
                .eq("service_id", service_id)
                .execute()
            )
            
            expires_at = (datetime.utcnow() + timedelta(days=365)).isoformat()
            
            if existing.data:
                # Update existing record
                update_data = {
                    "status": "active",
                    "expires_at": expires_at,
                    "updated_at": datetime.utcnow().isoformat()
                }
                if payment_id:
                    update_data["payment_id"] = payment_id
                
                self.supabase.table("user_services").update(update_data).eq("id", existing.data[0]["id"]).execute()
                logger.info(f"User service updated: user={user_id}, service={service_id}")
            else:
                # Create new record
                insert_data = {
                    "user_id": user_id,
                    "service_id": service_id,
                    "status": "active",
                    "expires_at": expires_at,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                if payment_id:
                    insert_data["payment_id"] = payment_id
                
                self.supabase.table("user_services").insert(insert_data).execute()
                logger.info(f"User service created: user={user_id}, service={service_id}")
            
        except Exception as e:
            logger.error(f"Error unlocking service: {str(e)}")
            raise

    # ─── USER SERVICES ──────────────────────────────────────────────

    async def get_user_services(self, user_id: str) -> Dict[str, bool]:
        """
        Get all services a user has access to.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with service_code as key and boolean access status
        """
        try:
            response = (
                self.supabase
                .table("user_services")
                .select("services(code, name, price, description, icon)")
                .eq("user_id", user_id)
                .eq("status", "active")
                .execute()
            )
            
            services = {}
            now = datetime.utcnow()
            
            if response.data:
                for record in response.data:
                    service = record.get("services", {})
                    code = service.get("code")
                    if code:
                        # Check expiry
                        expires_at = record.get("expires_at")
                        is_expired = False
                        if expires_at:
                            try:
                                expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                                if now > expires:
                                    is_expired = True
                            except:
                                pass
                        
                        services[code] = not is_expired
            
            return services
            
        except Exception as e:
            logger.error(f"Error getting user services: {e}")
            return {}

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
        
        Args:
            user_id: User ID
            
        Returns:
            List of service codes (strings from the services table code column)
        """
        try:
            response = (
                self.supabase
                .table("user_services")
                .select("services(code)")
                .eq("user_id", user_id)
                .eq("status", "active")
                .execute()
            )
            
            services = []
            for item in response.data:
                if item.get("services") and item["services"].get("code"):
                    services.append(item["services"]["code"])
            
            logger.info(f"User {user_id} has {len(services)} paid services")
            return services
            
        except Exception as e:
            logger.error(f"Error getting user paid services: {str(e)}")
            return []

    # ─── AVAILABLE SERVICES ─────────────────────────────────────────

    async def get_available_services(self) -> List[Dict[str, Any]]:
        """
        Get all available services.
        
        Returns:
            List of services from the database
        """
        try:
            response = (
                self.supabase
                .table("services")
                .select("*")
                .eq("active", True)
                .order("display_order", ascending=True)
                .execute()
            )
            
            logger.info(f"Found {len(response.data)} available services")
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting available services: {str(e)}")
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
            response = (
                self.supabase
                .table("services")
                .select("*")
                .eq("code", service_code)
                .eq("active", True)
                .single()
                .execute()
            )
            
            return response.data if response.data else None
            
        except Exception as e:
            logger.error(f"Error getting service by code {service_code}: {str(e)}")
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
        Handle M-Pesa callback.
        
        This is the ONLY place where services should be unlocked.
        
        Args:
            checkout_request_id: Checkout request ID
            result_code: Result code (0 = success)
            result_desc: Result description
            receipt: M-Pesa receipt number
            amount: Amount paid
            phone: Phone number that paid
            transaction_date: Transaction date
            callback_payload: Full callback payload
            
        Returns:
            Dict with update status
        """
        try:
            # Get payment
            payment = await self.repository.get_payment_by_checkout_id(checkout_request_id)
            if not payment:
                logger.warning(f"Payment not found for callback: {checkout_request_id}")
                return {"status": "not_found", "message": "Payment not found"}
            
            # Update payment from callback
            updated = await self.repository.update_payment_from_callback(
                checkout_request_id=checkout_request_id,
                result_code=result_code,
                result_desc=result_desc,
                receipt=receipt,
                amount=amount,
                phone=phone,
                transaction_date=transaction_date,
                callback_payload=callback_payload
            )
            
            # ─── UNLOCK SERVICE ONLY ON SUCCESS (ResultCode == 0) ─────
            if result_code == "0" and payment.get("user_id") and payment.get("service_id"):
                await self.unlock_service(
                    user_id=payment["user_id"],
                    service_id=payment["service_id"],
                    payment_id=payment.get("id")
                )
                logger.info(f"✅ Service unlocked via callback for {checkout_request_id}")
            else:
                logger.warning(f"Callback failed: {result_code} - {result_desc}")
            
            return {
                "status": "updated",
                "message": "Callback processed successfully",
                "payment": updated
            }
            
        except Exception as e:
            logger.error(f"Error handling callback: {str(e)}")
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
