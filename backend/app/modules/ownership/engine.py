"""
Auto-D Kenya
Vehicle Ownership Cost Engine

Purpose
-------
Coordinates vehicle ownership-cost calculations.

IMPORTANT:
-----------
The PostgreSQL function:

    public.calculate_vehicle_ownership_cost(
        p_vehicle_id integer,
        p_as_of_date date
    )

is the SINGLE SOURCE OF TRUTH for the actual ownership-cost
calculation.

This engine does NOT duplicate the database formulas.
It validates and normalizes the database result before returning
it to the service layer.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class OwnershipEngine:
    """
    Vehicle Ownership Cost calculation engine.

    The engine is deliberately thin because the authoritative
    calculation is performed by PostgreSQL.
    """

    NUMERIC_FIELDS = (
        "purchase_price",
        "total_fuel_cost",
        "total_maintenance_cost",
        "total_insurance_cost",
        "total_tax_cost",
        "total_repair_cost",
        "depreciation",
        "total_cost_of_ownership",
        "cost_per_day",
    )

    INTEGER_FIELDS = (
        "vehicle_id",
        "ownership_days",
    )

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def calculate(
        self,
        database_result: Any,
        vehicle_id: int,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Normalize and validate the PostgreSQL ownership-cost result.

        Parameters
        ----------
        database_result:
            Result returned by the PostgreSQL RPC call.

        vehicle_id:
            Vehicle being evaluated.

        as_of_date:
            Date against which ownership cost is calculated.

        Returns
        -------
        dict
            Clean ownership-cost result.
        """

        if vehicle_id <= 0:
            raise ValueError("vehicle_id must be greater than zero")

        effective_date = as_of_date or date.today()

        row = self._extract_row(database_result)

        if not row:
            raise ValueError(
                f"No ownership-cost result returned for vehicle "
                f"{vehicle_id}"
            )

        result = self._normalize_result(
            row=row,
            vehicle_id=vehicle_id,
            as_of_date=effective_date,
        )

        self._validate_result(result)

        return result

    # ------------------------------------------------------------------
    # RESULT EXTRACTION
    # ------------------------------------------------------------------

    def _extract_row(self, database_result: Any) -> Dict[str, Any]:
        """
        PostgreSQL RETURNS TABLE through Supabase normally arrives as:

            [
                {...}
            ]

        Handle both list and dictionary responses.
        """

        if database_result is None:
            return {}

        if isinstance(database_result, list):

            if not database_result:
                return {}

            row = database_result[0]

            if isinstance(row, dict):
                return row

            return {}

        if isinstance(database_result, dict):
            return database_result

        return {}

    # ------------------------------------------------------------------
    # NORMALIZATION
    # ------------------------------------------------------------------

    def _normalize_result(
        self,
        row: Dict[str, Any],
        vehicle_id: int,
        as_of_date: date,
    ) -> Dict[str, Any]:
        """
        Convert PostgreSQL numeric values into JSON-safe Python values.
        """

        normalized: Dict[str, Any] = {
            "vehicle_id": vehicle_id,
            "purchase_price": self._number(
                row.get("purchase_price")
            ),
            "total_fuel_cost": self._number(
                row.get("total_fuel_cost")
            ),
            "total_maintenance_cost": self._number(
                row.get("total_maintenance_cost")
            ),
            "total_insurance_cost": self._number(
                row.get("total_insurance_cost")
            ),
            "total_tax_cost": self._number(
                row.get("total_tax_cost")
            ),
            "total_repair_cost": self._number(
                row.get("total_repair_cost")
            ),
            "depreciation": self._number(
                row.get("depreciation")
            ),
            "total_cost_of_ownership": self._number(
                row.get("total_cost_of_ownership")
            ),
            "ownership_days": self._integer(
                row.get("ownership_days")
            ),
            "cost_per_day": self._number(
                row.get("cost_per_day")
            ),
        }

        normalized["as_of_date"] = as_of_date.isoformat()
        normalized["currency"] = "KES"

        # --------------------------------------------------------------
        # Derived presentation values
        # --------------------------------------------------------------

        normalized["annualized_cost"] = self._annualized_cost(
            normalized["cost_per_day"]
        )

        normalized["monthly_cost"] = self._monthly_cost(
            normalized["cost_per_day"]
        )

        normalized["cost_breakdown"] = {
            "fuel": normalized["total_fuel_cost"],
            "maintenance": normalized["total_maintenance_cost"],
            "insurance": normalized["total_insurance_cost"],
            "tax": normalized["total_tax_cost"],
            "repairs": normalized["total_repair_cost"],
            "depreciation": normalized["depreciation"],
        }

        return normalized

    # ------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------

    def _validate_result(
        self,
        result: Dict[str, Any],
    ) -> None:
        """
        Validate that the database did not return impossible values.
        """

        numeric_fields = (
            "purchase_price",
            "total_fuel_cost",
            "total_maintenance_cost",
            "total_insurance_cost",
            "total_tax_cost",
            "total_repair_cost",
            "depreciation",
            "total_cost_of_ownership",
            "cost_per_day",
        )

        for field in numeric_fields:

            value = result.get(field, 0)

            if value < 0:
                logger.warning(
                    "Negative ownership value detected: %s=%s",
                    field,
                    value,
                )

        if result["ownership_days"] < 0:
            raise ValueError(
                "ownership_days cannot be negative"
            )

        if result["cost_per_day"] < 0:
            raise ValueError(
                "cost_per_day cannot be negative"
            )

        # --------------------------------------------------------------
        # Basic mathematical consistency check.
        #
        # The database function remains authoritative, therefore we
        # DON'T overwrite total_cost_of_ownership here.
        # --------------------------------------------------------------

        expected_components = (
            result["purchase_price"]
            + result["total_fuel_cost"]
            + result["total_maintenance_cost"]
            + result["total_insurance_cost"]
            + result["total_tax_cost"]
            + result["total_repair_cost"]
            + result["depreciation"]
        )

        actual_total = result["total_cost_of_ownership"]

        if actual_total > 0 and expected_components > 0:

            difference = abs(
                expected_components - actual_total
            )

            tolerance = max(
                Decimal("1.00"),
                actual_total * Decimal("0.01"),
            )

            if difference > tolerance:

                logger.warning(
                    "Ownership cost component mismatch: "
                    "components=%s total=%s difference=%s",
                    expected_components,
                    actual_total,
                    difference,
                )

    # ------------------------------------------------------------------
    # NUMERIC HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _number(value: Any) -> float:
        """
        Safely convert PostgreSQL numeric/Decimal/string values
        into a Python float.

        This specifically prevents errors such as:

            unsupported operand type(s) for /:
            'str' and 'int'
        """

        if value is None:
            return 0.0

        if isinstance(value, Decimal):
            return float(value)

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):

            value = value.strip()

            if not value:
                return 0.0

            try:
                return float(value)

            except ValueError as exc:
                raise ValueError(
                    f"Invalid numeric value: {value}"
                ) from exc

        try:
            return float(value)

        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Unable to convert value to number: {value!r}"
            ) from exc

    @staticmethod
    def _integer(value: Any) -> int:
        """
        Safely convert database values to integer.
        """

        if value is None:
            return 0

        if isinstance(value, int):
            return value

        if isinstance(value, Decimal):
            return int(value)

        if isinstance(value, float):
            return int(value)

        if isinstance(value, str):

            value = value.strip()

            if not value:
                return 0

            try:
                return int(float(value))

            except ValueError as exc:
                raise ValueError(
                    f"Invalid integer value: {value}"
                ) from exc

        try:
            return int(value)

        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Unable to convert value to integer: {value!r}"
            ) from exc

    # ------------------------------------------------------------------
    # PRESENTATION CALCULATIONS
    # ------------------------------------------------------------------

    @staticmethod
    def _monthly_cost(cost_per_day: float) -> float:
        """
        Convert daily ownership cost to an average monthly cost.

        Uses 365 / 12 rather than a hard-coded 30-day month.
        """

        if cost_per_day <= 0:
            return 0.0

        return round(
            cost_per_day * (365.0 / 12.0),
            2,
        )

    @staticmethod
    def _annualized_cost(cost_per_day: float) -> float:
        """
        Convert daily ownership cost to annualized ownership cost.
        """

        if cost_per_day <= 0:
            return 0.0

        return round(
            cost_per_day * 365.0,
            2,
        )
