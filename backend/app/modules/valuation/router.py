# app/modules/valuation/router.py
# Auto-D Kenya - Valuation Routes
# ================================================================
# TYPE: MODULE - Valuation API Routes

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import (
    get_current_user,
    get_current_user_optional,
)
from app.modules.valuation.schemas import (
    ValuationRequest,
    ValuationResponse,
    ValuationReportResponse,
)
from app.modules.valuation.service import ValuationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Vehicle Valuation"])

valuation_service = ValuationService()


# ================================================================
# CALCULATE VALUATION (Authenticated)
# ================================================================

@router.post(
    "/valuation/calculate",
    response_model=ValuationReportResponse,
)
async def calculate_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user),
):
    """Calculate a vehicle valuation."""

    try:

        return await valuation_service.calculate_valuation(
            variant_id=request.variant_id,
            year=request.vehicle_year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            location=request.location,
            fuel_type=request.fuel_type,
            transmission=request.transmission,
            ownership_count=request.ownership_count,
            service_history=request.service_history,
            user_id=current_user.get("id"),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Valuation failed")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ================================================================
# PUBLIC VALUATION
# ================================================================

@router.post(
    "/valuation/calculate-public",
    response_model=ValuationReportResponse,
)
async def calculate_public_valuation(
    request: ValuationRequest,
):
    """Public valuation endpoint."""

    try:

        return await valuation_service.calculate_valuation(
            variant_id=request.variant_id,
            year=request.vehicle_year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            location=request.location,
            fuel_type=request.fuel_type,
            transmission=request.transmission,
            ownership_count=request.ownership_count,
            service_history=request.service_history,
            user_id=None,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        logger.exception("Public valuation failed")

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# ================================================================
# HISTORY
# ================================================================

@router.get("/valuation/history")
async def get_history(
    current_user: dict = Depends(get_current_user),
):
    """Get valuation history."""

    return await valuation_service.get_valuation_history(
        current_user["id"]
    )


@router.get("/valuation/history/{report_id}")
async def get_history_item(
    report_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Get a valuation report."""

    report = await valuation_service.get_valuation_by_id(
        report_id,
        current_user["id"],
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    return report


# ================================================================
# STATISTICS
# ================================================================

@router.get("/valuation/stats")
async def get_stats(
    current_user: dict = Depends(get_current_user),
):
    """Get valuation statistics."""

    return await valuation_service.get_valuation_stats(
        current_user["id"]
    )


# ================================================================
# HEALTH
# ================================================================

@router.get("/valuation/health")
async def health():

    return {
        "status": "healthy",
        "service": "valuation",
        "version": "2.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ================================================================
# LEGACY ENDPOINT
# ================================================================

@router.post(
    "/valuation/calculate-legacy",
    response_model=ValuationResponse,
)
async def calculate_legacy(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user_optional),
):
    """
    Legacy valuation endpoint.

    Converts the new report format into the old flat format.
    """

    result = await valuation_service.calculate_valuation(
        variant_id=request.variant_id,
        year=request.vehicle_year,
        mileage=request.mileage,
        condition=request.condition,
        accident_history=request.accident_history,
        location=request.location,
        fuel_type=request.fuel_type,
        transmission=request.transmission,
        ownership_count=request.ownership_count,
        service_history=request.service_history,
        user_id=current_user.get("id") if current_user else None,
    )

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
            "depreciation_percentage": 0,
            "annual_rate": 0,
        },
        "adjustments": [],
        "market_comparison": None,
        "recommendation": None,
        "currency": "KES",
        "calculated_at": result["report"]["generated_at"],
    }
