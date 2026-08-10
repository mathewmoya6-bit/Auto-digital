import logging
from typing import Any, Dict

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class ValuationRepository:

    def __init__(self):
        self.supabase = get_supabase()

    def calculate_valuation(
        self,
        vehicle_crsp_id: int,
        manufacture_year: int,
        mileage_km: int,
        vehicle_type: str = "SEDAN",
        condition_name: str = "GOOD",
        accident_status: str = "NONE",
        location_name: str = "NAIROBI",
        profit_margin_percent: float = 5.00,
    ) -> Dict[str, Any]:

        params = {
            "p_vehicle_crsp_id": vehicle_crsp_id,
            "p_manufacture_year": manufacture_year,
            "p_mileage_km": mileage_km,
            "p_vehicle_type": vehicle_type,
            "p_condition_name": condition_name,
            "p_accident_status": accident_status,
            "p_location_name": location_name,
            "p_profit_margin_percent": profit_margin_percent,
        }

        logger.info(
            "Calculating valuation for CRSP %s",
            vehicle_crsp_id,
        )

        response = (
            self.supabase
            .rpc(
                "calculate_vehicle_valuation",
                params,
            )
            .execute()
        )

        if not response.data:
            raise ValueError(
                f"No valuation result returned for CRSP {vehicle_crsp_id}"
            )

        # PostgreSQL RETURNS TABLE normally returns a list.
        result = response.data[0]

        return result
