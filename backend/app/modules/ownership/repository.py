# app/modules/ownership/repository.py
"""
Auto-D Kenya - Ownership Repository

Database access layer for TCO calculations.

The repository deliberately keeps SQL/Supabase access out of the service.
It is tolerant of the current Auto-D schema and uses existing tables where
available instead of depending on the old vehicle_running_cost_rates table.
"""

import logging
from datetime import date
from typing import Any, Dict, Optional

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class OwnershipRepository:
    """Supabase repository for Auto-D ownership/TCO data."""

    def __init__(self, supabase=None):
        self.supabase = supabase or get_supabase()

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _number(value: Any, default: float = 0.0) -> float:
        if value is None:
            return default
        try:
            if isinstance(value, str):
                value = value.strip().replace(",", "")
                if not value:
                    return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _first(data):
        return data[0] if data else None

    async def _safe_query(self, table: str, query_builder):
        """
        Execute a Supabase query without allowing an optional cost table
        to break the entire TCO calculation.
        """
        try:
            result = query_builder.execute()
            return result.data or []
        except Exception as exc:
            logger.warning(
                "Ownership repository query failed for %s: %s",
                table,
                exc,
            )
            return []

    # ------------------------------------------------------------------
    # Vehicle / CRSP
    # ------------------------------------------------------------------

    async def get_vehicle_crsp(self, crsp_id: int) -> Dict[str, Any]:
        """
        Get the authoritative CRSP vehicle.

        Primary source: vehicle_crsp.
        Fallback: vehicle_crsp_lookup if the deployment still exposes it.
        """

        tables = ("vehicle_crsp", "vehicle_crsp_lookup")

        for table in tables:
            try:
                result = (
                    self.supabase
                    .table(table)
                    .select("*")
                    .eq("crsp_id", crsp_id)
                    .limit(1)
                    .execute()
                )

                if result.data:
                    return result.data[0]

            except Exception as exc:
                logger.warning(
                    "Unable to read %s for CRSP %s: %s",
                    table,
                    crsp_id,
                    exc,
                )

        return {}

    # ------------------------------------------------------------------
    # Fuel prices
    # ------------------------------------------------------------------

    async def get_fuel_price(
        self,
        fuel_type: str,
        region: Optional[str] = None,
    ) -> float:
        """
        Get the latest Auto-D fuel price.

        Priority:
          1. latest_fuel_prices
          2. fuel_prices
          3. county_fuel_prices

        Returns 0 for EV because electricity is handled separately.
        """

        fuel = (fuel_type or "petrol").strip().lower()

        if fuel in {"electric", "ev"}:
            return 0.0

        # 1. latest_fuel_prices
        try:
            query = (
                self.supabase
                .table("latest_fuel_prices")
                .select("fuel_type,price,price_date,region")
                .ilike("fuel_type", fuel)
                .order("price_date", desc=True)
                .limit(1)
            )

            if region:
                query = query.ilike("region", region)

            rows = await self._safe_query("latest_fuel_prices", query)

            if rows:
                price = self._number(rows[0].get("price"))
                if price > 0:
                    return price

        except Exception as exc:
            logger.warning("latest_fuel_prices lookup failed: %s", exc)

        # 2. fuel_prices
        try:
            query = (
                self.supabase
                .table("fuel_prices")
                .select("fuel_type,price,price_date,region,is_active")
                .ilike("fuel_type", fuel)
                .eq("is_active", True)
                .order("price_date", desc=True)
                .limit(1)
            )

            if region:
                query = query.ilike("region", region)

            rows = await self._safe_query("fuel_prices", query)

            if rows:
                price = self._number(rows[0].get("price"))
                if price > 0:
                    return price

        except Exception as exc:
            logger.warning("fuel_prices lookup failed: %s", exc)

        # 3. County averages
        column_map = {
            "petrol": "petrol_price",
            "gasoline": "petrol_price",
            "diesel": "diesel_price",
            "hybrid": "hybrid_price",
            "lpg": "lpg_price",
        }

        column = column_map.get(fuel)

        if column:
            try:
                rows = await self._safe_query(
                    "county_fuel_prices",
                    (
                        self.supabase
                        .table("county_fuel_prices")
                        .select(column)
                        .order("effective_date", desc=True)
                        .limit(20)
                    ),
                )

                values = [
                    self._number(row.get(column))
                    for row in rows
                    if self._number(row.get(column)) > 0
                ]

                if values:
                    return sum(values) / len(values)

            except Exception as exc:
                logger.warning(
                    "county_fuel_prices lookup failed: %s",
                    exc,
                )

        # Do not silently invent a price here. The service can apply its
        # request/default value when the database contains no current price.
        return 0.0

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    async def get_maintenance_rate(
        self,
        vehicle_type: Optional[str] = None,
        category_id: Optional[int] = None,
    ) -> float:
        """
        Resolve maintenance KES/km from maintenance_defaults.

        Supported current schema:
            maintenance_defaults.category_id

        If a rate column exists under another deployment version, the query
        below intentionally selects * and detects common rate names.
        """

        try:
            query = (
                self.supabase
                .table("maintenance_defaults")
                .select("*")
                .limit(20)
            )

            if category_id is not None:
                query = query.eq("category_id", category_id)

            rows = await self._safe_query("maintenance_defaults", query)

            if rows:
                preferred = (
                    "cost_per_km",
                    "maintenance_cost_per_km",
                    "rate_per_km",
                    "service_cost_per_km",
                    "rate",
                    "amount",
                    "fixed_amount",
                    "base_rate",
                )

                for row in rows:
                    for key in preferred:
                        value = self._number(row.get(key))
                        if value > 0:
                            return value

        except Exception as exc:
            logger.warning(
                "maintenance_defaults lookup failed: %s",
                exc,
            )

        # Current known Auto-D baseline.
        return {
            "petrol": 2.50,
            "diesel": 3.00,
            "hybrid": 2.00,
            "electric": 1.50,
            "ev": 1.50,
            "lpg": 2.20,
            "cng": 2.00,
        }.get((vehicle_type or "petrol").lower(), 2.50)

    # ------------------------------------------------------------------
    # Tyres
    # ------------------------------------------------------------------

    async def get_tyre_rate(
        self,
        category_id: Optional[int] = None,
    ) -> float:
        """Resolve tyre cost per kilometre from tyre_defaults."""

        try:
            query = (
                self.supabase
                .table("tyre_defaults")
                .select("*")
                .limit(20)
            )

            if category_id is not None:
                query = query.eq("category_id", category_id)

            rows = await self._safe_query("tyre_defaults", query)

            preferred = (
                "cost_per_km",
                "tyre_cost_per_km",
                "rate_per_km",
                "amount_per_km",
                "rate",
                "amount",
                "fixed_amount",
            )

            for row in rows:
                for key in preferred:
                    value = self._number(row.get(key))
                    if value > 0:
                        return value

        except Exception as exc:
            logger.warning(
                "tyre_defaults lookup failed: %s",
                exc,
            )

        return 0.80

    # ------------------------------------------------------------------
    # Insurance
    # ------------------------------------------------------------------

    async def get_insurance_rate(
        self,
        vehicle_type: Optional[str] = None,
        category_id: Optional[int] = None,
    ) -> float:
        """
        Return insurance percentage.

        insurance_rates.base_rate is assumed to be a percentage when
        populated. minimum/maximum premiums are not used here because the
        service currently models insurance as a percentage of vehicle value.
        """

        try:
            query = (
                self.supabase
                .table("insurance_rates")
                .select(
                    "vehicle_type,category_id,insurance_type,"
                    "base_rate,minimum_premium,maximum_premium,"
                    "effective_from,effective_to"
                )
                .limit(50)
            )

            if vehicle_type:
                query = query.ilike("vehicle_type", vehicle_type)

            if category_id is not None:
                query = query.eq("category_id", category_id)

            rows = await self._safe_query("insurance_rates", query)

            today = date.today()

            for row in rows:
                effective_from = row.get("effective_from")
                effective_to = row.get("effective_to")

                if effective_from and str(effective_from) > str(today):
                    continue

                if effective_to and str(effective_to) < str(today):
                    continue

                rate = self._number(row.get("base_rate"))

                if rate > 0:
                    return rate

        except Exception as exc:
            logger.warning(
                "insurance_rates lookup failed: %s",
                exc,
            )

        # Existing Auto-D default if no database rate is populated.
        return 3.0

    # ------------------------------------------------------------------
    # Depreciation
    # ------------------------------------------------------------------

    async def get_depreciation_factor(
        self,
        category_id: Optional[int],
        age: int,
    ) -> float:
        """
        Return depreciation factor for the current vehicle age.

        The current depreciation_rates table contains:
            year_1 ... year_5
            year_6_plus

        The values supplied in the Auto-D database are factors such as:
            0.90, 0.80, 0.70, ...

        These are interpreted as residual-value factors, not annual
        depreciation percentages. Therefore the annual depreciation rate is
        calculated as the reduction from the previous residual factor.
        """

        age = max(int(age or 0), 0)

        # New vehicle / first year.
        if age <= 0:
            return 0.0

        try:
            query = (
                self.supabase
                .table("depreciation_rates")
                .select(
                    "category_id,year_1,year_2,year_3,"
                    "year_4,year_5,year_6_plus"
                )
                .limit(20)
            )

            if category_id is not None:
                query = query.eq("category_id", category_id)

            rows = await self._safe_query(
                "depreciation_rates",
                query,
            )

            row = self._first(rows)

            if row:
                residuals = [
                    1.0,
                    self._number(row.get("year_1"), 0.90),
                    self._number(row.get("year_2"), 0.80),
                    self._number(row.get("year_3"), 0.70),
                    self._number(row.get("year_4"), 0.60),
                    self._number(row.get("year_5"), 0.50),
                    self._number(row.get("year_6_plus"), 0.40),
                ]

                index = min(age, 6)

                previous = residuals[index - 1]
                current = residuals[index]

                if index == 6:
                    current = residuals[6]

                # Avoid negative or nonsensical rates.
                return max(0.0, min(previous - current, 1.0))

        except Exception as exc:
            logger.warning(
                "depreciation_rates lookup failed: %s",
                exc,
            )

        # Safe Auto-D fallback: annual rate by vehicle age.
        fallback = {
            1: 0.10,
            2: 0.10,
            3: 0.10,
            4: 0.10,
            5: 0.10,
        }

        return fallback.get(age, 0.10)

    # ------------------------------------------------------------------
    # Combined cost inputs
    # ------------------------------------------------------------------

    async def get_cost_inputs(
        self,
        fuel_type: str,
        vehicle_type: str,
        vehicle_category: Optional[str] = None,
        category_id: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Load all variable running-cost inputs in one repository call.

        The returned keys match OwnershipService:
            fuel_price
            maintenance_per_km
            tyre_per_km
            insurance_rate
        """

        fuel_price = await self.get_fuel_price(fuel_type)

        maintenance = await self.get_maintenance_rate(
            vehicle_type=vehicle_type,
            category_id=category_id,
        )

        tyres = await self.get_tyre_rate(
            category_id=category_id,
        )

        insurance = await self.get_insurance_rate(
            vehicle_type=vehicle_type,
            category_id=category_id,
        )

        return {
            "fuel_price": fuel_price,
            "maintenance_per_km": maintenance,
            "tyre_per_km": tyres,
            "insurance_rate": insurance,
        }
