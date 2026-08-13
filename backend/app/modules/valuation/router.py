# app/modules/valuation/router.py
# ================================================================
# AUTO-D Kenya - Vehicle Valuation API
# ================================================================

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.valuation.schemas import (
    ValuationRequest,
    ValuationResponse,
    ValuationReportResponse,
    LegacyValuationRequest,
    ValuationStats,
    ValuationHealthResponse,
    ValuationHistoryResponse,
)
from app.modules.valuation.service import ValuationService
from app.core.dependencies import get_current_user, get_current_user_optional


router = APIRouter(
    prefix="/valuation",
    tags=["Vehicle Valuation"],
)

valuation_service = ValuationService()


# ================================================================
# INTERNAL HELPER
# ================================================================

def _calculate(request: ValuationRequest, user_id=None):
    """
    Single valuation entry point.

    IMPORTANT:
    - No vehicle_variants
    - No vehicle_master_specs
    - No await
    - Uses CRSP directly through ValuationService
    """

    return valuation_service.calculate_valuation(
        make=getattr(request, "make", None),
        model=getattr(request, "model", None),
        manufacture_year=request.manufacture_year,
        mileage=request.mileage_km,
        condition=request.condition_name,
        accident_history=request.accident_status,
        previous_owners=getattr(request, "ownership_count", 0),
        location=request.location_name,
        fuel_type=getattr(request, "fuel_type", None),
        transmission=getattr(request, "transmission", None),
        engine_capacity_id=getattr(request, "engine_capacity_id", None),
        vehicle_crsp_id=request.vehicle_crsp_id,
        vehicle_type=getattr(request, "vehicle_type", None),
        body_type=getattr(request, "body_type", None),
    )


# ================================================================
# CALCULATE
# ================================================================

@router.post(
    "/calculate",
    response_model=ValuationReportResponse,
)
async def calculate_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user_optional),
):
    try:
        user_id = current_user.get("id") if current_user else None

        result = _calculate(request, user_id)

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Valuation failed",
                "error": str(exc),
            },
        )


# ================================================================
# PUBLIC CALCULATE
# ================================================================

@router.post(
    "/calculate-public",
    response_model=ValuationReportResponse,
)
async def calculate_valuation_public(
    request: ValuationRequest,
):
    try:
        result = _calculate(request)

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Valuation failed",
                "error": str(exc),
            },
        )


# ================================================================
# QUICK VALUATION
# ================================================================

@router.post(
    "/quick",
    response_model=ValuationResponse,
)
async def quick_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user_optional),
):
    try:
        result = _calculate(
            request,
            current_user.get("id") if current_user else None,
        )

        valuation = result

        return {
            "vehicle": valuation.get("vehicle", {}),
            "market_value": valuation.get("market_value"),
            "price_range_low": valuation.get("estimated_value_min"),
            "price_range_high": valuation.get("estimated_value_max"),
            "confidence_score": valuation.get("confidence_score", 0),
            "depreciation": valuation.get("depreciation"),
            "adjustments": valuation.get("adjustments", {}),
            "market_comparison": None,
            "recommendation": valuation.get("recommendation"),
            "currency": "KES",
            "calculated_at": valuation.get(
                "calculated_at",
                datetime.utcnow().isoformat(),
            ),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Quick valuation failed",
                "error": str(exc),
            },
        )


# ================================================================
# LEGACY
# ================================================================

@router.post(
    "/calculate-legacy",
    response_model=ValuationResponse,
)
async def calculate_valuation_legacy(
    request: LegacyValuationRequest,
    current_user: dict = Depends(get_current_user_optional),
):
    try:
        converted = request.to_valuation_request()

        result = _calculate(
            converted,
            current_user.get("id") if current_user else None,
        )

        original_value = (
            result.get("crsp_value")
            or result.get("market_value")
            or 0
        )

        current_value = (
            result.get("estimated_value")
            or result.get("market_value")
            or 0
        )

        depreciation_amount = max(
            float(original_value) - float(current_value),
            0,
        )

        depreciation_percentage = (
            depreciation_amount / float(original_value) * 100
            if float(original_value) > 0
            else 0
        )

        return {
            "vehicle": result.get("vehicle", {}),
            "market_value": current_value,
            "price_range_low": result.get("estimated_value_min"),
            "price_range_high": result.get("estimated_value_max"),
            "confidence_score": result.get("confidence_score", 0),
            "depreciation": {
                "original_value": original_value,
                "current_value": current_value,
                "depreciation_amount": depreciation_amount,
                "depreciation_percentage": depreciation_percentage,
                "annual_rate": result.get(
                    "depreciation",
                    {},
                ).get("rate", 0),
            },
            "adjustments": result.get("adjustments", {}),
            "market_comparison": None,
            "recommendation": result.get("recommendation"),
            "currency": "KES",
            "calculated_at": result.get(
                "calculated_at",
                datetime.utcnow().isoformat(),
            ),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Legacy valuation failed",
                "error": str(exc),
            },
        )


# ================================================================
# HEALTH
# ================================================================

@router.get(
    "/health",
    response_model=ValuationHealthResponse,
)
async def valuation_health():
    return {
        "status": "healthy",
        "service": "valuation",
        "version": "3.0",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected",
    }


# ================================================================
# BULK
# ================================================================

@router.post("/bulk")
async def bulk_valuation(
    requests: List[ValuationRequest],
    current_user: dict = Depends(get_current_user_optional),
):
    results = []

    for request in requests:
        try:
            result = _calculate(
                request,
                current_user.get("id") if current_user else None,
            )

            results.append({
                "success": True,
                "vehicle_crsp_id": request.vehicle_crsp_id,
                "data": result,
            })

        except Exception as exc:
            results.append({
                "success": False,
                "vehicle_crsp_id": request.vehicle_crsp_id,
                "error": str(exc),
            })

    return {
        "total": len(results),
        "successful": sum(
            1 for item in results if item["success"]
        ),
        "failed": sum(
            1 for item in results if not item["success"]
        ),
        "results": results,
    }


# ================================================================
# COMPARE
# ================================================================

@router.post("/compare")
async def compare_valuations(
    requests: List[ValuationRequest],
    current_user: dict = Depends(get_current_user_optional),
):
    results = []

    for request in requests:
        try:
            result = _calculate(
                request,
                current_user.get("id") if current_user else None,
            )

            vehicle = result.get("vehicle", {})

            results.append({
                "vehicle_crsp_id": request.vehicle_crsp_id,
                "make": vehicle.get("make"),
                "model": vehicle.get("model"),
                "year": request.manufacture_year,
                "estimated_value": result.get(
                    "estimated_value"
                ),
                "confidence_score": result.get(
                    "confidence_score", 0
                ),
                "success": True,
            })

        except Exception as exc:
            results.append({
                "vehicle_crsp_id": request.vehicle_crsp_id,
                "success": False,
                "error": str(exc),
            })

    return {
        "comparison": results,
        "total": len(results),
        "successful": sum(
            1 for item in results if item["success"]
        ),
        "failed": sum(
            1 for item in results if not item["success"]
        ),
    }


# ================================================================
# HISTORY
# ================================================================

@router.get(
    "/history",
    response_model=ValuationHistoryResponse,
)
async def get_valuation_history(
    current_user: dict = Depends(get_current_user),
):
    try:
        user_id = current_user.get("id")

        history = valuation_service.get_valuation_history(
            user_id
        )

        return {
            "items": history,
            "total": len(history),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/history/{report_id}")
async def get_valuation_report(
    report_id: int,
    current_user: dict = Depends(get_current_user),
):
    try:
        user_id = current_user.get("id")

        report = valuation_service.get_valuation_by_id(
            report_id,
            user_id,
        )

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Valuation report not found",
            )

        return report

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/history/report/{report_number}")
async def get_valuation_by_report_number(
    report_number: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        user_id = current_user.get("id")

        report = valuation_service.get_valuation_by_report_number(
            report_number,
            user_id,
        )

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Valuation report not found",
            )

        return report

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


# ================================================================
# STATS
# ================================================================

@router.get(
    "/stats",
    response_model=ValuationStats,
)
async def get_valuation_stats(
    current_user: dict = Depends(get_current_user),
):
    try:
        return valuation_service.get_valuation_stats(
            current_user.get("id")
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


__all__ = ["router"]
