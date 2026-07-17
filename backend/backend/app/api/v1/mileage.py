# backend/app/api/v1/mileage.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.request import MileageRateRequest
from app.schemas.response import MileageRateResponse
from app.services.vehicle_service import VehicleService
from app.engines.mileage_rate_engine import MileageRateEngine
from app.core.security import get_current_user

router = APIRouter()
vehicle_service = VehicleService()
mileage_engine = MileageRateEngine()

@router.post("/calculate")
async def calculate_mileage_rate(
    request: MileageRateRequest,
    current_user: dict = Depends(get_current_user)
) -> MileageRateResponse:
    """Calculate mileage rate for a vehicle"""
    # Get vehicle details
    vehicle = vehicle_service.get_variant(request.variant_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # Calculate mileage rate
    response = mileage_engine.calculate(vehicle, request)
    return response
