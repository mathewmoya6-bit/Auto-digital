# app/modules/mpesa/service.py
# Auto-D Kenya - M-Pesa Service
# ================================================================
# TYPE: MODULE - M-Pesa business logic

import logging
from datetime import datetime
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
            service_id: Service code (e.g., "instant_valuation")
            description: Transaction description
            user_id: User ID (optional)
            request_id: Request ID (optional) - not used in payment creation
            amount: Amount to charge (optional, uses service price)
            
        Returns:
            Dict with checkout_request_id, message, and status
        """
        # Get service details
        service = (
            self.supabase
                .table("services")
                .select("*")
                .eq("code", service_id)
                .eq("active", True)
                .execute()
        )
        
        if not service.data:
            raise NotFoundException(f"Service not found: {service_id}")
        
        service_data = service.data[0]
        price = amount or float(service_data.get("price", 0))
        
        # Generate checkout ID
        checkout_id = f"CHK-{service_id[:4]}-{str(int(datetime.utcnow().timestamp()))[-6:]}"
        
        # Initiate STK Push
        result = await self.stk_push.initiate_push(
            phone=phone,
            amount=price,
            description=description or service_data.get("name", "Auto-D Kenya Service"),
            checkout_request_id=checkout_id,
            user_id=user_id,
            service_id=service_id
        )
        
        # ✅ FIX 1: Removed request_id from payment creation
        await self.repository.create_payment({
            "user_id": user_id,
            
            # Numeric ID from the services table (bigint)
            "service_id": service_data["id"],
            
            # Human-readable name
            "service_name": service_data["name"],
            
            "amount": price,
            "currency": "KES",
            
            "phone": phone,
            
            "checkout_request_id": result["checkout_request_id"],
            "merchant_request_id": result.get("merchant_request_id"),
            
            "status": "pending",
        })
        
        logger.info(f"Payment initiated: {result['checkout_request_id']} for service {service_id}")
        
        return {
            "checkout_request_id": result["checkout_request_id"],
            "message": result.get("customer_message", "STK push sent successfully"),
            "status": "pending"
        }

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

    async def unlock_service(self, user_id: str, service_id: str) -> None:
        """
        Unlock a service for a user.
        
        Args:
            user_id: User ID
            service_id: Service ID (numeric)
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
            
            if existing.data:
                # Update existing record
                self.supabase.table("user_services").update({
                    "status": "active",
                    "purchased_at": datetime.utcnow().isoformat()
                }).eq("id", existing.data[0]["id"]).execute()
            else:
                # Create new record
                self.supabase.table("user_services").insert({
                    "user_id": user_id,
                    "service_id": service_id,
                    "status": "active",
                    "purchased_at": datetime.utcnow().isoformat()
                }).execute()
            
            logger.info(f"Service {service_id} unlocked for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error unlocking service: {str(e)}")
            raise

    async def get_user_services(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all services for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of user services with service details
        """
        try:
            response = (
                self.supabase
                    .table("user_services")
                    .select("*, services(*)")
                    .eq("user_id", user_id)
                    .execute()
            )
            
            logger.info(f"Found {len(response.data)} services for user {user_id}")
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting user services: {str(e)}")
            return []

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
            List of service codes
        """
        try:
            # Get paid services from user_services
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

    async def get_available_services(self) -> List[Dict[str, Any]]:
        """
        Get all available services.
        
        Returns:
            List of services
        """
        try:
            response = (
                self.supabase
                    .table("services")
                    .select("*")
                    .eq("active", True)
                    .order("name")
                    .execute()
            )
            
            logger.info(f"Found {len(response.data)} available services")
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting available services: {str(e)}")
            return []

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
            
            # If successful, unlock service
            if result_code == "0" and payment.get("user_id") and payment.get("service_id"):
                await self.unlock_service(payment["user_id"], payment["service_id"])
                logger.info(f"Service unlocked via callback for {checkout_request_id}")
            
            return {
                "status": "updated",
                "message": "Callback processed successfully",
                "payment": updated
            }
            
        except Exception as e:
            logger.error(f"Error handling callback: {str(e)}")
            raise
