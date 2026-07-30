# app/modules/mpesa/service.py
# Auto-D Kenya - M-Pesa Service
# ================================================================
# TYPE: MODULE - M-Pesa business logic

import logging
from typing import Optional, Dict, Any

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException, AppException
from app.modules.mpesa.repository import MpesaRepository
from app.modules.mpesa.stk_push import StkPushService

logger = logging.getLogger(__name__)


class MpesaService:
    """M-Pesa service for business logic."""
    
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
        """Initiate M-Pesa payment."""
        # Get service details
        service = self.supabase.table("services").select("*").eq("id", service_id).eq("active", True).execute()
        if not service.data:
            raise NotFoundException("Service not found")
        
        service_data = service.data[0]
        price = amount or float(service_data.get("price", 0))
        
        # Initiate STK push
        checkout_id = f"CHK-{service_id[:4]}-{str(int(datetime.utcnow().timestamp()))[-6:]}"
        
        result = await self.stk_push.initiate_push(
            phone=phone,
            amount=price,
            description=description or service_data.get("name", "Auto-D Kenya Service"),
            checkout_request_id=checkout_id
        )
        
        # Save payment record
        await self.repository.create_payment({
            "user_id": user_id,
            "service_id": service_id,
            "checkout_request_id": result["checkout_request_id"],
            "phone": phone,
            "amount": price,
            "description": description or service_data.get("name"),
            "request_id": request_id
        })
        
        return {
            "checkout_request_id": result["checkout_request_id"],
            "message": result.get("customer_message", "STK push sent successfully"),
            "status": "pending"
        }
    
    async def get_payment_status(self, checkout_request_id: str) -> Dict[str, Any]:
        """Get payment status."""
        payment = await self.repository.get_payment_by_checkout_id(checkout_request_id)
        if not payment:
            raise NotFoundException("Payment not found")
        
        return {
            "status": payment.get("status"),
            "amount": payment.get("amount"),
            "phone": payment.get("phone"),
            "created_at": payment.get("created_at")
        }
    
    async def confirm_payment(self, checkout_request_id: str) -> Dict[str, Any]:
        """Confirm payment and unlock service."""
        payment = await self.repository.get_payment_by_checkout_id(checkout_request_id)
        if not payment:
            raise NotFoundException("Payment not found")
        
        if payment.get("status") == "completed":
            return {"status": "completed", "message": "Payment already confirmed"}
        
        # In production, this would verify with M-Pesa API
        # For now, we'll simulate confirmation
        await self.repository.update_payment_status(checkout_request_id, "completed")
        
        # Unlock service
        if payment.get("user_id") and payment.get("service_id"):
            await self.unlock_service(payment["user_id"], payment["service_id"])
        
        return {"status": "completed", "message": "Payment confirmed"}
    
    async def unlock_service(self, user_id: str, service_id: str) -> None:
        """Unlock a service for a user."""
        try:
            # Check if already exists
            existing = self.supabase.table("user_services").select("*").eq("user_id", user_id).eq("service_id", service_id).execute()
            
            if existing.data:
                # Update existing
                self.supabase.table("user_services").update({
                    "status": "active",
                    "purchased_at": datetime.utcnow().isoformat()
                }).eq("id", existing.data[0]["id"]).execute()
            else:
                # Create new
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
    
    async def get_user_services(self, user_id: str) -> list:
        """Get all services purchased by a user."""
        try:
            response = self.supabase.table("user_services").select("*, services(*)").eq("user_id", user_id).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting user services: {str(e)}")
            return []
    
    async def get_user_payments(self, user_id: str) -> list:
        """Get all payments for a user."""
        return await self.repository.get_user_payments(user_id)
