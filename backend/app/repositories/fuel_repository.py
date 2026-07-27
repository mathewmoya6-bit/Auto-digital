"""
Fuel Repository - Data access layer for fuel prices
Production Ready
"""

from datetime import date, timedelta
from typing import Optional, List, Dict, Any

import logging

from app.core.database import supabase

logger = logging.getLogger(__name__)


class FuelRepository:
    """Repository for fuel price operations"""

    def __init__(self):
        self.table = "fuel_prices"

    # ---------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------

    def _get_fuel_type_id(self, fuel_type: str) -> Optional[int]:
        """Lookup fuel type ID."""

        try:
            response = (
                supabase
                .table("fuel_types")
                .select("id")
                .ilike("name", fuel_type.strip())
                .limit(1)
                .execute()
            )

            if response.data:
                return response.data[0]["id"]

            logger.warning(f"Fuel type '{fuel_type}' not found.")
            return None

        except Exception as e:
            logger.exception(e)
            return None

    # ---------------------------------------------------------

    def get_all_fuel_prices(self) -> List[Dict[str, Any]]:
        """
        Returns latest active fuel prices.
        """

        try:

            response = (
                supabase
                .table(self.table)
                .select("""
                    *,
                    fuel_types(name)
                """)
                .is_("effective_to", None)
                .order("fuel_type_id")
                .execute()
            )

            return response.data

        except Exception as e:

            logger.exception(e)
            return []

    # ---------------------------------------------------------

    def get_fuel_price(
        self,
        fuel_type: str
    ) -> Optional[Dict[str, Any]]:

        fuel_type_id = self._get_fuel_type_id(fuel_type)

        if fuel_type_id is None:
            return None

        try:

            response = (
                supabase
                .table(self.table)
                .select("""
                    *,
                    fuel_types(name)
                """)
                .eq("fuel_type_id", fuel_type_id)
                .is_("effective_to", None)
                .limit(1)
                .execute()
            )

            if response.data:
                return response.data[0]

            return None

        except Exception as e:

            logger.exception(e)
            return None

    # ---------------------------------------------------------

    def get_fuel_prices_by_region(
        self,
        region: str
    ) -> List[Dict[str, Any]]:

        try:

            response = (
                supabase
                .table(self.table)
                .select("""
                    *,
                    fuel_types(name)
                """)
                .eq("region", region)
                .is_("effective_to", None)
                .order("fuel_type_id")
                .execute()
            )

            return response.data

        except Exception as e:

            logger.exception(e)
            return []

    # ---------------------------------------------------------

    def upsert_fuel_price(
        self,
        fuel_type: str,
        price: float,
        region: str = "Kenya",
        source: str = "Admin",
        unit: str = "Litre"
    ) -> Optional[Dict[str, Any]]:

        fuel_type_id = self._get_fuel_type_id(fuel_type)

        if fuel_type_id is None:
            raise ValueError(f"Unknown fuel type: {fuel_type}")

        try:

            #
            # Close previous active price
            #

            (
                supabase
                .table(self.table)
                .update({
                    "effective_to": date.today() - timedelta(days=1)
                })
                .eq("fuel_type_id", fuel_type_id)
                .eq("region", region)
                .is_("effective_to", None)
                .execute()
            )

            #
            # Insert new active price
            #

            payload = {

                "fuel_type_id": fuel_type_id,

                "region": region,

                "price_per_unit": float(price),

                "effective_from": date.today(),

                "effective_to": None,

                "source": source,

                "unit": unit

            }

            response = (
                supabase
                .table(self.table)
                .insert(payload)
                .execute()
            )

            if response.data:
                return response.data[0]

            return None

        except Exception as e:

            logger.exception(e)
            return None

    # ---------------------------------------------------------

    def delete_fuel_price(
        self,
        fuel_type: str
    ) -> bool:

        fuel_type_id = self._get_fuel_type_id(fuel_type)

        if fuel_type_id is None:
            return False

        try:

            (
                supabase
                .table(self.table)
                .delete()
                .eq("fuel_type_id", fuel_type_id)
                .execute()
            )

            return True

        except Exception as e:

            logger.exception(e)
            return False

    # ---------------------------------------------------------

    def get_fuel_price_history(
        self,
        fuel_type: str,
        limit: int = 30
    ) -> List[Dict[str, Any]]:

        fuel_type_id = self._get_fuel_type_id(fuel_type)

        if fuel_type_id is None:
            return []

        try:

            response = (
                supabase
                .table(self.table)
                .select("""
                    *,
                    fuel_types(name)
                """)
                .eq("fuel_type_id", fuel_type_id)
                .order("effective_from", desc=True)
                .limit(limit)
                .execute()
            )

            return response.data

        except Exception as e:

            logger.exception(e)
            return []
