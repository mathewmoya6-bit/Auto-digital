# backend/app/api/v1/running_cost.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.request import RunningCostRequest
from app.schemas.response import RunningCostResponse
from app.services.vehicle_service import VehicleService
from app.engines.running_cost_engine import RunningCostEngine
from app.core.security import get_current_user

router = APIRouter()
vehicle_service = VehicleService()
running_cost_engine = RunningCostEngine()

@router.post("/calculate")
async def calculate_running_cost(
    request: RunningCostRequest,
    current_user: dict = Depends(get_current_user)
) -> RunningCostResponse:
    """Calculate running cost for a vehicle"""
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
