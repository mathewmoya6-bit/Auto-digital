"""
Auto-D Kenya
Ownership Service

Production service layer.

Responsibilities:
- Accept validated OwnershipCostRequest
- Delegate calculation to OwnershipEngine
- Provide a stable service interface for the router/other modules

The service does NOT:
- query user_vehicles
- calculate fuel costs itself
- calculate depreciation itself
- maintain duplicate pricing tables
- perform demo/fallback calculations

The PostgreSQL function
    public.calculate_vehicle_running_cost_v2(jsonb)

remains the calculation source of truth.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.modules.ownership.engine import OwnershipEngine
from app.modules.ownership.schemas import OwnershipCostRequest

logger = logging.getLogger(__name__)


class OwnershipService:
    """
    Production Ownership/TCO service.
    """

    def __init__(self) -> None:
        self.engine = OwnershipEngine()

    async def calculate_tco(
        self,
        request: OwnershipCostRequest,
    ) -> Dict[str, Any]:
        """
        Calculate total vehicle ownership/running cost.

        Delegates the actual calculation to OwnershipEngine.
        """

        try:
            return await self.engine.calculate(request)

        except Exception:
            logger.exception(
                "Ownership service calculation failed for CRSP ID %s",
                request.vehicle_crsp_id,
            )
            raise

    async def calculate_ownership_cost(
        self,
        request: OwnershipCostRequest,
    ) -> Dict[str, Any]:
        """
        Alias for calculate_tco().

        Kept for compatibility with existing callers.
        """

        return await self.calculate_tco(request)
