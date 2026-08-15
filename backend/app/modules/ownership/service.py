# app/modules/ownership/service.py
"""
Vehicle Ownership Cost Service
Auto-D Kenya

PostgreSQL is the single source of truth for ownership calculations.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional

from app.modules.ownership.repository import OwnershipRepository

logger = logging.getLogger(__name__)


class OwnershipService:
    """Service layer for vehicle ownership cost."""

    def __init__(self):
        self.repository = OwnershipRepository()

    @staticmethod
    def _number(value: Any) -> float:
        """
        Convert PostgreSQL numeric/strings/None safely to float.

        This prevents errors such as:

            unsupported operand type(s) for /:
            'str' and 'int'
        """

        if value is None:
            return 0.0

        if isinstance(value, bool):
            return float(value)

        if isinstance(value, (int, float, Decimal)):
            return float(value)

        if isinstance(value, str):
            value = value.strip()

            if not value:
                return 0.0

            try:
                return float(value)
            except ValueError:
                logger.warning(
                    "Could not convert numeric value: %r",
                    value,
                )
                return 0.0

        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    async def calculate_ownership(
        self,
        vehicle_id: int,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:

        if not vehicle_id:
            raise ValueError("vehicle_id is required")

        result = await self.repository.calculate_vehicle_ownership_cost(
            vehicle_id=vehicle_id,
            as_of_date=as_of_date,
        )

        # Normalize every numeric database field.
        purchase_price = self._number(result.get("purchase_price"))
        fuel = self._number(result.get("total_fuel_cost"))
        maintenance = self._number(
            result.get("total_maintenance_cost")
        )
        insurance = self._number(
            result.get("total_insurance_cost")
        )
        tax = self._number(result.get("total_tax_cost"))
        repair = self._number(result.get("total_repair_cost"))
        depreciation = self._number(result.get("depreciation"))
        ownership_days = int(
            self._number(result.get("ownership_days"))
        )

        # Use DB TCO when available.
        database_tco = self._number(
            result.get("total_cost_of_ownership")
        )

        # If the database function returns zero/null TCO while the
        # component values are populated, calculate it from components.
        components_total = (
            fuel
            + maintenance
            + insurance
            + tax
            + repair
            + depreciation
        )

        total_cost_of_ownership = (
            database_tco
            if database_tco > 0
            else components_total
        )

        # Calculate cost/day safely.
        cost_per_day = (
            total_cost_of_ownership / ownership_days
            if ownership_days > 0
            else 0.0
        )

        # Useful derived ownership figures.
        monthly_cost = cost_per_day * 30.4375
        annual_cost = cost_per_day * 365.0

        return {
            "success": True,

            "vehicle_id": int(vehicle_id),

            "purchase_price": round(purchase_price, 2),

            "ownership_days": ownership_days,

            "cost_per_day": round(cost_per_day, 2),

            "monthly_cost": round(monthly_cost, 2),

            "annual_cost": round(annual_cost, 2),

            "total_fuel_cost": round(fuel, 2),

            "total_maintenance_cost": round(
                maintenance, 2
            ),

            "total_insurance_cost": round(
                insurance, 2
            ),

            "total_tax_cost": round(tax, 2),

            "total_repair_cost": round(repair, 2),

            "depreciation": round(
                depreciation, 2
            ),

            "total_cost_of_ownership": round(
                total_cost_of_ownership, 2
            ),

            "breakdown": {
                "fuel": round(fuel, 2),
                "maintenance": round(maintenance, 2),
                "insurance": round(insurance, 2),
                "tax": round(tax, 2),
                "repairs": round(repair, 2),
                "depreciation": round(
                    depreciation, 2
                ),
            },

            "calculated_at": (
                as_of_date or date.today()
            ).isoformat(),
        }
