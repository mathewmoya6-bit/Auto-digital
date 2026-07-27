"""
Fuel Repository - Data access layer for fuel prices
"""

from datetime import date
from typing import Optional, List, Dict, Any

from app.core.database import supabase

import logging

logger = logging.getLogger(__name__)


class FuelRepository:

    def __init__(self):
        self.table = "fuel_prices"

    # ------------------------------
    # Internal helper
    # ------------------------------

    def _get_fuel_type_id(self, fuel_type: str) -> Optional[int]:
        """
        Convert fuel type name to ID.
        Requires a fuel_types table.
        """

        try:
            response = (
                supabase
                .table("fuel_types")
                .select("id")
                .ilike("name", fuel_type)
                .limit(1)
                .execute()
            )

            if response.data:
                return response.data[0]["id"]

            return None

        except Exception as e:
            logger.error(e)
            return None

    # ------------------------------

    def get_all_fuel_prices(self):

        try:

            response = (
                supabase
                .table(self.table)
                .select("*")
                .order("fuel_type_id")
                .execute()
            )

            return response.data

        except Exception as e:

            logger.error(e)

            return []

    # ------------------------------

    def get_fuel_price(self, fuel_type):

        fuel_type_id = self._get_fuel_type_id(fuel_type)

        if not fuel_type_id:
            return None

        try:

            response = (
                supabase
                .table(self.table)
                .select("*")
                .eq("fuel_type_id", fuel_type_id)
                .is_("effective_to", None)
                .limit(1)
                .execute()
            )

            return response.data[0] if response.data else None

        except Exception as e:

            logger.error(e)

            return None

    # ------------------------------

    def get_fuel_prices_by_region(self, region):

        try:

            response = (
                supabase
                .table(self.table)
                .select("*")
                .eq("region", region)
                .execute()
            )

            return response.data

        except Exception as e:

            logger.error(e)

            return []

    # ------------------------------

    def upsert_fuel_price(
        self,
        fuel_type,
        price,
        region="Kenya"
    ):

        fuel_type_id = self._get_fuel_type_id(fuel_type)

        if not fuel_type_id:

            raise Exception(
                f"Unknown fuel type: {fuel_type}"
            )

        try:

            # Close previous active record

            (
                supabase
                .table(self.table)
                .update({
                    "effective_to": date.today()
                })
                .eq("fuel_type_id", fuel_type_id)
                .is_("effective_to", None)
                .execute()
            )

            payload = {

                "fuel_type_id": fuel_type_id,

                "region": region,

                "price_per_unit": price,

                "effective_from": date.today(),

                "effective_to": None,

                "source": "Admin",

                "unit": "Litre"

            }

            response = (
                supabase
                .table(self.table)
                .insert(payload)
                .execute()
            )

            return response.data[0]

        except Exception as e:

            logger.exception(e)

            return None

    # ------------------------------

    def delete_fuel_price(self, fuel_type):

        fuel_type_id = self._get_fuel_type_id(fuel_type)

        if not fuel_type_id:
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

            logger.error(e)

            return False

    # ------------------------------

    def get_fuel_price_history(
        self,
        fuel_type,
        limit=30
    ):

        fuel_type_id = self._get_fuel_type_id(fuel_type)

        if not fuel_type_id:
            return []

        try:

            response = (
                supabase
                .table(self.table)
                .select("*")
                .eq("fuel_type_id", fuel_type_id)
                .order("effective_from", desc=True)
                .limit(limit)
                .execute()
            )

            return response.data

        except Exception as e:

            logger.error(e)

            return []
