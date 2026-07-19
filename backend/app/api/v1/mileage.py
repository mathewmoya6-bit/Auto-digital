# backend/app/api/v1/mileage.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.request import MileageRateRequest
from app.schemas.response import MileageRateResponse
from app.services.vehicle_service import VehicleService
from app.engines.mileage_rate_engine import MileageRateEngine
# CHANGED: get_current_user -> get_current_user_optional, same reasoning
# as running_cost.py — this is a public calculator endpoint.
from app.core.security import get_current_user_optional

router = APIRouter()
vehicle_service = VehicleService()
mileage_engine = MileageRateEngine()


@router.post("/calculate")
async def calculate_mileage_rate(
    request: MileageRateRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
) -> MileageRateResponse:
    """Calculate mileage rate for a vehicle"""
    # Get vehicle details
    vehicle = vehicle_service.get_variant(request.variant_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )

    # CHANGED: was `mileage_engine.calculate(vehicle, request)` — that
    # method doesn't exist on MileageRateEngine, only
    # `calculate_mileage_rate` does (see app/engines/mileage_rate_engine.py).
    # The old code would raise AttributeError on every single request.
    response = mileage_engine.calculate_mileage_rate(vehicle, request)
    return response
