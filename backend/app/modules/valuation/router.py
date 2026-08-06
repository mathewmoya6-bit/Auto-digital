# app/modules/valuation/router.py
# Auto-D Kenya - Valuation Routes
# ================================================================
# TYPE: MODULE - Valuation API routes

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List

from app.modules.valuation.schemas import (
    ValuationRequest,
    ValuationResponse,
    ValuationReportResponse,
    ValuationStats,
    ValuationHealthResponse,
    ValuationHistoryResponse
)
from app.modules.valuation.service import ValuationService
from app.core.dependencies import get_current_user, get_current_user_optional

# ─── ROUTER WITH PREFIX ──────────────────────────────────────────────

router = APIRouter(
    prefix="/valuation",
    tags=["Vehicle Valuation"],
)

valuation_service = ValuationService()


# ================================================================
# VALUATION ENDPOINTS
# ================================================================

@router.post("/calculate", response_model=ValuationReportResponse)
async def calculate_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Calculate vehicle valuation.
    
    Returns a comprehensive valuation report with:
    - Estimated market value
    - Retail, trade, and dealer values
    - Confidence score
    - Value range
    - Analysis and methodology
    """
    try:
        user_id = current_user.get("id") if current_user else None
        
        result = await valuation_service.calculate_valuation(
            variant_id=request.variant_id,
            year=request.year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            location=request.location,
            fuel_type=request.fuel_type,
            transmission=request.transmission,
            ownership_count=request.ownership_count,
            service_history=request.service_history,
            user_id=user_id
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Valuation failed: {str(e)}"
        )


@router.post("/calculate-public", response_model=ValuationReportResponse)
async def calculate_valuation_public(
    request: ValuationRequest
):
    """
    Calculate vehicle valuation (public endpoint - no authentication required).
    
    Returns a comprehensive valuation report with:
    - Estimated market value
    - Retail, trade, and dealer values
    - Confidence score
    - Value range
    - Analysis and methodology
    """
    try:
        result = await valuation_service.calculate_valuation(
            variant_id=request.variant_id,
            year=request.year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            location=request.location,
            fuel_type=request.fuel_type,
            transmission=request.transmission,
            ownership_count=request.ownership_count,
            service_history=request.service_history,
            user_id=None
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Valuation failed: {str(e)}"
        )


@router.post("/calculate-legacy", response_model=ValuationResponse)
async def calculate_valuation_legacy(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Calculate vehicle valuation (legacy response format).
    
    Returns a simplified valuation response without the full report structure.
    """
    try:
        user_id = current_user.get("id") if current_user else None
        
        result = await valuation_service.calculate_valuation(
            variant_id=request.variant_id,
            year=request.year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            location=request.location,
            fuel_type=request.fuel_type,
            transmission=request.transmission,
            ownership_count=request.ownership_count,
            service_history=request.service_history,
            user_id=user_id
        )
        
        # ─── CONVERT TO LEGACY FORMAT ──────────────────────────────────
        
        return {
            "vehicle": result["vehicle"],
            "market_value": result["valuation"]["estimated_vehicle_value"],
            "price_range_low": result["valuation"]["estimated_value_range"]["minimum"],
            "price_range_high": result["valuation"]["estimated_value_range"]["maximum"],
            "confidence_score": result["valuation"]["confidence_score"],
            "depreciation": {
                "original_value": result["valuation"]["retail_value"],
                "current_value": result["valuation"]["estimated_vehicle_value"],
                "depreciation_amount": (
                    result["valuation"]["retail_value"] 
                    - result["valuation"]["estimated_vehicle_value"]
                ),
                "depreciation_percentage": (
                    (result["valuation"]["retail_value"] - result["valuation"]["estimated_vehicle_value"]) 
                    / result["valuation"]["retail_value"] 
                    * 100
                ) if result["valuation"]["retail_value"] > 0 else 0,
                "annual_rate": 0.15,
            },
            "adjustments": result.get("analysis", {}).get("adjustments", []),
            "market_comparison": None,
            "recommendation": None,
            "currency": "KES",
            "calculated_at": result["report"]["generated_at"],
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Valuation failed: {str(e)}"
        )


# ================================================================
# HISTORY ENDPOINTS
# ================================================================

@router.get("/history", response_model=ValuationHistoryResponse)
async def get_valuation_history(
    current_user: dict = Depends(get_current_user)
):
    """
    Get valuation history for the current user.
    """
    try:
        user_id = current_user.get("id")
        history = await valuation_service.get_valuation_history(user_id)
        
        return {
            "items": history,
            "total": len(history)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get valuation history: {str(e)}"
        )


@router.get("/history/{report_id}")
async def get_valuation_report(
    report_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific valuation report by ID.
    """
    try:
        user_id = current_user.get("id")
        report = await valuation_service.get_valuation_by_id(report_id, user_id)
        
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get valuation report: {str(e)}"
        )


@router.get("/history/report/{report_number}")
async def get_valuation_by_report_number(
    report_number: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a valuation report by report number.
    """
    try:
        user_id = current_user.get("id")
        report = await valuation_service.get_valuation_by_report_number(report_number, user_id)
        
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get valuation report: {str(e)}"
        )


# ================================================================
# STATISTICS ENDPOINTS
# ================================================================

@router.get("/stats", response_model=ValuationStats)
async def get_valuation_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get valuation statistics for the current user.
    """
    try:
        user_id = current_user.get("id")
        stats = await valuation_service.get_valuation_stats(user_id)
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get valuation stats: {str(e)}"
        )


# ================================================================
# HEALTH ENDPOINT
# ================================================================

@router.get("/health", response_model=ValuationHealthResponse)
async def valuation_health():
    """
    Health check for valuation service.
    """
    try:
        health = await valuation_service.health_check()
        return health
    except Exception as e:
        return {
            "status": "degraded",
            "service": "valuation",
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


# ================================================================
# BULK ENDPOINTS
# ================================================================

@router.post("/bulk")
async def bulk_valuation(
    requests: List[ValuationRequest],
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Calculate valuations for multiple vehicles in bulk.
    """
    try:
        user_id = current_user.get("id") if current_user else None
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
                    fuel_type=request.fuel_type,
                    transmission=request.transmission,
                    ownership_count=request.ownership_count,
                    service_history=request.service_history,
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
            "total": len(requests),
            "successful": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bulk valuation failed: {str(e)}"
        )


@router.post("/compare")
async def compare_valuations(
    requests: List[ValuationRequest],
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Compare valuations for multiple vehicles.
    """
    try:
        user_id = current_user.get("id") if current_user else None
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
                    fuel_type=request.fuel_type,
                    transmission=request.transmission,
                    ownership_count=request.ownership_count,
                    service_history=request.service_history,
                    user_id=user_id
                )
                
                # Extract key comparison data
                results.append({
                    "variant_id": request.variant_id,
                    "make": result["vehicle"].get("make"),
                    "model": result["vehicle"].get("model"),
                    "year": request.year,
                    "estimated_value": result["valuation"]["estimated_vehicle_value"],
                    "confidence_score": result["valuation"]["confidence_score"],
                    "success": True
                })
            except Exception as e:
                results.append({
                    "variant_id": request.variant_id,
                    "error": str(e),
                    "success": False
                })
        
        return {
            "comparison": results,
            "total": len(results),
            "successful": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"])
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Valuation comparison failed: {str(e)}"
        )


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    "router",
]
