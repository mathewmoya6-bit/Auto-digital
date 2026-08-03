"""
Auto-D Kenya - Reports Service
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException

from app.modules.valuation.service import ValuationService
from app.modules.running_cost.service import RunningCostService

logger = logging.getLogger(__name__)


class ReportService:
    """Business logic for generating reports."""

    VALUATION_SERVICE_ID = 1
    RUNNING_COST_SERVICE_ID = 2

    def __init__(self):
        self.supabase = get_supabase()
        self.valuation_service = ValuationService()
        self.running_cost_service = RunningCostService()

    async def _get_vehicle(
        self,
        vehicle_id: str,
        user_id: str,
    ) -> Dict[str, Any]:

        response = (
            self.supabase
            .table("vehicles")
            .select("*")
            .eq("id", vehicle_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )

        if not response or not response.data:
            raise NotFoundException("Vehicle not found.")

        return response.data

    async def _get_unused_payment(
        self,
        user_id: str,
        service_id: int,
    ) -> Dict[str, Any]:
        """
        Returns the latest paid payment that has not yet been linked
        to a report.
        """

        payment = (
            self.supabase
            .table("payments")
            .select("*")
            .eq("user_id", user_id)
            .eq("service_id", service_id)
            .eq("status", "paid")
            .order("created_at", desc=True)
            .execute()
        )

        if not payment.data:
            raise NotFoundException(
                "No completed payment found."
            )

        for row in payment.data:

            existing = (
                self.supabase
                .table("reports")
                .select("id")
                .eq("payment_id", row["id"])
                .maybe_single()
                .execute()
            )

            if not existing.data:
                return row

        raise NotFoundException(
            "All payments for this service have already been used."
        )

    async def _save_report(
        self,
        *,
        payment_id: str,
        user_id: str,
        vehicle: Dict[str, Any],
        service_id: int,
        report_type: str,
        title: str,
        report: Dict[str, Any],
    ):

        self.supabase.table("reports").insert(
            {
                "user_id": user_id,
                "vehicle_id": vehicle["id"],
                "vehicle_plate": vehicle.get("registration_number"),
                "payment_id": payment_id,
                "service_id": str(service_id),
                "report_type": report_type,
                "title": title,
                "content": report,
                "status": "completed",
                "is_downloaded": False,
                "download_count": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()

    async def generate_valuation_report(
        self,
        vehicle_id: str,
        user_id: str,
    ) -> Dict[str, Any]:

        payment = await self._get_unused_payment(
            user_id,
            self.VALUATION_SERVICE_ID,
        )

        vehicle = await self._get_vehicle(
            vehicle_id,
            user_id,
        )

        variant_id = vehicle.get("variant_id")

        if not variant_id:
            raise NotFoundException(
                "Vehicle variant not found."
            )

        valuation = await self.valuation_service.calculate_valuation(
            variant_id=variant_id,
            year=vehicle.get("year"),
            mileage=vehicle.get("mileage", 0),
            condition=vehicle.get("condition", "good"),
            location=vehicle.get("location", "nairobi"),
            user_id=user_id,
        )

        report = {
            "report_number": f"AUTO-VAL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "vehicle": valuation.get("vehicle", {}),
            "summary": {
                "estimated_value": valuation.get("estimated_vehicle_value"),
                "market_value": valuation.get("market_value"),
                "retail_value": valuation.get("retail_value"),
                "trade_value": valuation.get("trade_value"),
                "value_range": valuation.get("estimated_value_range"),
                "confidence_score": valuation.get("confidence_score"),
                "base_price_source": valuation.get("base_price_source"),
            },
            "price_explanation": valuation.get("price_explanation"),
        }

        await self._save_report(
            payment_id=payment["id"],
            user_id=user_id,
            vehicle=vehicle,
            service_id=self.VALUATION_SERVICE_ID,
            report_type="valuation",
            title="Vehicle Valuation Report",
            report=report,
        )

        return report

    async def generate_running_cost_report(
        self,
        vehicle_id: str,
        user_id: str,
    ) -> Dict[str, Any]:

        payment = await self._get_unused_payment(
            user_id,
            self.RUNNING_COST_SERVICE_ID,
        )

        vehicle = await self._get_vehicle(
            vehicle_id,
            user_id,
        )

        variant_id = vehicle.get("variant_id")

        if not variant_id:
            raise NotFoundException(
                "Vehicle variant not found."
            )

        report = await self.running_cost_service.calculate_running_cost(
            variant_id=variant_id,
            annual_mileage=vehicle.get("annual_mileage", 20000),
            user_id=user_id,
        )

        await self._save_report(
            payment_id=payment["id"],
            user_id=user_id,
            vehicle=vehicle,
            service_id=self.RUNNING_COST_SERVICE_ID,
            report_type="running_cost",
            title="Running Cost Report",
            report=report,
        )

        return report

    async def get_report_history(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:

        try:

            response = (
                self.supabase
                .table("reports")
                .select("""
                    id,
                    payment_id,
                    vehicle_id,
                    report_type,
                    title,
                    status,
                    download_count,
                    is_downloaded,
                    created_at
                """)
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )

            return response.data or []

        except Exception as e:
            logger.exception(
                "Failed to load report history: %s",
                e,
            )
            return []
