# app/modules/valuation/router.py
# Auto-D Kenya - Valuation Routes
# ================================================================
# TYPE: MODULE - Valuation API routes

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.modules.valuation.service import ValuationService
from app.modules.valuation.schemas import ValuationRequest, ValuationResponse

router = APIRouter()
valuation_service = ValuationService()


@router.post("/valuation/calculate", response_model=ValuationResponse)
async def calculate_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Calculate vehicle valuation."""
    result = await valuation_service.calculate_valuation(
        variant_id=request.variant_id,
        year=request.year,
        mileage=request.mileage,
        condition=request.condition,
        accident_history=request.accident_history,
        location=request.location,
        user_id=current_user["id"]
    )
    return result


@router.get("/valuation/history")
async def get_valuation_history(current_user: dict = Depends(get_current_user)):
    """Get valuation history for the current user."""
    return await valuation_service.get_valuation_history(current_user["id"])
