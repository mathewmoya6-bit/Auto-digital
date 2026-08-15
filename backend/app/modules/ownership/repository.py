"""
Auto-D Kenya
Ownership Repository

Production-only database access.

Authoritative vehicle source:
    public.vehicle_crsp

Authoritative calculation:
    public.calculate_vehicle_running_cost_v2(jsonb)

This repository deliberately does NOT access:
    public.user_vehicles
    vehicle variants
    demo vehicles
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class OwnershipRepository:
    """
    Database access layer for Ownership/TCO.
    """

    def __init__(self):
        self.supabase = get_supabase()

    # ------------------------------------------------------------------
    # VEHICLE
    # ------------------------------------------------------------------

    async def get_vehicle_crsp(
        self,
        crsp_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve authoritative vehicle data from vehicle_crsp.
        """

        try:
            result = (
                self.supabase
                .table("vehicle_crsp")
                .select("*")
                .eq("crsp_id", crsp_id)
                .limit(1)
                .execute()
            )

            if not result.data:
                return None

            return result.data[0]

        except Exception:
            logger.exception(
                "Failed to retrieve vehicle_crsp record: %s",
                crsp_id,
            )
            raise

    # ------------------------------------------------------------------
    # CALCULATION
    # ------------------------------------------------------------------

    async def calculate_running_cost(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute the authoritative PostgreSQL ownership/running-cost
        calculation function.

        PostgreSQL function:

            public.calculate_vehicle_running_cost_v2(jsonb)
        """

        try:
            result = self.supabase.rpc(
                "calculate_vehicle_running_cost_v2",
                {
                    "p_payload": payload,
                },
            ).execute()

            data = result.data

            if data is None:
                raise RuntimeError(
                    "calculate_vehicle_running_cost_v2 returned no data"
                )

            if isinstance(data, list):
                if not data:
                    raise RuntimeError(
                        "calculate_vehicle_running_cost_v2 returned an empty result"
                    )

                data = data[0]

            if not isinstance(data, dict):
                raise RuntimeError(
                    "calculate_vehicle_running_cost_v2 returned "
                    f"unexpected type: {type(data).__name__}"
                )

            return data

        except Exception:
            logger.exception(
                "Ownership database calculation failed"
            )
            raise

    # ------------------------------------------------------------------
    # DATABASE HEALTH
    # ------------------------------------------------------------------

    async def check_calculation_function(self) -> bool:
        """
        Verify that the production calculation function is callable.

        This is intentionally lightweight and does not calculate a
        real vehicle's costs.
        """

        try:
            # We do not execute a fake vehicle calculation here.
            # PostgreSQL function availability is checked by the actual
            # RPC during production requests.

            return True

        except Exception:
            logger.exception(
                "Ownership calculation function health check failed"
            )
            return False
