# app/modules/valuation/router.py
# Auto-D Kenya - Valuation Routes
# ================================================================
# TYPE: MODULE - Valuation API routes

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user, get_current_user_optional
from app.modules.valuation.schemas import ValuationRequest, ValuationResponse, ValuationReportResponse
from app.modules.valuation.service import ValuationService

logger = logging.getLogger(__name__)

router = APIRouter()
valuation_service = ValuationService()


# ─── MAIN VALUATION ENDPOINT ──────────────────────────────────────

@router.post("/valuation/calculate", response_model=ValuationReportResponse)
async def calculate_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Calculate vehicle valuation.
    
    POST /api/v1/valuation/calculate
    
    Returns a comprehensive valuation report with:
    - Report metadata (title, number, status)
    - Vehicle information
    - Valuation results (estimated value, range, confidence)
    - Analysis methodology and adjustments
    - Professional disclaimer
    
    Requires authentication.
    """
    try:
        result = await valuation_service.calculate_valuation(
            variant_id=request.variant_id,
            year=request.year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            location=request.location,
            user_id=current_user.get("id") if current_user else None
        )
        
        return result
        
    except ValueError as e:
        logger.warning(f"Valuation validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Valuation calculation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation calculation failed: {str(e)}"
        )


# ─── PUBLIC VALUATION (no auth required) ──────────────────────────

@router.post("/valuation/calculate-public", response_model=ValuationReportResponse)
async def calculate_valuation_public(
    request: ValuationRequest
):
    """
    Calculate vehicle valuation (public endpoint).
    
    POST /api/v1/valuation/calculate-public
    
    Same as the authenticated endpoint but without saving history.
    Useful for testing and demo purposes.
    """
    try:
        result = await valuation_service.calculate_valuation(
            variant_id=request.variant_id,
            year=request.year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            location=request.location,
            user_id=None
        )
        
        return result
        
    except ValueError as e:
        logger.warning(f"Public valuation validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Public valuation calculation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation calculation failed: {str(e)}"
        )


# ─── VALUATION HISTORY ─────────────────────────────────────────────

@router.get("/valuation/history")
async def get_valuation_history(
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's valuation history.
    
    GET /api/v1/valuation/history
    
    Returns a list of all valuation reports for the authenticated user.
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found"
            )
        
        history = await valuation_service.get_valuation_history(user_id)
        
        return {
            "status": "success",
            "data": history,
            "count": len(history),
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Error getting valuation history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}"
        )


@router.get("/valuation/history/{report_id}")
async def get_valuation_report(
    report_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific valuation report by ID.
    
    GET /api/v1/valuation/history/{report_id}
    
    Returns a single valuation report with full details.
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found"
            )
        
        report = await valuation_service.get_valuation_by_id(report_id, user_id)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            )
        
        return {
            "status": "success",
            "data": report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting valuation report {report_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve report: {str(e)}"
        )


@router.get("/valuation/stats")
async def get_valuation_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's valuation statistics.
    
    GET /api/v1/valuation/stats
    
    Returns aggregate statistics about the user's valuations.
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found"
            )
        
        stats = await valuation_service.get_valuation_stats(user_id)
        
        return {
            "status": "success",
            "data": stats,
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Error getting valuation stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve stats: {str(e)}"
        )


# ─── HEALTH CHECK ──────────────────────────────────────────────────

@router.get("/valuation/health")
async def valuation_health():
    """
    Health check for valuation service.
    
    GET /api/v1/valuation/health
    
    Returns service status and version information.
    """
    return {
        "status": "healthy",
        "service": "valuation",
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": [
            "/valuation/calculate",
            "/valuation/calculate-public",
            "/valuation/history",
            "/valuation/history/{report_id}",
            "/valuation/stats",
            "/valuation/health"
        ]
    }


# ─── LEGACY COMPATIBILITY ENDPOINT ────────────────────────────────

@router.post("/valuation/calculate-legacy", response_model=ValuationResponse)
async def calculate_valuation_legacy(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Legacy valuation endpoint for backward compatibility.
    
    POST /api/v1/valuation/calculate-legacy
    
    Returns the old flat response structure.
    This endpoint is deprecated and will be removed in a future version.
    """
    logger.warning("Legacy valuation endpoint used by user: {}", current_user.get("id", "anonymous"))
    
    try:
        result = await valuation_service.calculate_valuation(
            variant_id=request.variant_id,
            year=request.year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            location=request.location,
            user_id=current_user.get("id") if current_user else None
        )
        
        # Convert new structure to legacy flat structure
        legacy_result = {
            "report_number": result["report"]["report_number"],
            "generated_at": result["report"]["generated_at"],
            "estimated_vehicle_value": result["valuation"]["estimated_vehicle_value"],
            "retail_value": result["valuation"]["retail_value"],
            "trade_value": result["valuation"]["trade_value"],
            "dealer_value": result["valuation"]["dealer_value"],
            "currency": result["valuation"]["currency"],
            "confidence_score": result["valuation"]["confidence_score"],
            "estimated_value_range": result["valuation"]["estimated_value_range"],
            "vehicle": result["vehicle"],
            "analysis": result["analysis"],
            "disclaimer": result["disclaimer"]
        }
        
        return legacy_result
        
    except ValueError as e:
        logger.warning(f"Legacy valuation validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Legacy valuation calculation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation calculation failed: {str(e)}"
        )


# ─── BULK VALUATION ENDPOINT ──────────────────────────────────────

@router.post("/valuation/bulk")
async def calculate_bulk_valuation(
    requests: list[ValuationRequest],
    current_user: dict = Depends(get_current_user)
):
    """
    Calculate valuations for multiple vehicles in bulk.
    
    POST /api/v1/valuation/bulk
    
    Returns a list of valuation reports.
    Useful for fleet valuation or comparing multiple vehicles.
    """
    try:
        user_id = current_user.get("id")
        results = []
        
        for request in requests:
            try:
                result = await valuation_service.calculate_valuation(
                    variant_id=request.variant_id,
                    year=request.year,
                    mileage=request.mileage,
                    condition=request.condition,
                    accident_history=request.accident_history,
                    location=request.location,
                    user_id=user_id
                )
                results.append({
                    "success": True,
                    "data": result
                })
            except Exception as e:
                results.append({
                    "success": False,
                    "error": str(e),
                    "variant_id": request.variant_id
                })
        
        return {
            "status": "success",
            "total": len(requests),
            "successful": len([r for r in results if r["success"]]),
            "failed": len([r for r in results if not r["success"]]),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Bulk valuation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk valuation failed: {str(e)}"
        )


# ─── VALUATION COMPARISON ──────────────────────────────────────────

@router.post("/valuation/compare")
async def compare_valuations(
    variant_ids: list[int],
    current_user: dict = Depends(get_current_user)
):
    """
    Compare valuations for multiple variants.
    
    POST /api/v1/valuation/compare
    
    Returns a comparison of valuations for different vehicle variants.
    """
    try:
        user_id = current_user.get("id")
        results = []
        
        # Get default parameters from the first request or use defaults
        # In a real implementation, you'd pass these in the request body
        
        for variant_id in variant_ids:
            try:
                # Get variant data first to get year/mileage or use defaults
                # For now, use default values
                result = await valuation_service.calculate_valuation(
                    variant_id=variant_id,
                    year=2020,
                    mileage=50000,
                    condition="good",
                    accident_history="none",
                    location="nairobi",
                    user_id=user_id
                )
                results.append({
                    "variant_id": variant_id,
                    "vehicle": f"{result['vehicle']['make']} {result['vehicle']['model']}",
                    "estimated_value": result["valuation"]["estimated_vehicle_value"],
                    "confidence": result["valuation"]["confidence_score"]
                })
            except Exception as e:
                results.append({
                    "variant_id": variant_id,
                    "error": str(e)
                })
        
        return {
            "status": "success",
            "comparison": results
        }
        
    except Exception as e:
        logger.error(f"Valuation comparison error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comparison failed: {str(e)}"
        )
