# app/modules/ownership/repository.py
"""
Vehicle Ownership Cost Repository
Auto-D Kenya

This repository is ONLY responsible for calling the PostgreSQL
calculate_vehicle_ownership_cost() function.

It does NOT calculate ownership costs in Python.
PostgreSQL remains the single source of truth.
"""

import logging
from datetime import date
from typing import Any, Dict, Optional

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class OwnershipRepository:
    """Repository for vehicle ownership cost calculations."""

    def __init__(self):
        self.supabase = get_supabase()

    async def calculate_vehicle_ownership_cost(
        self,
        vehicle_id: int,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Call PostgreSQL:

            calculate_vehicle_ownership_cost(integer, date)

        Returns the database result as a dictionary.
        """

        if not vehicle_id:
            raise ValueError("vehicle_id is required")

        calculation_date = as_of_date or date.today()

        logger.info(
            "Calculating vehicle ownership cost: "
            "vehicle_id=%s, as_of_date=%s",
            vehicle_id,
            calculation_date,
        )

        try:
            response = self.supabase.rpc(
                "calculate_vehicle_ownership_cost",
                {
                    "p_vehicle_id": int(vehicle_id),
                    "p_as_of_date": calculation_date.isoformat(),
                },
            ).execute()

            data = response.data

            logger.info(
                "Ownership RPC response for vehicle_id=%s: %s",
                vehicle_id,
                data,
            )

            if data is None:
                raise ValueError(
                    f"No ownership-cost result returned for vehicle {vehicle_id}"
                )

            # PostgreSQL TABLE-returning functions normally arrive as
            # a list containing one row.
            if isinstance(data, list):
                if not data:
                    raise ValueError(
                        f"No ownership-cost result returned for vehicle {vehicle_id}"
                    )

                data = data[0]

            if not isinstance(data, dict):
                raise TypeError(
                    "Unexpected ownership RPC response type: "
                    f"{type(data).__name__}"
                )

            return data

        except Exception as exc:
            logger.exception(
                "Ownership calculation failed for vehicle_id=%s",
                vehicle_id,
            )
            raise RuntimeError(
                f"Failed to calculate ownership cost for vehicle "
                f"{vehicle_id}: {exc}"
            ) from exc
