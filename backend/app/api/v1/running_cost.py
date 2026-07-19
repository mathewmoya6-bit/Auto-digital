# backend/app/api/v1/running_cost.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.request import RunningCostRequest
from app.schemas.response import RunningCostResponse
from app.services.vehicle_service import VehicleService
from app.engines.running_cost_engine import RunningCostEngine
# CHANGED: get_current_user -> get_current_user_optional so this public
# calculator endpoint doesn't 401 for anonymous visitors. current_user is
# now Optional[dict] and will be None when no/invalid bearer token is sent.
from app.core.security import get_current_user_optional

router = APIRouter()
vehicle_service = VehicleService()
running_cost_engine = RunningCostEngine()


@router.post("/calculate")
async def calculate_running_cost(
    request: RunningCostRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
) -> RunningCostResponse:
    """Calculate running cost for a vehicle. Works anonymously; if a valid
    Supabase session token is supplied, current_user will be populated
    (useful for e.g. saving the report against an account later)."""
    # Get vehicle details
    vehicle = vehicle_service.get_variant(request.variant_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )

    # Calculate running cost
    response = running_cost_engine.calculate(vehicle, request)
    return response
