# app/modules/valuation/router.py
# ================================================================
# Auto-D Kenya - Valuation Routes
# ================================================================

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List

from app.modules.valuation.schemas import (
    ValuationRequest,
    ValuationResponse,
    ValuationReportResponse,
    ValuationStats,
    ValuationHealthResponse,
    ValuationHistoryResponse,
    LegacyValuationRequest,
    ReportMetadata,
)
from app.modules.valuation.service import ValuationService
from app.core.dependencies import get_current_user, get_current_user_optional

# ─── ROUTER ──────────────────────────────────────────────────────────

router = APIRouter(
    prefix="/valuation",
    tags=["Vehicle Valuation"],
)

service = ValuationService()


# ================================================================
# VALUATION ENDPOINTS
# ================================================================

@router.post("/calculate", response_model=ValuationResponse)
async def calculate_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Calculate vehicle valuation.
    
    Accepts the frontend payload with make, model, year, mileage, etc.
    Returns comprehensive valuation results.
    """
    try:
        user_id = current_user.get("id") if current_user else None
        
        result = service.calculate_valuation(
            make=request.make,
            model=request.model,
            year=request.year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            previous_owners=request.previous_owners,
            location=request.location,
            fuel_type=request.fuel_type,
            transmission=request.transmission,
            vehicle_type=request.vehicle_type,
            trim=request.trim,
            engine_capacity=request.engine_capacity,
            profit_margin=request.profit_margin,
        )
        
        # Save to history if user is authenticated
        if user_id:
            request_data = request.model_dump()
            await service.save_valuation_history(user_id, result, request_data)
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Valuation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation failed: {str(e)}"
        )


@router.post("/calculate-public", response_model=ValuationResponse)
async def calculate_valuation_public(
    request: ValuationRequest
):
    """
    Calculate vehicle valuation (public endpoint - no authentication required).
    """
    try:
        result = service.calculate_valuation(
            make=request.make,
            model=request.model,
            year=request.year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            previous_owners=request.previous_owners,
            location=request.location,
            fuel_type=request.fuel_type,
            transmission=request.transmission,
            vehicle_type=request.vehicle_type,
            trim=request.trim,
            engine_capacity=request.engine_capacity,
            profit_margin=request.profit_margin,
        )
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation failed: {str(e)}"
        )


@router.post("/calculate-legacy", response_model=ValuationResponse)
async def calculate_valuation_legacy(
    request: LegacyValuationRequest,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Calculate vehicle valuation (legacy format - backward compatibility).
    """
    try:
        user_id = current_user.get("id") if current_user else None
        
        # Convert legacy request to new format
        result = service.calculate_valuation(
            make="",  # Legacy doesn't have make/model
            model="",
            year=request.year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            previous_owners=request.ownership_count,
            location=request.location,
            fuel_type=request.fuel_type,
            transmission=request.transmission,
            profit_margin=request.profit_margin_percent,
        )
        
        if user_id:
            await service.save_valuation_history(user_id, result, {"year": request.year})
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation failed: {str(e)}"
        )


# ================================================================
# CRSP LOOKUP ENDPOINTS
# ================================================================

@router.get("/crsp/makes")
async def get_makes(
    current_user: dict = Depends(get_current_user_optional)
):
    """Get all makes from CRSP."""
    return service.get_makes()


@router.get("/crsp/models")
async def get_models(
    make: str,
    current_user: dict = Depends(get_current_user_optional)
):
    """Get models for a make."""
    return service.get_models(make)


@router.get("/crsp/years")
async def get_years(
    make: str,
    model: str,
    current_user: dict = Depends(get_current_user_optional)
):
    """Get years for a model."""
    return service.get_years(make, model)


@router.get("/crsp/trims")
async def get_trims(
    make: str,
    model: str,
    year: int,
    current_user: dict = Depends(get_current_user_optional)
):
    """Get trims for a model and year."""
    return service.get_trims(make, model, year)


@router.get("/crsp/search")
async def search_crsp(
    make: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = 25,
    current_user: dict = Depends(get_current_user_optional)
):
    """Search CRSP records."""
    return service.search_crsp(make, model, year, limit)


@router.get("/crsp/{crsp_id}")
async def get_crsp_vehicle(
    crsp_id: int,
    current_user: dict = Depends(get_current_user_optional)
):
    """Get CRSP vehicle by ID."""
    result = service.get_crsp_vehicle(crsp_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CRSP vehicle {crsp_id} not found"
        )
    return result


# ================================================================
# HISTORY ENDPOINTS
# ================================================================

@router.get("/history", response_model=ValuationHistoryResponse)
async def get_valuation_history(
    current_user: dict = Depends(get_current_user)
):
    """Get valuation history for the current user."""
    try:
        user_id = current_user.get("id")
        history = await service.get_valuation_history(user_id)
        return {"items": history, "total": len(history)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get history: {str(e)}"
        )


@router.get("/history/{report_id}")
async def get_valuation_report(
    report_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific valuation report by ID."""
    try:
        user_id = current_user.get("id")
        report = await service.get_valuation_by_id(report_id, user_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Valuation report not found"
            )
        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get report: {str(e)}"
        )


# ================================================================
# STATISTICS ENDPOINTS
# ================================================================

@router.get("/stats", response_model=ValuationStats)
async def get_valuation_stats(
    current_user: dict = Depends(get_current_user)
):
    """Get valuation statistics for the current user."""
    try:
        user_id = current_user.get("id")
        return await service.get_valuation_stats(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


# ================================================================
# HEALTH ENDPOINT
# ================================================================

@router.get("/health", response_model=ValuationHealthResponse)
async def valuation_health():
    """Health check for valuation service."""
    return service.health_check()


# ================================================================
# BULK ENDPOINTS
# ================================================================

@router.post("/bulk")
async def bulk_valuation(
    requests: List[ValuationRequest],
    current_user: dict = Depends(get_current_user_optional)
):
    """Calculate valuations for multiple vehicles."""
    try:
        user_id = current_user.get("id") if current_user else None
        request_data = [req.model_dump() for req in requests]
        results = service.calculate_bulk_valuations(request_data)
        
        if user_id:
            for i, result in enumerate(results):
                if result.get("success"):
                    await service.save_valuation_history(user_id, result["result"], request_data[i])
        
        return {
            "total": len(requests),
            "successful": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if not r.get("success")),
            "results": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk valuation failed: {str(e)}"
        )


# ================================================================
# EXPORTS
# ================================================================

__all__ = ["router"]
