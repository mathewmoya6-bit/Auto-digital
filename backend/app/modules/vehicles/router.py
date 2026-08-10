# app/modules/vehicles/router.py
# Auto-D Kenya - Vehicle Routes
# ================================================================
# TYPE: MODULE - Vehicle management API routes
# ================================================================

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, List
import logging

from app.modules.vehicles.service import VehicleService
from app.modules.vehicles.schemas import (
    CategoryResponse,
    MakeResponse,
    ModelResponse,
    GenerationResponse,
    VariantResponse,
    VehicleMasterResponse,
    VehicleSearchResponse,
    BasePriceResponse,
    VehicleStatisticsResponse,
    VehicleHealthResponse,
)
from app.core.dependencies import get_current_user, get_current_user_optional
from app.core.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)

# ─── ROUTER ──────────────────────────────────────────────────────────

# ✅ Only "Vehicles" tag - removed any "Vehicle Master" tags
router = APIRouter(
    prefix="/vehicles",
    tags=["Vehicles"],  # Only this tag
)

vehicle_service = VehicleService()


# ================================================================
# CATEGORIES
# ================================================================

@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get all vehicle categories.
    """
    try:
        return await vehicle_service.get_categories()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get categories: {str(e)}"
        )


# ================================================================
# MAKES
# ================================================================

@router.get("/makes", response_model=List[MakeResponse])
async def get_makes(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get all vehicle makes, optionally filtered by category.
    """
    try:
        return await vehicle_service.get_makes(category_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get makes: {str(e)}"
        )


# ================================================================
# MODELS
# ================================================================

@router.get("/models/{make_id}", response_model=List[ModelResponse])
async def get_models(
    make_id: int,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get models for a specific make.
    """
    try:
        return await vehicle_service.get_models(make_id)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get models: {str(e)}"
        )


# ================================================================
# GENERATIONS
# ================================================================

@router.get("/generations/{model_id}", response_model=List[GenerationResponse])
async def get_generations(
    model_id: int,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get generations for a specific model.
    """
    try:
        return await vehicle_service.get_generations(model_id)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get generations: {str(e)}"
        )


# ================================================================
# VARIANTS
# ================================================================

@router.get("/variants/{generation_id}", response_model=List[VariantResponse])
async def get_variants(
    generation_id: int,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get variants (engine options) for a specific generation.
    """
    try:
        return await vehicle_service.get_variants(generation_id)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get variants: {str(e)}"
        )


# ================================================================
# VARIANT DETAILS
# ================================================================

@router.get("/variant/{variant_id}", response_model=VariantResponse)
async def get_variant(
    variant_id: int,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get detailed information for a specific variant.
    """
    try:
        return await vehicle_service.get_variant(variant_id)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get variant: {str(e)}"
        )


# ================================================================
# VEHICLE MASTER
# ================================================================

@router.get("/master/{variant_id}", response_model=VehicleMasterResponse)
async def get_vehicle_master(
    variant_id: int,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get comprehensive vehicle master data for a variant.
    """
    try:
        return await vehicle_service.get_vehicle_master(variant_id)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get vehicle master: {str(e)}"
        )


@router.get("/master/search", response_model=List[VehicleSearchResponse])
async def search_vehicle_master(
    query: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Results limit"),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Search vehicle master data.
    """
    try:
        return await vehicle_service.search_vehicle_master(query, limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


# ================================================================
# BASE PRICE
# ================================================================

@router.get("/base-price/{variant_id}", response_model=BasePriceResponse)
async def get_base_price(
    variant_id: int,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get base price for a variant.
    """
    try:
        return await vehicle_service.get_base_price(variant_id)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get base price: {str(e)}"
        )


# ================================================================
# STATISTICS
# ================================================================

@router.get("/statistics", response_model=VehicleStatisticsResponse)
async def get_vehicle_statistics(
    current_user: dict = Depends(get_current_user)
):
    """
    Get vehicle statistics.
    """
    try:
        return await vehicle_service.get_statistics()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


# ================================================================
# HEALTH
# ================================================================

@router.get("/health", response_model=VehicleHealthResponse)
async def vehicle_health():
    """
    Health check for vehicle service.
    """
    try:
        return await vehicle_service.health_check()
    except Exception as e:
        return VehicleHealthResponse(
            status="degraded",
            service="vehicles",
            version="1.0",
            timestamp=datetime.utcnow().isoformat(),
            error=str(e)
        )


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    "router",
]
