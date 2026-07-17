# backend/app/api/v1/valuation.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.request import ValuationRequest
from app.schemas.response import ValuationResponse
from app.services.vehicle_service import VehicleService
from app.engines.valuation_engine import ValuationEngine
from app.core.security import get_current_user

router = APIRouter()
vehicle_service = VehicleService()
valuation_engine = ValuationEngine()

@router.post("/calculate")
async def calculate_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user)
) -> ValuationResponse:
    """Calculate vehicle valuation"""
    # Get vehicle details
    vehicle = vehicle_service.get_variant(request.variant_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # Calculate valuation
    response = valuation_engine.calculate(vehicle, request)
    return response
