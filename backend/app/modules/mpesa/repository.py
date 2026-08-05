# app/modules/mpesa/repository.py
# ================================================================
# Auto-D Kenya - M-Pesa Repository
# ================================================================

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class MpesaRepository:
    """Database operations for M-Pesa payments."""

    @property
    def supabase(self):
        client = get_supabase()
        if client is None:
            raise RuntimeError("Supabase client is not initialized")
        return client

    # ============================================================
    # Payments
    # ============================================================

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
        callback_payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:

        now = datetime.now(timezone.utc).isoformat()

        update = {
            "result_code": str(result_code),
            "result_desc": result_desc,
            "updated_at": now,
            "callback_payload": callback_payload,
        }

        # --------------------------------------------------------
        # SUCCESS / FAILURE
        # --------------------------------------------------------

        if str(result_code) == "0":
            update["status"] = "completed"
            update["completed_at"] = now
        else:
            update["status"] = "failed"

        # --------------------------------------------------------
        # OPTIONAL FIELDS
        # --------------------------------------------------------

        if receipt:
            update["receipt_number"] = receipt

        if amount is not None:
            update["paid_amount"] = amount

        if phone:
            update["paid_phone"] = phone

        if transaction_date:
            update["transaction_date"] = transaction_date

        logger.info(
            "Updating payment %s with %s",
            checkout_request_id,
            update,
        )

        result = (
            self.supabase
            .table("payments")
            .update(update)
            .eq("checkout_request_id", checkout_request_id)
            .select()
            .single()
            .execute()
        )

        logger.info("Update returned: %s", result.data)

        return result.data if result else None

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
            .select()
            .single()
            .execute()
        )

        return result.data if result else None

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

    # ============================================================
    # Reports
    # ============================================================

    async def link_report(
        self,
        payment_id: str,
        report_id: str,
    ) -> None:

        (
            self.supabase
            .table("reports")
            .update({"payment_id": payment_id})
            .eq("id", report_id)
            .execute()
        )

    # ============================================================
    # Cleanup
    # ============================================================

    async def get_pending_payments(self) -> List[Dict[str, Any]]:

        result = (
            self.supabase
            .table("payments")
            .select("*")
            .eq("status", "pending")
            .execute()
        )

        return result.data or []
