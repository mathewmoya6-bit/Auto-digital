"""
Auto-D Kenya - M-Pesa Repository
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class MpesaRepository:
    """Database operations for M-Pesa."""

    @property
    def supabase(self):
        client = get_supabase()
        if client is None:
            raise RuntimeError("Supabase client is not initialized")
        return client

    # ---------------------------------------------------------
    # Payments
    # ---------------------------------------------------------

    async def create_payment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()

        row = {
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
            "description": data.get("description"),
            "created_at": now,
            "updated_at": now,
        }

        result = (
            self.supabase
            .table("payments")
            .insert(row)
            .execute()
        )

        return result.data[0] if result.data else {}

    async def get_payment_by_checkout_id(
        self,
        checkout_request_id: str,
    ) -> Optional[Dict[str, Any]]:

        result = (
            self.supabase
            .table("payments")
            .select("*")
            .eq("checkout_request_id", checkout_request_id)
            .maybe_single()
            .execute()
        )

        return result.data if result else None

    async def get_payment_by_id(
        self,
        payment_id: str,
    ) -> Optional[Dict[str, Any]]:

        result = (
            self.supabase
            .table("payments")
            .select("*")
            .eq("id", payment_id)
            .maybe_single()
            .execute()
        )

        return result.data if result else None

    async def update_payment_from_callback(
        self,
        checkout_request_id: str,
        result_code: str,
        result_desc: str,
        receipt: Optional[str] = None,
        amount: Optional[float] = None,
        phone: Optional[str] = None,
        transaction_date: Optional[str] = None,
        callback_payload: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:

        now = datetime.now(timezone.utc).isoformat()

        update = {
            "result_code": result_code,
            "result_desc": result_desc,
            "updated_at": now,
            "callback_payload": callback_payload,
        }

        if result_code == "0":
            update["status"] = "paid"
            update["completed_at"] = now
        else:
            update["status"] = "failed"

        if receipt:
            update["mpesa_receipt"] = receipt
            update["mpesa_receipt_number"] = receipt

        if amount is not None:
            update["paid_amount"] = amount
            update["callback_amount"] = amount

        if phone:
            update["paid_phone"] = phone

        if transaction_date:
            update["transaction_date"] = transaction_date

        result = (
            self.supabase
            .table("payments")
            .update(update)
            .eq("checkout_request_id", checkout_request_id)
            .execute()
        )

        return result.data[0] if result.data else None

    async def update_payment_status(
        self,
        checkout_request_id: str,
        status: str,
    ) -> Optional[Dict[str, Any]]:

        result = (
            self.supabase
            .table("payments")
            .update({
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("checkout_request_id", checkout_request_id)
            .execute()
        )

        return result.data[0] if result.data else None

    async def get_user_payments(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:

        result = (
            self.supabase
            .table("payments")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        return result.data or []

    # ---------------------------------------------------------
    # Reports
    # ---------------------------------------------------------

    async def link_report(
        self,
        payment_id: str,
        report_id: str,
    ) -> None:
        """
        Attach a generated report to a payment.
        """

        (
            self.supabase
            .table("reports")
            .update({"payment_id": payment_id})
            .eq("id", report_id)
            .execute()
        )

    # ---------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------

    async def get_pending_payments(self) -> List[Dict[str, Any]]:

        result = (
            self.supabase
            .table("payments")
            .select("*")
            .eq("status", "pending")
            .execute()
        )

        return result.data or []
