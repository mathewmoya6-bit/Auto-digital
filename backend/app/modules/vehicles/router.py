# app/modules/vehicles/router.py

# ================================================================
# Auto-D Kenya - Vehicle Routes
# ================================================================
# CRSP-driven vehicle catalogue API.
#
# CRSP is the authoritative vehicle identity.
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
    """
    Return approved vehicle categories.
    """

    try:
        return await vehicle_service.get_categories()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get categories: {str(e)}",
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
    """
    Return vehicle makes.

    Category filtering is optional.
    """

    try:
        return await vehicle_service.get_makes(
            category_id=category_id
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get makes: {str(e)}",
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
    """
    Return models belonging to a make.
    """

    try:
        return await vehicle_service.get_models(
            make_id=make_id
        )

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get models: {str(e)}",
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
        description="Search make, model or vehicle details",
    ),
    make_id: Optional[int] = Query(
        None,
        description="Filter by make ID",
    ),
    model_id: Optional[int] = Query(
        None,
        description="Filter by model ID",
    ),
    fuel: Optional[str] = Query(
        None,
        description="Filter by fuel type",
    ),
    transmission: Optional[str] = Query(
        None,
        description="Filter by transmission",
    ),
    engine_capacity_cc: Optional[int] = Query(
        None,
        description="Filter by engine capacity in CC",
    ),
    year: Optional[int] = Query(
        None,
        description="Filter by CRSP/manufacture year",
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
    """
    Search the CRSP vehicle catalogue.
    """

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

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vehicle search failed: {str(e)}",
        )


# ================================================================
# SINGLE CRSP VEHICLE
# ================================================================

@router.get(
    "/{crsp_id}",
    response_model=VehicleMasterResponse,
)
async def get_vehicle(
    crsp_id: int,
    current_user: dict = Depends(get_current_user_optional),
):
    """
    Return one complete CRSP vehicle.

    crsp_id is the authoritative vehicle identifier.
    """

    try:
        return await vehicle_service.get_vehicle(
            crsp_id=crsp_id
        )

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get vehicle: {str(e)}",
        )


# ================================================================
# VEHICLE PROFILE
# ================================================================

@router.get(
    "/profile/{crsp_id}",
    response_model=VehicleMasterResponse,
)
async def get_vehicle_profile(
    crsp_id: int,
    current_user: dict = Depends(get_current_user_optional),
):
    """
    Return vehicle details together with CRSP pricing.
    """

    try:
        profile = await vehicle_service.get_vehicle_profile(
            crsp_id=crsp_id
        )

        # VehicleMasterResponse expects the vehicle fields at
        # the top level, so return the vehicle component.
        return profile["vehicle"]

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get vehicle profile: {str(e)}",
        )


# ================================================================
# BASE PRICE / CRSP
# ================================================================

@router.get(
    "/base-price/{crsp_id}",
    response_model=BasePriceResponse,
)
async def get_base_price(
    crsp_id: int,
    current_user: dict = Depends(get_current_user_optional),
):
    """
    Return CRSP reference price for a vehicle.
    """

    try:
        return await vehicle_service.get_base_price(
            crsp_id=crsp_id
        )

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get CRSP price: {str(e)}",
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
    """
    Return CRSP catalogue statistics.
    """

    try:
        return await vehicle_service.get_statistics()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}",
        )


# ================================================================
# HEALTH
# ================================================================

@router.get(
    "/health",
    response_model=VehicleHealthResponse,
)
async def vehicle_health():
    """
    Vehicle catalogue health check.
    """

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

    except Exception as e:
        return VehicleHealthResponse(
            status="degraded",
            service="vehicles",
            version="2.0",
            timestamp=datetime.utcnow().isoformat(),
            error=str(e),
        )


# ================================================================
# EXPORT
# ================================================================

__all__ = [
    "router",
]
