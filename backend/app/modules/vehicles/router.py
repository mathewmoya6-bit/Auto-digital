
# ================================================================
# Auto-D Kenya - Vehicle Routes
# ================================================================
# CRSP-driven vehicle catalogue API.
#
# Source of truth:
#     public.vehicle_crsp_lookup
#
# Authoritative vehicle identifier:
#     crsp_id
# ================================================================

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.modules.vehicles.service import VehicleService
from app.modules.vehicles.schemas import (
    CategoryResponse,
    MakeResponse,
    ModelResponse,
    VehicleSearchResponse,
    VehicleMasterResponse,
    BasePriceResponse,
    VehicleStatisticsResponse,
    VehicleHealthResponse,
)
from app.core.dependencies import get_current_user, get_current_user_optional
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
)


# ================================================================
# ROUTER
# ================================================================

router = APIRouter(
    prefix="/vehicles",
    tags=["Vehicles"],
)

vehicle_service = VehicleService()


# ================================================================
# CATEGORIES
# ================================================================

@router.get(
    "/categories",
    response_model=List[CategoryResponse],
)
async def get_categories(
    current_user: dict = Depends(get_current_user_optional),
):
    """Return approved vehicle categories."""

    try:
        return await vehicle_service.get_categories()

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get categories: {str(exc)}",
        )


# ================================================================
# MAKES
# ================================================================

@router.get(
    "/makes",
    response_model=List[MakeResponse],
)
async def get_makes(
    category_id: Optional[int] = Query(
        None,
        description="Optional application category ID",
    ),
    current_user: dict = Depends(get_current_user_optional),
):
    """Return all CRSP vehicle makes."""

    try:
        return await vehicle_service.get_makes(
            category_id=category_id,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get makes: {str(exc)}",
        )


# ================================================================
# MODELS
# ================================================================

@router.get(
    "/models/{make_id}",
    response_model=List[ModelResponse],
)
async def get_models(
    make_id: int,
    current_user: dict = Depends(get_current_user_optional),
):
    """Return CRSP models for a make."""

    try:
        return await vehicle_service.get_models(
            make_id=make_id,
        )

    except ValidationException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except NotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get models: {str(exc)}",
        )


# ================================================================
# VEHICLE SEARCH
# ================================================================

@router.get(
    "/search",
    response_model=List[VehicleSearchResponse],
)
async def search_vehicles(
    search: Optional[str] = Query(
        None,
        min_length=2,
        description="Search make, model or trim",
    ),
    make_id: Optional[int] = Query(
        None,
        description="CRSP make ID",
    ),
    model_id: Optional[int] = Query(
        None,
        description="CRSP model ID",
    ),
    fuel: Optional[str] = Query(
        None,
        description="Fuel type",
    ),
    transmission: Optional[str] = Query(
        None,
        description="Transmission type",
    ),
    engine_capacity_cc: Optional[int] = Query(
        None,
        description="Engine capacity in CC",
    ),
    year: Optional[int] = Query(
        None,
        description="Manufacture or CRSP year",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=500,
        description="Maximum number of results",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Pagination offset",
    ),
    current_user: dict = Depends(get_current_user_optional),
):
    """Search the CRSP vehicle catalogue."""

    try:
        return await vehicle_service.search_vehicles(
            search=search,
            make_id=make_id,
            model_id=model_id,
            fuel=fuel,
            transmission=transmission,
            engine_capacity_cc=engine_capacity_cc,
            year=year,
            limit=limit,
            offset=offset,
        )

    except ValidationException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vehicle search failed: {str(exc)}",
        )


# ================================================================
# VEHICLE PROFILE
# ================================================================

@router.get(
    "/profile/{crsp_id}",
)
async def get_vehicle_profile(
    crsp_id: int,
    current_user: dict = Depends(get_current_user_optional),
):
    """
    Return the complete CRSP vehicle profile.

    Includes:
        vehicle
        pricing
    """

    try:
        return await vehicle_service.get_vehicle_profile(
            crsp_id=crsp_id,
        )

    except ValidationException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except NotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get vehicle profile: {str(exc)}",
        )


# ================================================================
# BASE PRICE
# ================================================================

@router.get(
    "/base-price/{crsp_id}",
    response_model=BasePriceResponse,
)
async def get_base_price(
    crsp_id: int,
    current_user: dict = Depends(get_current_user_optional),
):
    """Return the CRSP reference price."""

    try:
        return await vehicle_service.get_base_price(
            crsp_id=crsp_id,
        )

    except ValidationException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except NotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get CRSP price: {str(exc)}",
        )


# ================================================================
# STATISTICS
# ================================================================

@router.get(
    "/statistics",
    response_model=VehicleStatisticsResponse,
)
async def get_vehicle_statistics(
    current_user: dict = Depends(get_current_user),
):
    """Return CRSP catalogue statistics."""

    try:
        return await vehicle_service.get_statistics()

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(exc)}",
        )


# ================================================================
# HEALTH
# ================================================================

@router.get(
    "/health",
    response_model=VehicleHealthResponse,
)
async def vehicle_health():
    """Check CRSP vehicle catalogue health."""

    try:
        result = await vehicle_service.health_check()

        return VehicleHealthResponse(
            status=result.get("status", "healthy"),
            service="vehicles",
            version="2.0",
            timestamp=datetime.utcnow().isoformat(),
            database=result.get("database"),
            crsp_records=result.get("crsp_records"),
            error=result.get("error"),
        )

    except Exception as exc:
        return VehicleHealthResponse(
            status="degraded",
            service="vehicles",
            version="2.0",
            timestamp=datetime.utcnow().isoformat(),
            database="error",
            crsp_records=0,
            error=str(exc),
        )


# ================================================================
# SINGLE VEHICLE
# ================================================================
# IMPORTANT:
# This dynamic route MUST remain AFTER all named routes above.
# Otherwise paths such as /statistics, /health, etc. can be
# interpreted as a crsp_id route.

@router.get(
    "/{crsp_id}",
    response_model=VehicleMasterResponse,
)
async def get_vehicle(
    crsp_id: int,
    current_user: dict = Depends(get_current_user_optional),
):
    """Return one CRSP vehicle by authoritative crsp_id."""

    try:
        return await vehicle_service.get_vehicle(
            crsp_id=crsp_id,
        )

    except ValidationException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except NotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get vehicle: {str(exc)}",
        )


# ================================================================
# EXPORT
# ================================================================

__all__ = [
    "router",
]

