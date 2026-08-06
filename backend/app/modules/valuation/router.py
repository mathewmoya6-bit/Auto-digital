# app/modules/valuation/router.py

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

router = APIRouter()
valuation_service = ValuationService()


@router.post(
    "/valuation/calculate",
    response_model=ValuationReportResponse
)
async def calculate_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
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
            user_id=current_user.get("id"),
        )

        return result

    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.post(
    "/valuation/calculate-public",
    response_model=ValuationReportResponse,
)
async def calculate_public(
    request: ValuationRequest,
):
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

    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.get("/valuation/history")
async def valuation_history(
    current_user: dict = Depends(get_current_user),
):
    return await valuation_service.get_valuation_history(
        current_user["id"]
    )


@router.get("/valuation/history/{report_id}")
async def valuation_report(
    report_id: int,
    current_user: dict = Depends(get_current_user),
):
    report = await valuation_service.get_valuation_by_id(
        report_id,
        current_user["id"],
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    return report


@router.get("/valuation/stats")
async def valuation_stats(
    current_user: dict = Depends(get_current_user),
):
    return await valuation_service.get_valuation_stats(
        current_user["id"]
    )


@router.get("/valuation/health")
async def health():
    return {
        "status": "healthy",
        "service": "valuation",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post(
    "/valuation/calculate-legacy",
    response_model=ValuationResponse,
)
async def calculate_legacy(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user_optional),
):
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

    return result
