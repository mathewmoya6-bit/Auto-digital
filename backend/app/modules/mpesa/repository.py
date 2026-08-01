# app/modules/mpesa/repository.py
# Auto-D Kenya - M-Pesa Repository
# ================================================================
# TYPE: MODULE - M-Pesa database operations

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import uuid4

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class MpesaRepository:
    """M-Pesa repository for database operations."""
    
    def __init__(self):
        self.supabase = get_supabase()
    
    # ─── PAYMENT CRUD ──────────────────────────────────────────────

    async def create_payment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a payment record.
        
        ✅ Uses correct data structure with all required fields
        ✅ Uses 'payments' table
        """
        try:
            payment_data = {
                "id": str(uuid4()),
                "user_id": data.get("user_id"),
                "request_id": data.get("request_id"),
                "service_id": data.get("service_id"),
                "service_name": data.get("service_name"),
                "amount": data.get("amount"),
                "currency": data.get("currency", "KES"),
                "phone": data.get("phone"),
                "checkout_request_id": data.get("checkout_request_id"),
                "merchant_request_id": data.get("merchant_request_id"),
                "status": data.get("status", "pending"),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
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
    
    async def get_payment_by_id(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get payment by ID.
        """
        try:
            response = (
                self.supabase
                .table("payments")
                .select("*")
                .eq("id", payment_id)
                .execute()
            )
            
            if response.data:
                return response.data[0]
            return None
                
        except Exception as e:
            logger.error(f"Error getting payment by ID: {str(e)}")
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
            data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
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
                "status": "completed" if result_code == "0" else "failed",
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
            if result_code == "0":
                data["completed_at"] = datetime.utcnow().isoformat()
            
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
    
    # ─── PAYMENT QUERIES ───────────────────────────────────────────

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
    
    async def get_payments_by_user_and_service(self, user_id: str, service_id: str) -> List[Dict[str, Any]]:
        """
        Get payments for a user and service.
        """
        try:
            response = (
                self.supabase
                .table("payments")
                .select("*")
                .eq("user_id", user_id)
                .eq("service_id", service_id)
                .order("created_at", desc=True)
                .execute()
            )
            
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting payments by user and service: {str(e)}")
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
    
    # ─── USER SERVICES ─────────────────────────────────────────────

    async def create_user_service(
        self,
        user_id: str,
        service_id: int,
        payment_id: Optional[str] = None,
        expires_days: int = 365
    ) -> Dict[str, Any]:
        """
        Create a user service access record.
        """
        try:
            expires_at = (datetime.utcnow() + timedelta(days=expires_days)).isoformat()
            
            data = {
                "user_id": user_id,
                "service_id": service_id,
                "payment_id": payment_id,
                "status": "active",
                "expires_at": expires_at,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            response = (
                self.supabase
                .table("user_services")
                .insert(data)
                .execute()
            )
            
            if response.data:
                logger.info(f"User service created: user={user_id}, service={service_id}")
                return response.data[0]
            return {}
            
        except Exception as e:
            logger.error(f"Error creating user service: {str(e)}")
            raise
    
    async def update_user_service(
        self,
        user_id: str,
        service_id: int,
        status: str = "active",
        payment_id: Optional[str] = None,
        expires_days: int = 365
    ) -> Dict[str, Any]:
        """
        Update a user service access record.
        """
        try:
            expires_at = (datetime.utcnow() + timedelta(days=expires_days)).isoformat()
            
            data = {
                "status": status,
                "expires_at": expires_at,
                "updated_at": datetime.utcnow().isoformat()
            }
            if payment_id:
                data["payment_id"] = payment_id
            
            response = (
                self.supabase
                .table("user_services")
                .update(data)
                .eq("user_id", user_id)
                .eq("service_id", service_id)
                .execute()
            )
            
            if response.data:
                logger.info(f"User service updated: user={user_id}, service={service_id}")
                return response.data[0]
            return {}
            
        except Exception as e:
            logger.error(f"Error updating user service: {str(e)}")
            raise
    
    async def get_user_service(
        self,
        user_id: str,
        service_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get a user's service access record.
        """
        try:
            response = (
                self.supabase
                .table("user_services")
                .select("*")
                .eq("user_id", user_id)
                .eq("service_id", service_id)
                .execute()
            )
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting user service: {str(e)}")
            return None
    
    async def get_user_services(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all services a user has access to.
        """
        try:
            response = (
                self.supabase
                .table("user_services")
                .select("*, services(*)")
                .eq("user_id", user_id)
                .eq("status", "active")
                .execute()
            )
            
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting user services: {str(e)}")
            return []
    
    async def check_user_service_access(
        self,
        user_id: str,
        service_id: int
    ) -> bool:
        """
        Check if a user has active access to a service.
        """
        try:
            response = (
                self.supabase
                .table("user_services")
                .select("status, expires_at")
                .eq("user_id", user_id)
                .eq("service_id", service_id)
                .eq("status", "active")
                .execute()
            )
            
            if not response.data:
                return False
            
            record = response.data[0]
            expires_at = record.get("expires_at")
            
            if expires_at:
                try:
                    expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    if datetime.utcnow() > expires:
                        return False
                except:
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking user service access: {str(e)}")
            return False
    
    async def get_user_service_statuses(self, user_id: str) -> Dict[str, bool]:
        """
        Get all service access statuses for a user.
        """
        try:
            response = (
                self.supabase
                .table("user_services")
                .select("services(code), status, expires_at")
                .eq("user_id", user_id)
                .eq("status", "active")
                .execute()
            )
            
            result = {}
            now = datetime.utcnow()
            
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
                        except:
                            pass
                    result[code] = not is_expired
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting user service statuses: {str(e)}")
            return {}
    
    async def deactivate_user_service(
        self,
        user_id: str,
        service_id: int
    ) -> bool:
        """
        Deactivate a user's service access.
        """
        try:
            response = (
                self.supabase
                .table("user_services")
                .update({
                    "status": "expired",
                    "updated_at": datetime.utcnow().isoformat()
                })
                .eq("user_id", user_id)
                .eq("service_id", service_id)
                .execute()
            )
            
            return len(response.data) > 0
            
        except Exception as e:
            logger.error(f"Error deactivating user service: {str(e)}")
            return False
    
    async def get_expired_services(self) -> List[Dict[str, Any]]:
        """
        Get all expired service access records.
        """
        try:
            now = datetime.utcnow().isoformat()
            response = (
                self.supabase
                .table("user_services")
                .select("*")
                .eq("status", "active")
                .lt("expires_at", now)
                .execute()
            )
            
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting expired services: {str(e)}")
            return []
    
    # ─── SERVICE QUERIES ───────────────────────────────────────────

    async def get_service_by_code(self, service_code: str) -> Optional[Dict[str, Any]]:
        """
        Get a service by its code.
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
    
    async def get_service_by_id(self, service_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a service by its ID.
        """
        try:
            response = (
                self.supabase
                .table("services")
                .select("*")
                .eq("id", service_id)
                .eq("active", True)
                .single()
                .execute()
            )
            
            return response.data if response.data else None
            
        except Exception as e:
            logger.error(f"Error getting service by ID {service_id}: {str(e)}")
            return None
    
    async def get_available_services(self) -> List[Dict[str, Any]]:
        """
        Get all available services.
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
            
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting available services: {str(e)}")
            return []
    
    # ─── PAYMENT VERIFICATION ──────────────────────────────────────

    async def verify_payment_completed(self, checkout_request_id: str) -> bool:
        """
        Verify that a payment is completed.
        """
        payment = await self.get_payment_by_checkout_id(checkout_request_id)
        if not payment:
            return False
        
        status = payment.get("status")
        return status in ["completed", "paid", "success"]
    
    async def get_pending_payments(self) -> List[Dict[str, Any]]:
        """
        Get all pending payments (created > 5 minutes ago).
        """
        try:
            cutoff = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
            response = (
                self.supabase
                .table("payments")
                .select("*")
                .eq("status", "pending")
                .lt("created_at", cutoff)
                .execute()
            )
            
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting pending payments: {str(e)}")
            return []
