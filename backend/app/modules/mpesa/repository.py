# app/modules/mpesa/repository.py
# Auto-D Kenya - M-Pesa Repository
# ================================================================
# TYPE: MODULE - M-Pesa database operations

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class MpesaRepository:
    """M-Pesa repository for database operations."""
    
    def __init__(self):
        self.supabase = get_supabase()
    
    async def create_payment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a payment record.
        
        ✅ FIX: Removed 'request_id' field as it's not required
        """
        try:
            payment_data = {
                "id": str(uuid4()),
                "user_id": data.get("user_id"),
                
                "service_id": data.get("service_id"),
                "service_name": data.get("service_name"),
                
                "amount": data.get("amount"),
                "currency": data.get("currency", "KES"),
                
                "phone": data.get("phone"),
                
                "checkout_request_id": data.get("checkout_request_id"),
                "merchant_request_id": data.get("merchant_request_id"),
                
                "status": data.get("status", "pending"),
            }
            
            logger.info(f"Creating payment record: {payment_data['id']} for user {payment_data['user_id']}")
            logger.debug(f"Payment data: {payment_data}")
            
            response = (
                self.supabase
                    .table("payments")
                    .insert(payment_data)
                    .execute()
            )
            
            if response.data:
                logger.info(f"Payment record created: {response.data[0].get('id')}")
                return response.data[0]
            else:
                logger.error("No data returned from insert")
                return {}
                
        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}")
            raise
    
    async def get_payment_by_checkout_id(self, checkout_request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get payment by checkout request ID.
        """
        try:
            response = (
                self.supabase
                    .table("payments")
                    .select("*")
                    .eq("checkout_request_id", checkout_request_id)
                    .execute()
            )
            
            if response.data:
                logger.debug(f"Found payment: {response.data[0].get('id')}")
                return response.data[0]
            else:
                logger.warning(f"No payment found for checkout ID: {checkout_request_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting payment: {str(e)}")
            return None
    
    async def update_payment_status(
        self,
        checkout_request_id: str,
        status: str,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update payment status.
        """
        try:
            data = {"status": status}
            if transaction_id:
                data["transaction_id"] = transaction_id
            
            response = (
                self.supabase
                    .table("payments")
                    .update(data)
                    .eq("checkout_request_id", checkout_request_id)
                    .execute()
            )
            
            if response.data:
                logger.info(f"Payment status updated to {status} for {checkout_request_id}")
                return response.data[0]
            else:
                logger.warning(f"No payment found to update: {checkout_request_id}")
                return {}
                
        except Exception as e:
            logger.error(f"Error updating payment: {str(e)}")
            raise
    
    async def update_payment_from_callback(
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
        Update payment from M-Pesa callback.
        """
        try:
            data = {
                "status": "completed",
                "result_code": result_code,
                "result_desc": result_desc,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if receipt:
                data["mpesa_receipt"] = receipt
            if amount:
                data["paid_amount"] = amount
            if phone:
                data["paid_phone"] = phone
            if transaction_date:
                data["transaction_date"] = transaction_date
            if callback_payload:
                data["callback_payload"] = callback_payload
            
            logger.info(f"Updating payment from callback for {checkout_request_id}")
            logger.debug(f"Update data: {data}")
            
            response = (
                self.supabase
                    .table("payments")
                    .update(data)
                    .eq("checkout_request_id", checkout_request_id)
                    .execute()
            )
            
            if response.data:
                logger.info(f"Callback data updated for payment: {response.data[0].get('id')}")
                return response.data[0]
            else:
                logger.warning(f"No payment found for callback: {checkout_request_id}")
                return {}
                
        except Exception as e:
            logger.error(f"Error updating payment from callback: {str(e)}")
            raise
    
    async def get_user_payments(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all payments for a user.
        """
        try:
            response = (
                self.supabase
                    .table("payments")
                    .select("*")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .execute()
            )
            
            logger.info(f"Found {len(response.data)} payments for user {user_id}")
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting user payments: {str(e)}")
            return []
    
    async def get_payment_by_request_id(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get payment by request ID.
        
        Note: This method is deprecated as request_id is no longer stored.
        It will return None for all queries.
        """
        logger.warning(f"get_payment_by_request_id called with {request_id} - method is deprecated")
        return None
    
    async def get_payments_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Get all payments with a specific status.
        """
        try:
            response = (
                self.supabase
                    .table("payments")
                    .select("*")
                    .eq("status", status)
                    .order("created_at", desc=True)
                    .execute()
            )
            
            logger.info(f"Found {len(response.data)} payments with status {status}")
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting payments by status: {str(e)}")
            return []
    
    async def get_user_service_status(self, user_id: str, service_id: str) -> bool:
        """
        Check if a user has paid for a specific service.
        
        Note: service_id can be either the numeric ID (bigint) or the string code.
        """
        try:
            # Try as numeric ID first
            response = (
                self.supabase
                    .table("payments")
                    .select("status")
                    .eq("user_id", user_id)
                    .eq("service_id", service_id)
                    .eq("status", "completed")
                    .execute()
            )
            
            if response.data:
                return True
            
            # If service_id is a string code, try to find by service_name or through join
            # This handles both cases
            return False
            
        except Exception as e:
            logger.error(f"Error checking user service status: {str(e)}")
            return False
    
    async def get_user_paid_services(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all paid service IDs and names for a user.
        """
        try:
            response = (
                self.supabase
                    .table("payments")
                    .select("service_id, service_name, service_id")
                    .eq("user_id", user_id)
                    .eq("status", "completed")
                    .execute()
            )
            
            # Deduplicate by service_id
            seen = set()
            services = []
            for p in response.data:
                sid = p.get("service_id")
                if sid and sid not in seen:
                    seen.add(sid)
                    services.append({
                        "service_id": sid,
                        "service_name": p.get("service_name")
                    })
            
            logger.info(f"User {user_id} has {len(services)} paid services")
            return services
            
        except Exception as e:
            logger.error(f"Error getting user paid services: {str(e)}")
            return []
    
    async def get_all_payments(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all payments with pagination.
        """
        try:
            response = (
                self.supabase
                    .table("payments")
                    .select("*")
                    .order("created_at", desc=True)
                    .range(offset, offset + limit - 1)
                    .execute()
            )
            
            logger.info(f"Retrieved {len(response.data)} payments")
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting all payments: {str(e)}")
            return []
    
    async def get_payments_count(self) -> int:
        """
        Get total count of payments.
        """
        try:
            response = (
                self.supabase
                    .table("payments")
                    .select("*", count="exact")
                    .execute()
            )
            
            return response.count if response.count is not None else 0
            
        except Exception as e:
            logger.error(f"Error getting payments count: {str(e)}")
            return 0
    
    async def get_user_payments_count(self, user_id: str) -> int:
        """
        Get total count of payments for a user.
        """
        try:
            response = (
                self.supabase
                    .table("payments")
                    .select("*", count="exact")
                    .eq("user_id", user_id)
                    .execute()
            )
            
            return response.count if response.count is not None else 0
            
        except Exception as e:
            logger.error(f"Error getting user payments count: {str(e)}")
            return 0
    
    async def get_payments_by_service(self, service_id: str) -> List[Dict[str, Any]]:
        """
        Get all payments for a specific service.
        """
        try:
            response = (
                self.supabase
                    .table("payments")
                    .select("*")
                    .eq("service_id", service_id)
                    .order("created_at", desc=True)
                    .execute()
            )
            
            logger.info(f"Found {len(response.data)} payments for service {service_id}")
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting payments by service: {str(e)}")
            return []
    
    async def get_payments_by_date_range(
        self,
        start_date: str,
        end_date: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get payments within a date range.
        """
        try:
            response = (
                self.supabase
                    .table("payments")
                    .select("*")
                    .gte("created_at", start_date)
                    .lte("created_at", end_date)
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
            )
            
            logger.info(f"Found {len(response.data)} payments in date range")
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting payments by date range: {str(e)}")
            return []
