# backend/app/services/mpesa_service.py

"""
M-Pesa Service - Production Grade
All services and prices are pulled from the database dynamically
"""

import logging
import base64
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.database import supabase
from app.core.config import settings

logger = logging.getLogger(__name__)


# ─── Constants ──────────────────────────────────────────────────────

SERVICE_ACCESS_DAYS = 365
PAYMENT_TIMEOUT_MINUTES = 30


# ─── Enums ──────────────────────────────────────────────────────────

class PaymentStatus:
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Repository Classes ────────────────────────────────────────────

class ServiceRepository:
    """Service repository with caching."""
    
    _cache: Dict[str, Dict] = {}
    
    @classmethod
    async def get_by_code(cls, code: str) -> Optional[Dict]:
        """Get service by code."""
        # Check cache
        if code in cls._cache:
            return cls._cache[code]
        
        try:
            result = supabase.table("services")\
                .select("*")\
                .eq("code", code)\
                .eq("active", True)\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                service = result.data[0]
                cls._cache[code] = service
                return service
        except Exception as e:
            logger.error(f"Error fetching service {code}: {e}")
        
        return None
    
    @classmethod
    async def get_by_id(cls, service_id: int) -> Optional[Dict]:
        """Get service by ID."""
        # Check cache
        for code, service in cls._cache.items():
            if service.get("id") == service_id:
                return service
        
        try:
            result = supabase.table("services")\
                .select("*")\
                .eq("id", service_id)\
                .eq("active", True)\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                service = result.data[0]
                cls._cache[service.get("code")] = service
                return service
        except Exception as e:
            logger.error(f"Error fetching service {service_id}: {e}")
        
        return None
    
    @classmethod
    async def get_all_active(cls) -> List[Dict]:
        """Get all active services."""
        try:
            result = supabase.table("services")\
                .select("*")\
                .eq("active", True)\
                .order("display_order")\
                .execute()
            
            services = result.data or []
            
            # Update cache
            for service in services:
                cls._cache[service.get("code")] = service
            
            return services
        except Exception as e:
            logger.error(f"Error fetching active services: {e}")
            return []


class PaymentRepository:
    """Payment repository."""
    
    @classmethod
    async def create_payment(cls, data: Dict) -> Dict:
        """Create a new payment."""
        try:
            if "id" not in data:
                data["id"] = str(uuid.uuid4())
            data["created_at"] = datetime.now(timezone.utc).isoformat()
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            result = supabase.table("payments").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            return None
    
    @classmethod
    async def get_by_checkout_id(cls, checkout_id: str) -> Optional[Dict]:
        """Get payment by checkout ID."""
        try:
            result = supabase.table("payments")\
                .select("*")\
                .eq("checkout_request_id", checkout_id)\
                .limit(1)\
                .execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error fetching payment: {e}")
            return None
    
    @classmethod
    async def update_with_lock(cls, checkout_id: str, data: Dict, expected_status: str = "pending") -> Optional[Dict]:
        """Update payment with optimistic locking."""
        try:
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            result = supabase.table("payments")\
                .update(data)\
                .eq("checkout_request_id", checkout_id)\
                .eq("status", expected_status)\
                .execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating payment: {e}")
            return None


class ServiceAccessRepository:
    """Service access repository."""
    
    @classmethod
    async def create_access(cls, data: Dict) -> Dict:
        """Create service access record."""
        try:
            if "id" not in data:
                data["id"] = str(uuid.uuid4())
            data["created_at"] = datetime.now(timezone.utc).isoformat()
            
            result = supabase.table("service_access").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating service access: {e}")
            return None
    
    @classmethod
    async def check_access(cls, user_id: str, service_id: int) -> Optional[Dict]:
        """Check if user has access to service."""
        try:
            result = supabase.table("service_access")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("service_id", service_id)\
                .eq("status", "active")\
                .limit(1)\
                .execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error checking access: {e}")
            return None


class PaymentTransaction:
    """Payment transaction helper."""
    
    @classmethod
    async def complete_payment(cls, checkout_id: str, payment_data: Dict, unlock_service: bool = True) -> bool:
        """Complete payment transaction."""
        try:
            # Update payment
            payment = await PaymentRepository.update_with_lock(
                checkout_id,
                payment_data,
                expected_status="pending"
            )
            
            if not payment:
                return False
            
            # Unlock service
            if unlock_service and payment.get("user_id") and payment.get("service_id"):
                await ServiceAccessRepository.create_access({
                    "user_id": payment["user_id"],
                    "service_id": payment["service_id"],
                    "status": "active",
                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=SERVICE_ACCESS_DAYS)).isoformat(),
                    "payment_ref": checkout_id
                })
            
            return True
            
        except Exception as e:
            logger.error(f"Payment transaction error: {e}")
            return False


# ─── MpesaService ──────────────────────────────────────────────────

class MpesaService:
    """Main M-Pesa service."""
    
    def __init__(self):
        self.service_repo = ServiceRepository()
        self.payment_repo = PaymentRepository()
        self.access_repo = ServiceAccessRepository()
        self._initialized = False
    
    async def startup(self):
        """Initialize the service."""
        self._initialized = True
        logger.info("✅ M-Pesa Service initialized")
    
    # ─── Public Methods ────────────────────────────────────────────
    
    async def get_services(self) -> List[Dict]:
        """Get all active services."""
        try:
            return await self.service_repo.get_all_active()
        except Exception as e:
            logger.error(f"Error getting services: {e}")
            return []
    
    async def get_service_by_code(self, service_code: str) -> Optional[Dict]:
        """Get service by code."""
        try:
            return await self.service_repo.get_by_code(service_code)
        except Exception as e:
            logger.error(f"Error getting service by code: {e}")
            return None
    
    async def get_user_services(self, user_id: str) -> List[Dict]:
        """Get user's unlocked services."""
        try:
            # This would query service_access table
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Error getting user services: {e}")
            return []
    
    async def initiate_payment(
        self,
        phone: str,
        service_code: str,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        amount: Optional[float] = None
    ) -> Dict:
        """Initiate payment for a service."""
        try:
            # Get service
            service = await self.service_repo.get_by_code(service_code)
            if not service:
                return {
                    "success": False,
                    "error": f"Service '{service_code}' not found"
                }
            
            # Use provided amount or service price
            amount = amount or float(service.get("price", 0))
            if amount <= 0:
                return {
                    "success": False,
                    "error": f"Invalid amount: {amount}"
                }
            
            # Generate checkout ID
            checkout_id = f"CHECKOUT-{uuid.uuid4().hex[:8].upper()}"
            
            # Create payment record
            payment_data = {
                "user_id": user_id,
                "service_id": service.get("id"),
                "service_name": service.get("name"),
                "amount": amount,
                "currency": service.get("currency", "KES"),
                "phone": phone,
                "checkout_request_id": checkout_id,
                "status": PaymentStatus.PENDING,
                "request_id": request_id
            }
            
            payment = await self.payment_repo.create_payment(payment_data)
            if not payment:
                return {
                    "success": False,
                    "error": "Failed to create payment record"
                }
            
            return {
                "success": True,
                "checkout_request_id": checkout_id,
                "amount": amount,
                "service_name": service.get("name"),
                "payment_id": payment.get("id")
            }
            
        except Exception as e:
            logger.error(f"Payment initiation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def process_callback(self, callback_data: Dict) -> bool:
        """Process M-Pesa callback."""
        try:
            stk = callback_data.get("Body", {}).get("stkCallback", {})
            checkout_id = stk.get("CheckoutRequestID")
            result_code = stk.get("ResultCode")
            
            if not checkout_id:
                return False
            
            # Get payment
            payment = await self.payment_repo.get_by_checkout_id(checkout_id)
            if not payment:
                return False
            
            if payment.get("status") == PaymentStatus.COMPLETED:
                return True
            
            if str(result_code) == "0":
                # Success
                metadata = stk.get("CallbackMetadata", {}).get("Item", [])
                meta = {}
                for item in metadata:
                    name = item.get("Name")
                    if name:
                        meta[name] = item.get("Value")
                
                receipt = meta.get("MpesaReceiptNumber")
                amount = float(meta.get("Amount", 0))
                
                payment_data = {
                    "status": PaymentStatus.COMPLETED,
                    "mpesa_receipt": receipt,
                    "paid_amount": amount,
                    "paid_phone": meta.get("PhoneNumber"),
                    "result_code": "0",
                    "result_desc": "Payment successful",
                    "transaction_date": datetime.now(timezone.utc).isoformat()
                }
                
                return await PaymentTransaction.complete_payment(checkout_id, payment_data)
            else:
                # Failure
                payment_data = {
                    "status": PaymentStatus.FAILED,
                    "result_code": str(result_code),
                    "result_desc": stk.get("ResultDesc", "Payment failed")
                }
                updated = await self.payment_repo.update_with_lock(checkout_id, payment_data)
                return bool(updated)
            
        except Exception as e:
            logger.error(f"Callback processing error: {e}")
            return False
    
    async def get_payment_status(self, checkout_id: str) -> Dict:
        """Get payment status."""
        try:
            payment = await self.payment_repo.get_by_checkout_id(checkout_id)
            if not payment:
                return {
                    "success": False,
                    "error": "Payment not found"
                }
            
            return {
                "success": True,
                "checkout_request_id": payment.get("checkout_request_id"),
                "status": payment.get("status"),
                "amount": payment.get("amount"),
                "service_name": payment.get("service_name"),
                "mpesa_receipt": payment.get("mpesa_receipt"),
                "created_at": payment.get("created_at")
            }
        except Exception as e:
            logger.error(f"Error getting payment status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ─── FIX: confirm_payment method inside the class ─────────────
    
    async def confirm_payment(self, checkout_id: str, user_id: str) -> Dict[str, Any]:
        """
        Manually confirm a payment by CheckoutRequestID.
        
        Used when the M-Pesa callback did not arrive but the user
        has completed payment successfully.
        """
        try:
            # Get payment record
            payment = await self.payment_repo.get_by_checkout_id(checkout_id)

            if payment is None:
                return {
                    "success": False,
                    "error": "Payment not found"
                }

            # Verify ownership
            if payment.get("user_id") and payment.get("user_id") != user_id:
                return {
                    "success": False,
                    "error": "Not authorized"
                }

            # Already completed
            if payment.get("status") == PaymentStatus.COMPLETED:
                return {
                    "success": True,
                    "status": "already_completed",
                    "message": "Payment already confirmed"
                }

            # Verify service exists
            service_id = payment.get("service_id")
            if service_id:
                service = await self.service_repo.get_by_id(service_id)
                if service is None:
                    return {
                        "success": False,
                        "error": "Service not found"
                    }

            # Create synthetic callback data
            callback_data = {
                "Body": {
                    "stkCallback": {
                        "CheckoutRequestID": checkout_id,
                        "ResultCode": 0,
                        "ResultDesc": "Confirmed manually by user",
                        "CallbackMetadata": {
                            "Item": [
                                {
                                    "Name": "Amount",
                                    "Value": float(payment.get("amount", 0))
                                },
                                {
                                    "Name": "MpesaReceiptNumber",
                                    "Value": f"MANUAL-{checkout_id[:8]}"
                                },
                                {
                                    "Name": "PhoneNumber",
                                    "Value": payment.get("phone", "254700000000")
                                }
                            ]
                        }
                    }
                }
            }

            # Process the callback
            success = await self.process_callback(callback_data)

            if success:
                return {
                    "success": True,
                    "message": "Payment confirmed successfully"
                }

            return {
                "success": False,
                "error": "Failed to process callback"
            }

        except Exception as e:
            logger.exception(f"Confirm payment error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ─── Admin Methods ─────────────────────────────────────────────
    
    async def admin_get_all_services(self, include_inactive: bool = False) -> List[Dict]:
        """Admin: Get all services."""
        try:
            query = supabase.table("services").select("*")
            if not include_inactive:
                query = query.eq("active", True)
            result = query.order("display_order").execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Admin get services error: {e}")
            return []
    
    async def admin_get_service(self, service_id: int) -> Optional[Dict]:
        """Admin: Get service by ID."""
        try:
            result = supabase.table("services")\
                .select("*")\
                .eq("id", service_id)\
                .limit(1)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Admin get service error: {e}")
            return None
    
    async def admin_update_service(self, service_id: int, data: Dict, changed_by: str) -> Optional[Dict]:
        """Admin: Update service."""
        try:
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            data["updated_by"] = changed_by
            
            result = supabase.table("services")\
                .update(data)\
                .eq("id", service_id)\
                .execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Admin update service error: {e}")
            return None
    
    async def admin_delete_service(self, service_id: int, deleted_by: str) -> bool:
        """Admin: Soft delete service."""
        try:
            data = {
                "active": False,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
                "deleted_by": deleted_by
            }
            result = supabase.table("services")\
                .update(data)\
                .eq("id", service_id)\
                .execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Admin delete service error: {e}")
            return False
    
    async def admin_restore_service(self, service_id: int) -> bool:
        """Admin: Restore service."""
        try:
            data = {
                "active": True,
                "deleted_at": None,
                "deleted_by": None
            }
            result = supabase.table("services")\
                .update(data)\
                .eq("id", service_id)\
                .execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Admin restore service error: {e}")
            return False
    
    async def admin_get_price_history(self, service_id: int) -> List[Dict]:
        """Admin: Get price history."""
        try:
            result = supabase.table("service_price_history")\
                .select("*")\
                .eq("service_id", service_id)\
                .order("created_at", desc=True)\
                .execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Admin get price history error: {e}")
            return []
    
    async def admin_get_stats(self) -> Dict:
        """Admin: Get stats."""
        try:
            services = await self.get_services()
            return {
                "total_services": len(services),
                "active_services": len([s for s in services if s.get("active")]),
                "mpesa_service_loaded": self._initialized
            }
        except Exception as e:
            logger.error(f"Admin get stats error: {e}")
            return {
                "total_services": 0,
                "active_services": 0,
                "mpesa_service_loaded": False,
                "error": str(e)
            }


# ─── Singleton ─────────────────────────────────────────────────────

_mpesa_service: Optional[MpesaService] = None


def get_mpesa_service() -> MpesaService:
    """Get or create M-Pesa service singleton."""
    global _mpesa_service
    if _mpesa_service is None:
        _mpesa_service = MpesaService()
    return _mpesa_service


# ─── Export ─────────────────────────────────────────────────────

__all__ = [
    "MpesaService",
    "get_mpesa_service",
    "ServiceRepository",
    "PaymentRepository",
    "ServiceAccessRepository",
    "PaymentTransaction",
    "PaymentStatus"
]
