# app/modules/valuation/routes.py
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_user
from app.modules.valuation.schemas import (
    CRSPSearchRequest,
    HealthCheckResponse,
    ValuationHistoryResponse,
    ValuationRequest,
    ValuationResponse,
    ValuationStatsResponse,
)
from app.modules.valuation.service import ValuationService, get_valuation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/valuation", tags=["valuation"])


@router.post("/calculate", response_model=ValuationResponse)
async def calculate_valuation(
    request: ValuationRequest,
    service: ValuationService = Depends(get_valuation_service),
    user: Optional[dict] = Depends(get_current_user),
) -> ValuationResponse:
    """
    Calculate vehicle valuation.

    Accepts either:
    - crsp_id for a known CRSP vehicle
    - make, model, and optional filters to search for matching CRSP record

    Returns estimated market value with confidence score and adjustments.
    """
    try:
        # Convert request to dict and call service
        result = service.calculate_valuation(
            crsp_id=request.crsp_id,
            make=request.make,
            model=request.model,
            manufacture_year=request.manufacture_year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            previous_owners=request.previous_owners,
            location=request.location,
            fuel_type=request.fuel_type,
            transmission=request.transmission,
            engine_capacity_id=request.engine_capacity_id,
            vehicle_type=request.vehicle_type,
            body_type=request.body_type,
        )

        # Ensure adjustments field exists (safety check)
        if "adjustments" not in result:
            result["adjustments"] = {}

        # Save to history if user is authenticated and valuation successful
        if (
            user 
            and result.get("success") 
            and result.get("crsp_found")
            and result.get("estimated_value") is not None
        ):
            try:
                service.repository.save_valuation_history(
                    user_id=user.get("id"),
                    valuation_data={
                        **result,
                        "mileage": request.mileage,
                        "condition": request.condition,
                        "accident_history": request.accident_history,
                        "location": request.location,
                        "fuel_type": request.fuel_type,
                        "transmission": request.transmission,
                        "body_type": request.body_type,
                        "manufacture_year": request.manufacture_year,
                        "created_at": datetime.now().isoformat(),
                    },
                )
            except Exception as exc:
                logger.warning("Failed to save valuation history: %s", exc)

        return ValuationResponse(**result)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Valuation calculation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/crsp/search", response_model=list)
async def search_crsp(
    make: Optional[str] = Query(None, description="Vehicle make"),
    model: Optional[str] = Query(None, description="Vehicle model"),
    manufacture_year: Optional[int] = Query(None, description="Manufacture year"),
    engine_capacity_id: Optional[int] = Query(None, description="Engine capacity ID"),
    fuel_type: Optional[str] = Query(None, description="Fuel type"),
    transmission: Optional[str] = Query(None, description="Transmission type"),
    body_type: Optional[str] = Query(None, description="Body type"),
    limit: int = Query(25, ge=1, le=100, description="Results limit"),
    service: ValuationService = Depends(get_valuation_service),
) -> list:
    """Search for CRSP vehicle records."""
    try:
        results = service.search_crsp(
            make=make,
            model=model,
            manufacture_year=manufacture_year,
            engine_capacity_id=engine_capacity_id,
            fuel_type=fuel_type,
            transmission=transmission,
            body_type=body_type,
            limit=limit,
        )
        return results

    except Exception as exc:
        logger.exception("CRSP search failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/history", response_model=ValuationHistoryResponse)
async def get_valuation_history(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    service: ValuationService = Depends(get_valuation_service),
    user: dict = Depends(get_current_user),
) -> ValuationHistoryResponse:
    """Get user's valuation history."""
    try:
        offset = (page - 1) * limit
        items = service.repository.get_valuation_history(
            user_id=user.get("id"),
            limit=limit,
            offset=offset,
        )

        # Get total count
        total = len(items) if items else 0

        return ValuationHistoryResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
        )

    except Exception as exc:
        logger.exception("Failed to get valuation history: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/stats", response_model=ValuationStatsResponse)
async def get_valuation_stats(
    service: ValuationService = Depends(get_valuation_service),
    user: dict = Depends(get_current_user),
) -> ValuationStatsResponse:
    """Get valuation statistics for the authenticated user."""
    try:
        stats = service.repository.get_valuation_stats(user.get("id"))
        return ValuationStatsResponse(**stats)

    except Exception as exc:
        logger.exception("Failed to get valuation stats: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    service: ValuationService = Depends(get_valuation_service),
) -> HealthCheckResponse:
    """Health check endpoint."""
    try:
        # Check database connection
        db_healthy = True
        try:
            service.repository.get_crsp_by_id(1)
        except Exception:
            db_healthy = False

        return HealthCheckResponse(
            status="healthy" if db_healthy else "degraded",
            service="valuation",
            version="2.0",
            timestamp=datetime.now(),
            database="healthy" if db_healthy else "unhealthy",
        )

    except Exception as exc:
        logger.exception("Health check failed: %s", exc)
        return HealthCheckResponse(
            status="degraded",
            service="valuation",
            version="2.0",
            timestamp=datetime.now(),
            database="unhealthy",
        )


@router.get("/crsp/{crsp_id}")
async def get_crsp_record(
    crsp_id: int,
    service: ValuationService = Depends(get_valuation_service),
) -> dict:
    """Get a specific CRSP record by ID."""
    try:
        record = service.repository.get_crsp_by_id(crsp_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"CRSP record with ID {crsp_id} not found",
            )
        return record

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get CRSP record: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
