"""
Auto-D Kenya
Vehicle Ownership Repository

Database access layer for vehicle ownership cost calculations.
"""

import logging
from datetime import date
from typing import Any, Dict, Optional

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class OwnershipRepository:

    FUNCTION_NAME = "calculate_vehicle_ownership_cost"

    def __init__(self):
        self.supabase = get_supabase()

    async def calculate_ownership_cost(
        self,
        vehicle_id: int,
        as_of_date: date,
    ) -> Dict[str, Any]:

        if not vehicle_id or vehicle_id <= 0:
            raise ValueError("vehicle_id must be greater than zero")

        if as_of_date is None:
            as_of_date = date.today()

        logger.info(
            "Calling PostgreSQL function %s "
            "vehicle_id=%s as_of_date=%s",
            self.FUNCTION_NAME,
            vehicle_id,
            as_of_date,
        )

        try:

            response = self.supabase.rpc(
                self.FUNCTION_NAME,
                {
                    "p_vehicle_id": int(vehicle_id),
                    "p_as_of_date": as_of_date.isoformat(),
                },
            ).execute()

            logger.info(
                "Ownership RPC returned successfully: "
                "vehicle_id=%s data=%s",
                vehicle_id,
                response.data,
            )

            if not response.data:
                raise ValueError(
                    f"No ownership cost returned for "
                    f"vehicle_id={vehicle_id}"
                )

            if isinstance(response.data, list):
                return response.data[0]

            if isinstance(response.data, dict):
                return response.data

            raise ValueError(
                "Unexpected ownership RPC response format"
            )

        except Exception as exc:

            logger.exception(
                "Ownership RPC failed: "
                "function=%s vehicle_id=%s as_of_date=%s "
                "error=%s",
                self.FUNCTION_NAME,
                vehicle_id,
                as_of_date,
                exc,
            )

            raise
