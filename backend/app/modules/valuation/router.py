# app/modules/valuation/router.py
# Auto-D Kenya - Valuation Routes
# ================================================================
# TYPE: MODULE - Valuation API routes

import logging
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_user
from app.modules.valuation.schemas import ValuationRequest, ValuationResponse
from app.modules.valuation.service import ValuationService  # FIX 1: Use Service instead of Engine

logger = logging.getLogger(__name__)

router = APIRouter()

# FIX 2: Replace engine instance with service
valuation_service = ValuationService()


@router.post("/valuation/calculate", response_model=ValuationResponse)
async def calculate_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Calculate vehicle valuation.
    
    POST /api/v1/valuation/calculate
    
    Args:
        request: Valuation request with vehicle details
        current_user: Authenticated user
        
    Returns:
        ValuationResponse: Valuation results
    """
    try:
        # FIX 3: Call service layer instead of engine directly
        result = await valuation_service.calculate_valuation(
            variant_id=request.variant_id,
            year=request.year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            location=request.location,
            user_id=current_user.get("id") if current_user else None
        )
        
        # FIX 4: Add response safety with proper mapping
        return ValuationResponse(**result)
        
    except ValueError as e:
        logger.warning(f"Valuation validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Valuation calculation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Valuation calculation failed: {str(e)}")


# ─── ADDITIONAL ENDPOINTS ──────────────────────────────────────────

@router.get("/valuation/history")
async def get_valuation_history(
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's valuation history.
    
    GET /api/v1/valuation/history
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        history = await valuation_service.get_valuation_history(user_id)
        return {
            "status": "success",
            "data": history,
            "count": len(history)
        }
        
    except Exception as e:
        logger.error(f"Error getting valuation history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/valuation/history/{report_id}")
async def get_valuation_report(
    report_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific valuation report by ID.
    
    GET /api/v1/valuation/history/{report_id}
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        report = await valuation_service.get_valuation_by_id(report_id, user_id)
        
        if not report:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
        
        return {
            "status": "success",
            "data": report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting valuation report {report_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/valuation/stats")
async def get_valuation_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's valuation statistics.
    
    GET /api/v1/valuation/stats
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        stats = await valuation_service.get_valuation_stats(user_id)
        return {
            "status": "success",
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting valuation stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── PUBLIC VALUATION (no auth required) ──────────────────────────

@router.post("/valuation/calculate-public", response_model=ValuationResponse)
async def calculate_valuation_public(
    request: ValuationRequest
):
    """
    Calculate vehicle valuation (public endpoint, no authentication required).
    
    POST /api/v1/valuation/calculate-public
    """
    try:
        result = await valuation_service.calculate_valuation(
            variant_id=request.variant_id,
            year=request.year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            location=request.location,
            user_id=None  # No user for public endpoint
        )
        
        return ValuationResponse(**result)
        
    except ValueError as e:
        logger.warning(f"Public valuation validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Public valuation calculation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Valuation calculation failed: {str(e)}")


# ─── HEALTH CHECK ──────────────────────────────────────────────────

@router.get("/valuation/health")
async def valuation_health():
    """
    Health check for valuation service.
    
    GET /api/v1/valuation/health
    """
    return {
        "status": "healthy",
        "service": "valuation",
        "timestamp": datetime.utcnow().isoformat()
    }
