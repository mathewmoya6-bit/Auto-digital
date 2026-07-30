# app/modules/valuation/router.py
# Auto-D Kenya - Valuation Routes
# ================================================================
# TYPE: MODULE - Valuation API routes

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.modules.valuation.engine import ValuationEngine
from app.modules.valuation.schemas import ValuationRequest, ValuationResponse

router = APIRouter()
valuation_engine = ValuationEngine()


@router.post("/valuation/calculate", response_model=ValuationResponse)
async def calculate_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Calculate vehicle valuation."""
    result = await valuation_engine.calculate(
        variant_id=request.variant_id,
        year=request.year,
        mileage=request.mileage,
        condition=request.condition,
        accident_history=request.accident_history,
        location=request.location
    )
    return result
