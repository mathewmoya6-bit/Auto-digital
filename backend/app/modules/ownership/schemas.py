"""
Auto-D Kenya
Vehicle Ownership Cost API

Uses the PostgreSQL function:

public.calculate_vehicle_ownership_cost(
    p_vehicle_id integer,
    p_as_of_date date
)

The database function is the single source of truth for
vehicle ownership-cost calculations.
"""

import logging
from datetime import date
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.core.database import get_supabase
from app.modules.ownership.schemas import (
    OwnershipCostRequest,
    OwnershipCostResponse,
    OwnershipCostResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ownership",
    tags=["Vehicle Ownership Cost"],
)


@router.post(
    "/calculate",
    response_model=OwnershipCostResult,
    summary="Calculate vehicle ownership cost",
)
async def calculate_ownership_cost(
    request: OwnershipCostRequest,
):
    """
    Calculate the total ownership cost of a vehicle.

    Database function:
        calculate_vehicle_ownership_cost(integer, date)

    Returns:
        - Purchase price
        - Fuel cost
        - Maintenance cost
        - Insurance cost
        - Tax cost
        - Repair cost
        - Depreciation
        - Total cost of ownership
        - Ownership days
        - Cost per day
    """

    try:
        supabase = get_supabase()

        as_of_date = request.as_of_date or date.today()

        logger.info(
            "Calculating ownership cost: vehicle_id=%s, as_of_date=%s",
            request.vehicle_id,
            as_of_date,
        )

        result = supabase.rpc(
            "calculate_vehicle_ownership_cost",
            {
                "p_vehicle_id": request.vehicle_id,
                "p_as_of_date": as_of_date.isoformat(),
            },
        ).execute()

        if not result.data:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No ownership-cost data found for "
                    f"vehicle_id={request.vehicle_id}"
                ),
            )

        # PostgreSQL RETURNS TABLE normally comes back as a list.
        row = result.data[0] if isinstance(result.data, list) else result.data

        data = OwnershipCostResponse(
            vehicle_id=int(row.get("vehicle_id", request.vehicle_id)),
            purchase_price=float(row.get("purchase_price") or 0),
            total_fuel_cost=float(row.get("total_fuel_cost") or 0),
            total_maintenance_cost=float(
                row.get("total_maintenance_cost") or 0
            ),
            total_insurance_cost=float(
                row.get("total_insurance_cost") or 0
            ),
            total_tax_cost=float(row.get("total_tax_cost") or 0),
            total_repair_cost=float(row.get("total_repair_cost") or 0),
            depreciation=float(row.get("depreciation") or 0),
            total_cost_of_ownership=float(
                row.get("total_cost_of_ownership") or 0
            ),
            ownership_days=int(row.get("ownership_days") or 0),
            cost_per_day=float(row.get("cost_per_day") or 0),
        )

        return OwnershipCostResult(
            success=True,
            data=data,
            currency="KES",
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Vehicle ownership cost calculation failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=f"Ownership cost calculation failed: {str(exc)}",
        )
