# app/modules/mpesa/repository.py
# Auto-D Kenya - M-Pesa Repository
# ================================================================
# TYPE: MODULE - M-Pesa database operations

import logging
from typing import Optional, List, Dict, Any
from uuid import uuid4

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class MpesaRepository:
    """M-Pesa repository for database operations."""
    
    def __init__(self):
        self.supabase = get_supabase()
    
    async def create_payment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a payment record."""
        try:
            payment_data = {
                "id": str(uuid4()),
                "user_id": data.get("user_id"),
                "service_id": data.get("service_id"),
                "checkout_request_id": data.get("checkout_request_id"),
                "phone": data.get("phone"),
                "amount": data.get("amount"),
                "status": "pending",
                "description": data.get("description"),
                "request_id": data.get("request_id"),
                "created_at": data.get("created_at")
            }
            response = self.supabase.table("mpesa_payments").insert(payment_data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}")
            raise
    
    async def get_payment_by_checkout_id(self, checkout_request_id: str) -> Optional[Dict[str, Any]]:
        """Get payment by checkout request ID."""
        try:
            response = self.supabase.table("mpesa_payments").select("*").eq("checkout_request_id", checkout_request_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting payment: {str(e)}")
            return None
    
    async def update_payment_status(self, checkout_request_id: str, status: str, transaction_id: Optional[str] = None) -> Dict[str, Any]:
        """Update payment status."""
        try:
            data = {"status": status}
            if transaction_id:
                data["transaction_id"] = transaction_id
            response = self.supabase.table("mpesa_payments").update(data).eq("checkout_request_id", checkout_request_id).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error updating payment: {str(e)}")
            raise
    
    async def get_user_payments(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all payments for a user."""
        try:
            response = self.supabase.table("mpesa_payments").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting user payments: {str(e)}")
            return []
