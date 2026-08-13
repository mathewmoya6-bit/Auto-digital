# app/modules/valuation/router.py
# ================================================================
# AUTO-D KENYA - VALUATION ROUTER
# ================================================================
#
# CRSP is the authoritative vehicle valuation source.
#
# IMPORTANT:
# - No vehicle_variants
# - No variant_id
# - No vehicle_master_specs lookup
# - CRSP ID is preferred
# - ValuationService is synchronous
# - Database/repository performs the valuation calculation
#
# ================================================================

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import (
    get_current_user,
    get_current_user_optional,
)

from app.modules.valuation.schemas import (
    ValuationRequest,
    ValuationResponse,
    ValuationReportResponse,
    ValuationStats,
    ValuationHealthResponse,
    ValuationHistoryResponse,
    LegacyValuationRequest,
)

from app.modules.valuation.service import ValuationService


logger = logging.getLogger(__name__)


# ================================================================
# ROUTER
# ================================================================

router = APIRouter(
    prefix="/valuation",
    tags=["Vehicle Valuation"],
)


valuation_service = ValuationService()


# ================================================================
# MAIN VALUATION
# ================================================================

@router.post(
    "/calculate",
    response_model=ValuationReportResponse,
)
async def calculate_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user_optional),
):
    """
    Calculate vehicle valuation.

    CRSP-first valuation.

    The request's vehicle_crsp_id is passed directly to the
    valuation service. No variant or vehicle_master_specs lookup
    is performed.
    """

    try:

        user_id = (
            current_user.get("id")
            if current_user
            else None
        )

        logger.info(
            "Valuation request: crsp_id=%s year=%s mileage=%s",
            request.vehicle_crsp_id,
            request.manufacture_year,
            request.mileage_km,
        )

        result = valuation_service.calculate_valuation(
            vehicle_crsp_id=request.vehicle_crsp_id,
            manufacture_year=request.manufacture_year,
            mileage_km=request.mileage_km,
            condition_name=request.condition_name,
            accident_status=request.accident_status,
            location_name=request.location_name,
            profit_margin_percent=request.profit_margin_percent,
            fuel_type=getattr(
                request,
                "fuel_type",
                None,
            ),
            transmission=getattr(
                request,
                "transmission",
                None,
            ),
            body_type=getattr(
                request,
                "body_type",
                None,
            ),
        )

        # Attach user ID only if the response is a dictionary.
        # The valuation calculation itself does not depend on user ID.
        if isinstance(result, dict):
            result.setdefault(
                "user_id",
                user_id,
            )

        return result

    except ValueError as exc:

        logger.warning(
            "Valuation validation error: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:

        logger.exception(
            "Valuation calculation failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation calculation failed: {str(exc)}",
        )


# ================================================================
# PUBLIC VALUATION
# ================================================================

@router.post(
    "/calculate-public",
    response_model=ValuationReportResponse,
)
async def calculate_valuation_public(
    request: ValuationRequest,
):
    """
    Public vehicle valuation.

    Same CRSP valuation engine as the authenticated endpoint.
    """

    try:

        logger.info(
            "Public valuation request: crsp_id=%s year=%s mileage=%s",
            request.vehicle_crsp_id,
            request.manufacture_year,
            request.mileage_km,
        )

        result = valuation_service.calculate_valuation(
            vehicle_crsp_id=request.vehicle_crsp_id,
            manufacture_year=request.manufacture_year,
            mileage_km=request.mileage_km,
            condition_name=request.condition_name,
            accident_status=request.accident_status,
            location_name=request.location_name,
            profit_margin_percent=request.profit_margin_percent,
            fuel_type=getattr(
                request,
                "fuel_type",
                None,
            ),
            transmission=getattr(
                request,
                "transmission",
                None,
            ),
            body_type=getattr(
                request,
                "body_type",
                None,
            ),
        )

        return result

    except ValueError as exc:

        logger.warning(
            "Public valuation validation error: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:

        logger.exception(
            "Public valuation calculation failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation calculation failed: {str(exc)}",
        )


# ================================================================
# LEGACY VALUATION
# ================================================================

@router.post(
    "/calculate-legacy",
    response_model=ValuationResponse,
)
async def calculate_valuation_legacy(
    request: LegacyValuationRequest,
    current_user: dict = Depends(get_current_user_optional),
):
    """
    Legacy valuation endpoint.

    Converts the legacy request to the current ValuationRequest,
    then uses the same CRSP valuation engine.
    """

    try:

        converted_request = request.to_valuation_request()

        result = valuation_service.calculate_valuation(
            vehicle_crsp_id=converted_request.vehicle_crsp_id,
            manufacture_year=converted_request.manufacture_year,
            mileage_km=converted_request.mileage_km,
            condition_name=converted_request.condition_name,
            accident_status=converted_request.accident_status,
            location_name=converted_request.location_name,
            profit_margin_percent=(
                converted_request.profit_margin_percent
            ),
            fuel_type=getattr(
                request,
                "fuel_type",
                None,
            ),
            transmission=getattr(
                request,
                "transmission",
                None,
            ),
            body_type=getattr(
                request,
                "body_type",
                None,
            ),
        )

        if not isinstance(result, dict):
            return result

        # ------------------------------------------------------------
        # If valuation failed, return a clean response.
        # ------------------------------------------------------------

        if not result.get("success", False):

            return {
                "vehicle": result.get(
                    "vehicle",
                    {},
                ),
                "market_value": None,
                "price_range_low": None,
                "price_range_high": None,
                "confidence_score": 0,
                "depreciation": {
                    "original_value": (
                        result.get("crsp_value")
                    ),
                    "current_value": None,
                    "depreciation_amount": None,
                    "depreciation_percentage": None,
                    "annual_rate": 0,
                },
                "adjustments": [],
                "market_comparison": None,
                "recommendation": result.get(
                    "message"
                ),
                "currency": "KES",
                "calculated_at": result.get(
                    "calculated_at",
                    datetime.now().isoformat(),
                ),
            }

        # ------------------------------------------------------------
        # Current valuation result
        # ------------------------------------------------------------

        valuation = result.get(
            "valuation",
            {},
        )

        if not isinstance(valuation, dict):
            valuation = {}

        estimated_value = (
            valuation.get(
                "estimated_vehicle_value"
            )
            or valuation.get(
                "estimated_value"
            )
            or result.get(
                "estimated_value"
            )
            or result.get(
                "market_value"
            )
        )

        value_range = valuation.get(
            "estimated_value_range",
            {},
        )

        if not isinstance(value_range, dict):
            value_range = {}

        return {
            "vehicle": result.get(
                "vehicle",
                {},
            ),
            "market_value": estimated_value,
            "price_range_low": (
                value_range.get(
                    "minimum"
                )
                or result.get(
                    "estimated_value_min"
                )
            ),
            "price_range_high": (
                value_range.get(
                    "maximum"
                )
                or result.get(
                    "estimated_value_max"
                )
            ),
            "confidence_score": (
                valuation.get(
                    "confidence_score"
                )
                or result.get(
                    "confidence_score",
                    0,
                )
            ),
            "depreciation": {
                "original_value": (
                    valuation.get(
                        "crsp_value"
                    )
                    or result.get(
                        "crsp_value"
                    )
                ),
                "current_value": estimated_value,
                "depreciation_amount": None,
                "depreciation_percentage": None,
                "annual_rate": valuation.get(
                    "depreciation_rate",
                    0,
                ),
            },
            "adjustments": [],
            "market_comparison": None,
            "recommendation": result.get(
                "message"
            ),
            "currency": "KES",
            "calculated_at": result.get(
                "calculated_at",
                datetime.now().isoformat(),
            ),
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:

        logger.exception(
            "Legacy valuation failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation calculation failed: {str(exc)}",
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
    """
    Quick CRSP valuation.

    Uses exactly the same valuation engine as /calculate.
    """

    try:

        result = valuation_service.calculate_valuation(
            vehicle_crsp_id=request.vehicle_crsp_id,
            manufacture_year=request.manufacture_year,
            mileage_km=request.mileage_km,
            condition_name=request.condition_name,
            accident_status=request.accident_status,
            location_name=request.location_name,
            profit_margin_percent=request.profit_margin_percent,
            fuel_type=getattr(
                request,
                "fuel_type",
                None,
            ),
            transmission=getattr(
                request,
                "transmission",
                None,
            ),
            body_type=getattr(
                request,
                "body_type",
                None,
            ),
        )

        if not result.get("success", False):

            return {
                "vehicle": result.get(
                    "vehicle",
                    {},
                ),
                "market_value": None,
                "price_range_low": None,
                "price_range_high": None,
                "confidence_score": 0,
                "depreciation": {
                    "original_value": result.get(
                        "crsp_value"
                    ),
                    "current_value": None,
                    "depreciation_amount": None,
                    "depreciation_percentage": None,
                    "annual_rate": 0,
                },
                "adjustments": [],
                "market_comparison": None,
                "recommendation": result.get(
                    "message"
                ),
                "currency": "KES",
                "calculated_at": result.get(
                    "calculated_at",
                    datetime.now().isoformat(),
                ),
            }

        valuation = result.get(
            "valuation",
            {},
        )

        if not isinstance(valuation, dict):
            valuation = {}

        estimated_value = (
            valuation.get(
                "estimated_vehicle_value"
            )
            or valuation.get(
                "estimated_value"
            )
            or result.get(
                "estimated_value"
            )
            or result.get(
                "market_value"
            )
        )

        value_range = valuation.get(
            "estimated_value_range",
            {},
        )

        if not isinstance(value_range, dict):
            value_range = {}

        return {
            "vehicle": result.get(
                "vehicle",
                {},
            ),
            "market_value": estimated_value,
            "price_range_low": (
                value_range.get(
                    "minimum"
                )
                or result.get(
                    "estimated_value_min"
                )
            ),
            "price_range_high": (
                value_range.get(
                    "maximum"
                )
                or result.get(
                    "estimated_value_max"
                )
            ),
            "confidence_score": (
                valuation.get(
                    "confidence_score"
                )
                or result.get(
                    "confidence_score",
                    0,
                )
            ),
            "depreciation": {
                "original_value": (
                    valuation.get(
                        "crsp_value"
                    )
                    or result.get(
                        "crsp_value"
                    )
                ),
                "current_value": estimated_value,
                "depreciation_amount": None,
                "depreciation_percentage": None,
                "annual_rate": valuation.get(
                    "depreciation_rate",
                    0,
                ),
            },
            "adjustments": [],
            "market_comparison": None,
            "recommendation": result.get(
                "message"
            ),
            "currency": "KES",
            "calculated_at": result.get(
                "calculated_at",
                datetime.now().isoformat(),
            ),
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:

        logger.exception(
            "Quick valuation failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation calculation failed: {str(exc)}",
        )


# ================================================================
# CRSP SEARCH
# ================================================================

@router.get("/search")
async def search_crsp(
    make: str,
    model: str,
    manufacture_year: int | None = None,
    limit: int = 25,
):
    """
    Search CRSP records by make/model.

    This is a direct CRSP lookup and does not use variants.
    """

    try:

        records = valuation_service.search_crsp(
            make=make,
            model=model,
            manufacture_year=manufacture_year,
            limit=limit,
        )

        return {
            "success": True,
            "count": len(records),
            "results": records,
        }

    except Exception as exc:

        logger.exception(
            "CRSP search failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CRSP search failed: {str(exc)}",
        )


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
    """
    Get valuation history.
    """

    try:

        user_id = current_user.get("id")

        method = getattr(
            valuation_service,
            "get_valuation_history",
            None,
        )

        if not callable(method):
            return {
                "items": [],
                "total": 0,
            }

        history = method(user_id)

        return {
            "items": history or [],
            "total": len(history or []),
        }

    except Exception as exc:

        logger.exception(
            "Failed to get valuation history: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get valuation history: {str(exc)}",
        )


# ================================================================
# HISTORY BY ID
# ================================================================

@router.get(
    "/history/{report_id}",
)
async def get_valuation_report(
    report_id: int,
    current_user: dict = Depends(get_current_user),
):
    """
    Get valuation report by ID.
    """

    try:

        user_id = current_user.get("id")

        method = getattr(
            valuation_service,
            "get_valuation_by_id",
            None,
        )

        if not callable(method):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Valuation report not found",
            )

        report = method(
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

        logger.exception(
            "Failed to get valuation report: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get valuation report: {str(exc)}",
        )


# ================================================================
# HISTORY BY REPORT NUMBER
# ================================================================

@router.get(
    "/history/report/{report_number}",
)
async def get_valuation_by_report_number(
    report_number: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get valuation report by report number.
    """

    try:

        user_id = current_user.get("id")

        method = getattr(
            valuation_service,
            "get_valuation_by_report_number",
            None,
        )

        if not callable(method):

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Valuation report not found",
            )

        report = method(
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

        logger.exception(
            "Failed to get valuation report: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get valuation report: {str(exc)}",
        )


# ================================================================
# STATISTICS
# ================================================================

@router.get(
    "/stats",
    response_model=ValuationStats,
)
async def get_valuation_stats(
    current_user: dict = Depends(get_current_user),
):
    """
    Get valuation statistics.
    """

    try:

        user_id = current_user.get("id")

        method = getattr(
            valuation_service,
            "get_valuation_stats",
            None,
        )

        if not callable(method):

            return {
                "total_valuations": 0,
                "average_value": 0,
                "highest_value": 0,
                "lowest_value": 0,
            }

        return method(user_id)

    except Exception as exc:

        logger.exception(
            "Failed to get valuation stats: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get valuation stats: {str(exc)}",
        )


# ================================================================
# HEALTH
# ================================================================

@router.get(
    "/health",
    response_model=ValuationHealthResponse,
)
async def valuation_health():
    """
    Valuation service health check.
    """

    try:

        method = getattr(
            valuation_service,
            "health_check",
            None,
        )

        if callable(method):

            return method()

        return {
            "status": "healthy",
            "service": "valuation",
            "version": "3.0",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "available",
        }

    except Exception as exc:

        logger.exception(
            "Valuation health check failed: %s",
            exc,
        )

        return {
            "status": "degraded",
            "service": "valuation",
            "version": "3.0",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "unhealthy",
            "error": str(exc),
        }


# ================================================================
# BULK
# ================================================================

@router.post("/bulk")
async def bulk_valuation(
    requests: List[ValuationRequest],
    current_user: dict = Depends(get_current_user_optional),
):
    """
    Calculate multiple CRSP valuations.
    """

    results = []

    user_id = (
        current_user.get("id")
        if current_user
        else None
    )

    for request in requests:

        try:

            result = valuation_service.calculate_valuation(
                vehicle_crsp_id=request.vehicle_crsp_id,
                manufacture_year=request.manufacture_year,
                mileage_km=request.mileage_km,
                condition_name=request.condition_name,
                accident_status=request.accident_status,
                location_name=request.location_name,
                profit_margin_percent=request.profit_margin_percent,
                fuel_type=getattr(
                    request,
                    "fuel_type",
                    None,
                ),
                transmission=getattr(
                    request,
                    "transmission",
                    None,
                ),
                body_type=getattr(
                    request,
                    "body_type",
                    None,
                ),
            )

            results.append({
                "success": bool(
                    result.get(
                        "success",
                        False,
                    )
                ),
                "vehicle_crsp_id": (
                    request.vehicle_crsp_id
                ),
                "data": result,
            })

        except Exception as exc:

            logger.exception(
                "Bulk valuation failed for CRSP %s",
                request.vehicle_crsp_id,
            )

            results.append({
                "success": False,
                "vehicle_crsp_id": (
                    request.vehicle_crsp_id
                ),
                "error": str(exc),
            })

    return {
        "total": len(requests),
        "successful": sum(
            1
            for item in results
            if item["success"]
        ),
        "failed": sum(
            1
            for item in results
            if not item["success"]
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
    """
    Compare multiple CRSP valuations.
    """

    results = []

    for request in requests:

        try:

            result = valuation_service.calculate_valuation(
                vehicle_crsp_id=request.vehicle_crsp_id,
                manufacture_year=request.manufacture_year,
                mileage_km=request.mileage_km,
                condition_name=request.condition_name,
                accident_status=request.accident_status,
                location_name=request.location_name,
                profit_margin_percent=request.profit_margin_percent,
                fuel_type=getattr(
                    request,
                    "fuel_type",
                    None,
                ),
                transmission=getattr(
                    request,
                    "transmission",
                    None,
                ),
                body_type=getattr(
                    request,
                    "body_type",
                    None,
                ),
            )

            vehicle = result.get(
                "vehicle",
                {},
            )

            valuation = result.get(
                "valuation",
                {},
            )

            results.append({
                "vehicle_crsp_id": (
                    request.vehicle_crsp_id
                ),
                "make": vehicle.get(
                    "make"
                ),
                "model": vehicle.get(
                    "model"
                ),
                "year": (
                    request.manufacture_year
                ),
                "estimated_value": (
                    valuation.get(
                        "estimated_vehicle_value"
                    )
                    or result.get(
                        "estimated_value"
                    )
                    or result.get(
                        "market_value"
                    )
                ),
                "confidence_score": (
                    valuation.get(
                        "confidence_score"
                    )
                    or result.get(
                        "confidence_score",
                        0,
                    )
                ),
                "success": bool(
                    result.get(
                        "success",
                        False,
                    )
                ),
            })

        except Exception as exc:

            logger.exception(
                "Comparison failed for CRSP %s",
                request.vehicle_crsp_id,
            )

            results.append({
                "vehicle_crsp_id": (
                    request.vehicle_crsp_id
                ),
                "error": str(exc),
                "success": False,
            })

    return {
        "comparison": results,
        "total": len(results),
        "successful": sum(
            1
            for item in results
            if item["success"]
        ),
        "failed": sum(
            1
            for item in results
            if not item["success"]
        ),
    }


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    "router",
]
