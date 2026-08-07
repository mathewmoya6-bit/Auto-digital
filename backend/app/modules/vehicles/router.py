# app/modules/vehicles/router.py

"""
Auto-D Kenya
Vehicle Master Router
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.modules.vehicles.service import VehicleService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/vehicles",
    tags=["Vehicle Master"],
)

service = VehicleService()

# ==========================================================
# VEHICLE CATEGORIES
# ==========================================================

@router.get("/categories")
async def get_categories():
    """Get all vehicle categories."""
    return await service.get_categories()


# ==========================================================
# MAKES
# ==========================================================

@router.get("/makes")
async def get_makes(
    category_id: Optional[int] = Query(default=None)
):
    """Get vehicle makes."""
    return await service.get_makes(category_id)


# ==========================================================
# MODELS
# ==========================================================

@router.get("/models/{make_id}")
async def get_models(make_id: int):
    """Get models for a make."""
    return await service.get_models(make_id)


# ==========================================================
# GENERATIONS
# ==========================================================

@router.get("/generations/{model_id}")
async def get_generations(model_id: int):
    """Get generations."""
    return await service.get_generations(model_id)


# ==========================================================
# VARIANTS
# ==========================================================

@router.get("/variants/{generation_id}")
async def get_variants(generation_id: int):
    """Get variants."""
    return await service.get_variants(generation_id)


@router.get("/variant/{variant_id}")
async def get_variant(variant_id: int):
    """Get a single variant."""

    vehicle = await service.get_variant(variant_id)

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail="Vehicle variant not found",
        )

    return vehicle


# ==========================================================
# MASTER VEHICLE DATABASE
# ==========================================================

@router.get("/master/{variant_id}")
async def get_vehicle_master(
    variant_id: int,
):
    """Return complete vehicle."""

    vehicle = await service.get_vehicle_master(
        variant_id
    )

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail="Vehicle not found",
        )

    return vehicle


@router.get("/master/search")
async def search_vehicle_master(
    make: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[int] = None,
    fuel: Optional[str] = None,
    transmission: Optional[str] = None,
):
    """Search master vehicle database."""

    return await service.search_vehicle_master(
        make=make,
        model=model,
        year=year,
        fuel=fuel,
        transmission=transmission,
    )


# ==========================================================
# BASE PRICE
# ==========================================================

@router.get("/base-price/{variant_id}")
async def get_base_price(
    variant_id: int,
):
    """Get CRSP/Base Price."""

    return await service.get_base_price(
        variant_id
    )


# ==========================================================
# DASHBOARD
# ==========================================================

@router.get("/statistics")
async def statistics():
    """Vehicle database statistics."""

    return {
        "total_vehicles": await service.get_master_vehicle_count()
    }


# ==========================================================
# HEALTH
# ==========================================================

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "module": "Vehicle Master",
    }
