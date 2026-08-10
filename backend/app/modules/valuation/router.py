# app/modules/valuation/router.py
"""AUTO-D valuation API routes."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.modules.valuation.schema import (
    CRSPVehicleResponse,
    ValuationRequest,
    ValuationResponse,
)
from app.modules.valuation.service import ValuationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/valuation", tags=["Valuation"])


@router.post("", response_model=ValuationResponse)
@router.post("/", response_model=ValuationResponse, include_in_schema=False)
def calculate_valuation(payload: ValuationRequest):
    """Calculate an indicative vehicle valuation.

    This route is synchronous because ValuationService and the Supabase
    repository are synchronous. Do not add ``await`` here.
    """
    try:
        service = ValuationService()
        result = service.calculate_valuation(**payload.model_dump(exclude_none=True))
        return result
    except Exception as exc:
        logger.exception("Valuation failed")
        raise HTTPException(status_code=500, detail=f"Valuation failed: {exc}")


@router.get("/crsp/{crsp_id}", response_model=CRSPVehicleResponse)
def get_crsp(crsp_id: int):
    try:
        service = ValuationService()
        data = service.get_crsp_vehicle(vehicle_crsp_id=crsp_id)
        return {
            "success": True,
            "found": bool(data),
            "data": data,
            "results": [data] if data else [],
            "message": None if data else "CRSP record not found",
        }
    except Exception as exc:
        logger.exception("CRSP lookup failed")
        raise HTTPException(status_code=500, detail=f"CRSP lookup failed: {exc}")


@router.get("/crsp", response_model=CRSPVehicleResponse)
def search_crsp(
    make: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    manufacture_year: Optional[int] = Query(None),
    engine_capacity_id: Optional[int] = Query(None),
    fuel_type: Optional[str] = Query(None),
    transmission: Optional[str] = Query(None),
    body_type: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=100),
):
    try:
        service = ValuationService()
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
        return {
            "success": True,
            "found": bool(results),
            "data": results[0] if results else None,
            "results": results,
            "message": None if results else "No CRSP records found",
        }
    except Exception as exc:
        logger.exception("CRSP search failed")
        raise HTTPException(status_code=500, detail=f"CRSP search failed: {exc}")
