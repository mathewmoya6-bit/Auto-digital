# backend/app/api/v1/ownership.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.request import OwnershipCostRequest
from app.schemas.response import OwnershipCostResponse
from app.services.vehicle_service import VehicleService
from app.engines.ownership_engine import OwnershipEngine
from app.core.security import get_current_user

router = APIRouter()
vehicle_service = VehicleService()
ownership_engine = OwnershipEngine()

@router.post("/calculate")
async def calculate_ownership_cost(
    request: OwnershipCostRequest,
    current_user: dict = Depends(get_current_user)
) -> OwnershipCostResponse:
    """Calculate total ownership cost over time"""
    # Get vehicle details
    vehicle = vehicle_service.get_variant(request.variant_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # Calculate ownership cost
    response = ownership_engine.calculate(vehicle, request)
    return response
