# backend/app/api/v1/valuation.py

"""
Valuation Routes
GET /api/v1/ping - Valuation Ping
POST /api/v1/calculate - Calculate Valuation
GET /api/v1/variant/{variant_id} - Get Variant
GET /api/v1/compare/{variant_id} - Get Market Comparison
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user, get_optional_user
from app.services.valuation_service import get_valuation_service
from app.schemas.request import ValuationRequest
from app.schemas.response import ValuationResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Valuation"])


# ─── Request Models ──────────────────────────────────────────────

class CalculateValuationRequest(BaseModel):
    """Request model for valuation calculation"""
    variant_id: str = Field(..., description="Vehicle variant ID")
    year: int = Field(..., description="Year of manufacture", ge=1980, le=2026)
    mileage: float = Field(..., description="Current mileage in km", ge=0)
    condition: str = Field("good", description="Vehicle condition: excellent, very_good, good, fair, poor")
    accident_history: str = Field("none", description="Accident history: none, minor, major, total_loss")
    previous_owners: int = Field(1, description="Number of previous owners", ge=0)
    location: str = Field("nairobi", description="Vehicle location")
    service_history: bool = Field(True, description="Has service history")
    images: Optional[list] = Field(None, description="Vehicle images")


# ─── Endpoints ──────────────────────────────────────────────────

@router.get("/ping")
async def valuation_ping():
    """
    GET /api/v1/ping - Valuation service ping.
    Returns service status.
    """
    return {
        "status": "ok",
        "service": "valuation",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/calculate", response_model=None)  # ← FIX: Disable response model
async def calculate_valuation(
    request: Request,  # ← This is now properly handled
    valuation_request: CalculateValuationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    POST /api/v1/calculate - Calculate vehicle valuation.
    
    Returns comprehensive valuation including market value, trade value, retail value,
    and confidence score based on vehicle data and market conditions.
    """
    try:
        service = get_valuation_service()
        
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
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Valuation calculation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation calculation failed: {str(e)}"
        )


@router.get("/variant/{variant_id}")
async def get_variant(
    variant_id: str,
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """
    GET /api/v1/variant/{variant_id} - Get variant details.
    
    Returns detailed specifications for a vehicle variant.
    """
    try:
        service = get_valuation_service()
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
        logger.error(f"Error getting variant {variant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch variant details"
        )


@router.get("/compare/{variant_id}")
async def get_market_comparison(
    variant_id: str,
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """
    GET /api/v1/compare/{variant_id} - Get market comparison.
    
    Returns market comparison including average price, price range,
    and comparable vehicles for a variant.
    """
    try:
        service = get_valuation_service()
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
        logger.error(f"Error getting market comparison for {variant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch market comparison"
        )
