"""
Settings Repository
Production Ready
"""

import json
import logging
from typing import Any, Dict, Optional

from app.core.database import supabase

logger = logging.getLogger(__name__)


class SettingsRepository:

    def __init__(self):
        self.table = "settings"

    # ---------------------------------------------------------
    # Generic Setting
    # ---------------------------------------------------------

    def get_setting(self, key: str) -> Optional[Any]:
        try:

            response = (
                supabase.table(self.table)
                .select("value")
                .eq("key", key)
                .limit(1)
                .execute()
            )

            if response.data:
                value = response.data[0]["value"]

                if isinstance(value, str):
                    try:
                        return json.loads(value)
                    except Exception:
                        return value

                return value

            return None

        except Exception as e:
            logger.exception(e)
            return None

    # ---------------------------------------------------------
    # Engine Settings
    # ---------------------------------------------------------

    def get_engine_settings(self) -> Dict[str, Any]:

        defaults = {
            "depreciation_rate": 0.15,
            "insurance_rate": 0.045,
            "annual_mileage": 20000,
            "tyre_lifespan": 45000,
            "service_interval": 10000,
        }

        settings = self.get_setting("engine_settings")

        if isinstance(settings, dict):
            defaults.update(settings)

        return defaults

    # ---------------------------------------------------------
    # Fuel Prices
    # ---------------------------------------------------------

    def get_fuel_prices_from_settings(self) -> Dict[str, float]:
        """
        Read current fuel prices directly from fuel_prices table.
        """

        prices = {
            "petrol": 214.03,
            "diesel": 202.75,
            "hybrid": 214.03,
            "electric": 30.00,
            "cng": 120.00,
            "lpg": 120.00,
            "hydrogen": 300.00
        }

        try:

            response = (
                supabase.table("fuel_prices")
                .select("""
                    price_per_unit,
                    fuel_types(name)
                """)
                .is_("effective_to", None)
                .execute()
            )

            for row in response.data:

                fuel = row["fuel_types"]["name"].lower()

                prices[fuel] = float(row["price_per_unit"])

            return prices

        except Exception as e:
            logger.exception(e)
            return prices

    # ---------------------------------------------------------
    # Valuation Settings
    # ---------------------------------------------------------

    def get_valuation_settings(self):

        defaults = {

            "condition_multipliers": {

                "excellent": 1.10,
                "very_good": 1.05,
                "good": 1.00,
                "fair": 0.85,
                "poor": 0.70

            },

            "location_multipliers": {

                "nairobi": 1.05,
                "mombasa": 0.98,
                "kisumu": 0.95,
                "nakuru": 0.97,
                "eldoret": 0.96,
                "other": 0.95

            }

        }

        settings = self.get_setting("valuation_settings")

        if isinstance(settings, dict):
            defaults.update(settings)

        return defaults

    # ---------------------------------------------------------
    # Update Engine Settings
    # ---------------------------------------------------------

    def update_engine_settings(self, settings: Dict[str, Any]) -> bool:

        try:

            response = (
                supabase.table(self.table)
                .upsert(
                    {
                        "key": "engine_settings",
                        "value": json.dumps(settings),
                    },
                    on_conflict="key",
                )
                .execute()
            )

            return bool(response.data)

        except Exception as e:
            logger.exception(e)
            return False
