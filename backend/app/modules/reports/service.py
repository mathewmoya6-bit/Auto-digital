# app/modules/reports/service.py
# Auto-D Kenya - Reports Service
# ================================================================
# TYPE: MODULE - Report generation service

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException

from app.modules.valuation.service import ValuationService
from app.modules.running_cost.service import RunningCostService

logger = logging.getLogger(__name__)


class ReportService:
    """Business logic for generating Auto-D reports."""

    def __init__(self):
        self.supabase = get_supabase()
        self.valuation_service = ValuationService()
        self.running_cost_service = RunningCostService()

    async def _get_vehicle(self, vehicle_id: str, user_id: str) -> Dict[str, Any]:
        """Load vehicle belonging to the user."""

        response = (
            self.supabase
            .table("vehicles")
            .select("*")
            .eq("id", vehicle_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            raise NotFoundException("Vehicle not found.")

        return response.data[0]

    async def generate_valuation_report(
        self,
        vehicle_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Generate a quick vehicle valuation report.
        """

        vehicle = await self._get_vehicle(vehicle_id, user_id)

        variant_id = vehicle.get("variant_id")

        if not variant_id:
            raise NotFoundException("Vehicle variant not found.")

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
            "status": "completed",
            "generated_at": datetime.now(timezone.utc).isoformat(),

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

        return report

    async def generate_running_cost_report(
        self,
        vehicle_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Generate running cost report using RunningCostService.
        """

        vehicle = await self._get_vehicle(vehicle_id, user_id)

        variant_id = vehicle.get("variant_id")

        if not variant_id:
            raise NotFoundException("Vehicle variant not found.")

        report = await self.running_cost_service.calculate_running_cost(
            variant_id=variant_id,
            annual_mileage=vehicle.get("annual_mileage", 20000),
            user_id=user_id,
        )

        return report

    async def get_report_history(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Return report history.
        """

        try:

            response = (
                self.supabase
                .table("valuation_reports")
                .select(
                    """
                    id,
                    report_number,
                    vehicle_id,
                    estimated_value,
                    confidence_score,
                    created_at
                    """
                )
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )

            return response.data or []

        except Exception as e:
            logger.exception("Failed to load report history: %s", e)
            return []
