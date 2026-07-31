# app/modules/mpesa/service.py
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException, AppException
from app.modules.mpesa.repository import MpesaRepository
from app.modules.mpesa.stk_push import StkPushService

logger = logging.getLogger(__name__)


class MpesaService:
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
        """Initiate M-Pesa payment.

        `service_id` here is the frontend's string code (e.g. "mileage"),
        not the table's bigint `id`. Filtering on `id` with a string throws
        a Postgres 22P02 type error before the query even runs.
        """
        service = self.supabase.table("services").select("*").eq("code", service_id).eq("active", True).execute()
        if not service.data:
            raise NotFoundException(f"Service not found: {service_id}")

        service_data = service.data[0]
        price = amount or float(service_data.get("price", 0))

        checkout_id = f"CHK-{service_id[:4]}-{str(int(datetime.utcnow().timestamp()))[-6:]}"

        result = await self.stk_push.initiate_push(
            phone=phone,
            amount=price,
            description=description or service_data.get("name", "Auto-D Kenya Service"),
            checkout_request_id=checkout_id
        )

        await self.repository.create_payment({
            "user_id": user_id,
            "service_id": service_id,  # keep as the string code — see note below on why
            "checkout_request_id": result["checkout_request_id"],
            "phone": phone,
            "amount": price,
            "description": description or service_data.get("name"),
            "request_id": request_id,
            "status": "pending",
        })

        return {
            "checkout_request_id": result["checkout_request_id"],
            "message": result.get("customer_message", "STK push sent successfully"),
            "status": "pending"
        }

    async def get_payment_status(self, checkout_request_id: str, user_id: str) -> Dict[str, Any]:
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
        payment = await self.repository.get_payment_by_checkout_id(checkout_request_id)
        if not payment or payment.get("user_id") != user_id:
            raise NotFoundException("Payment not found")

        if payment.get("status") == "completed":
            return {"status": "completed", "message": "Payment already confirmed"}

        if payment.get("status") != "paid":
            raise AppException("Payment not yet confirmed by M-Pesa", status_code=409)

        await self.repository.update_payment_status(checkout_request_id, "completed")

        if payment.get("user_id") and payment.get("service_id"):
            await self.unlock_service(payment["user_id"], payment["service_id"])

        return {"status": "completed", "message": "Payment confirmed"}

    async def unlock_service(self, user_id: str, service_id: str) -> None:
        try:
            existing = self.supabase.table("user_services").select("*").eq("user_id", user_id).eq("service_id", service_id).execute()

            if existing.data:
                self.supabase.table("user_services").update({
                    "status": "active",
                    "purchased_at": datetime.utcnow().isoformat()
                }).eq("id", existing.data[0]["id"]).execute()
            else:
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
        try:
            response = self.supabase.table("user_services").select("*, services(*)").eq("user_id", user_id).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting user services: {str(e)}")
            return []

    async def get_user_payments(self, user_id: str) -> list:
        return await self.repository.get_user_payments(user_id)
