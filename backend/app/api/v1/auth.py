# backend/app/api/v1/valuation.py

from fastapi import APIRouter, HTTPException, Depends, Request, status
from typing import Optional, Dict
from datetime import datetime, timezone

from app.core.dependencies import get_current_user
from app.services.valuation_service import ValuationService
from app.schemas.request import ValuationRequest
from app.schemas.response import ValuationResponse

router = APIRouter(tags=["Valuation"])


# ─── Request Models ──────────────────────────────────────────────

class CalculateValuationRequest(BaseModel):
    """Request model for valuation calculation"""
    variant_id: str
    year: int
    mileage: float
    condition: str = "good"
    accident_history: str = "none"
    previous_owners: int = 1
    location: str = "nairobi"
    service_history: bool = True
    images: Optional[list] = None


# ─── Endpoints ──────────────────────────────────────────────────

@router.get("/ping")
async def valuation_ping():
    """GET /api/v1/ping - Valuation service ping"""
    return {
        "status": "ok",
        "service": "valuation",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/calculate", response_model=None)  # ← FIX: Add response_model=None
async def calculate_valuation(
    request: Request,  # ← Request is allowed now
    valuation_request: CalculateValuationRequest,
    current_user: dict = Depends(get_current_user)
):
    """POST /api/v1/calculate - Calculate vehicle valuation"""
    try:
        service = ValuationService()
        
        # Convert to service request format
        service_request = ValuationRequest(
            variant_id=valuation_request.variant_id,
            year=valuation_request.year,
            mileage=valuation_request.mileage,
            condition=valuation_request.condition,
            accident_history=valuation_request.accident_history,
            previous_owners=valuation_request.previous_owners,
            location=valuation_request.location,
            service_history=valuation_request.service_history,
            images=valuation_request.images,
            user_id=current_user.get("id")
        )
        
        result = service.calculate_valuation(service_request)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Valuation calculation failed"
            )
        
        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation calculation failed: {str(e)}"
        )


@router.get("/variant/{variant_id}")
async def get_variant(
    variant_id: str,
    current_user: dict = Depends(get_current_user)
):
    """GET /api/v1/variant/{variant_id} - Get variant details"""
    try:
        service = ValuationService()
        variant = service.get_variant(variant_id)
        
        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Variant with ID {variant_id} not found"
            )
        
        return variant
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch variant: {str(e)}"
        )


@router.get("/compare/{variant_id}")
async def get_market_comparison(
    variant_id: str,
    current_user: dict = Depends(get_current_user)
):
    """GET /api/v1/compare/{variant_id} - Get market comparison"""
    try:
        service = ValuationService()
        comparison = service.get_market_comparison(variant_id)
        
        if not comparison:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Market data for variant {variant_id} not found"
            )
        
        return comparison
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch market comparison: {str(e)}"
        )
