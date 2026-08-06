# app/modules/valuation/router.py
# Auto-D Kenya - Valuation Routes
# ================================================================
# TYPE: MODULE - Valuation API routes

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional

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

router = APIRouter()
valuation_service = ValuationService()


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
            year=request.year,  # FIXED: was request.vehicle_year
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            location=request.location,
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
            year=request.year,  # FIXED: was request.vehicle_year
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            location=request.location,
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
            year=request.year,  # FIXED: was request.vehicle_year
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            location=request.location,
            user_id=user_id
        )
        
        # Convert to legacy format if needed
        # This returns the full report but the response model will validate
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Valuation failed: {str(e)}"
        )


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


@router.get("/health", response_model=ValuationHealthResponse)
async def valuation_health():
    """
    Health check for valuation service.
    """
    return {
        "status": "healthy",
        "service": "valuation",
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/bulk")
async def bulk_valuation(
    requests: list[ValuationRequest],
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
                    year=request.year,  # FIXED: was request.vehicle_year
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
    requests: list[ValuationRequest],
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
                    year=request.year,  # FIXED: was request.vehicle_year
                    mileage=request.mileage,
                    condition=request.condition,
                    accident_history=request.accident_history,
                    location=request.location,
                    user_id=user_id
                )
                
                # Extract key comparison data
                results.append({
                    "variant_id": request.variant_id,
                    "make": result["vehicle"]["make"],
                    "model": result["vehicle"]["model"],
                    "year": request.year,
                    "estimated_value": result["valuation"]["estimated_vehicle_value"],
                    "confidence_score": result["valuation"]["confidence_score"]
                })
            except Exception as e:
                results.append({
                    "variant_id": request.variant_id,
                    "error": str(e),
                    "success": False
                })
        
        return {
            "comparison": results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Valuation comparison failed: {str(e)}"
        )
