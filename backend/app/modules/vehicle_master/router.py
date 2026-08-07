"""
Auto-D Kenya
Vehicle Master Admin Router
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.modules.vehicle_master.schemas import (
    VehicleMasterUpdate,
    BasePriceUpdate,
    SpecificationUpdate,
    VehicleUpdate,
    VehicleSearchParams,
)
from app.modules.vehicle_master.service import VehicleMasterService
from app.modules.vehicle_master.permissions import require_vehicle_master_access

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/vehicle-master",
    tags=["Vehicle Master Admin"],
)

service = VehicleMasterService()


# ==========================================================
# DASHBOARD
# ==========================================================

@router.get("/dashboard")
async def dashboard(
    _=Depends(require_vehicle_master_access),
):
    """Get vehicle database dashboard statistics."""
    return await service.get_dashboard()


# ==========================================================
# SEARCH
# ==========================================================

@router.get("/search")
async def search_vehicle_database(
    make: Optional[str] = Query(None, description="Filter by make name"),
    model: Optional[str] = Query(None, description="Filter by model name"),
    year: Optional[int] = Query(None, description="Filter by year (matches generation range)"),
    fuel: Optional[str] = Query(None, description="Filter by fuel type"),
    transmission: Optional[str] = Query(None, description="Filter by transmission type"),
    body_type: Optional[str] = Query(None, description="Filter by body type"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    _=Depends(require_vehicle_master_access),
):
    """Search the master vehicle database."""
    return await service.search(
        make=make,
        model=model,
        year=year,
        fuel=fuel,
        transmission=transmission,
        body_type=body_type,
        page=page,
        per_page=per_page,
    )


# ==========================================================
# GET VEHICLE
# ==========================================================

@router.get("/{variant_id}")
async def get_vehicle(
    variant_id: int,
    _=Depends(require_vehicle_master_access),
):
    """Get complete vehicle by variant ID."""
    vehicle = await service.get_vehicle(variant_id)
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )
    return vehicle


# ==========================================================
# UPDATE COMPLETE VEHICLE
# ==========================================================

@router.put("/{variant_id}")
async def update_vehicle(
    variant_id: int,
    payload: VehicleMasterUpdate,
    _=Depends(require_vehicle_master_access),
):
    """Update complete vehicle."""
    return await service.update_vehicle(
        variant_id,
        payload.model_dump(exclude_none=True),
    )


# ==========================================================
# UPDATE VARIANT
# ==========================================================

@router.patch("/{variant_id}/variant")
async def update_variant(
    variant_id: int,
    payload: VehicleUpdate,
    _=Depends(require_vehicle_master_access),
):
    """Update variant."""
    return await service.update_variant(
        variant_id,
        payload.model_dump(exclude_none=True),
    )


# ==========================================================
# UPDATE SPECIFICATIONS
# ==========================================================

@router.patch("/{variant_id}/specifications")
async def update_specifications(
    variant_id: int,
    payload: SpecificationUpdate,
    _=Depends(require_vehicle_master_access),
):
    """Update vehicle specifications."""
    return await service.update_specifications(
        variant_id,
        payload.model_dump(exclude_none=True),
    )


# ==========================================================
# UPDATE BASE PRICE
# ==========================================================

@router.patch("/{variant_id}/pricing")
async def update_pricing(
    variant_id: int,
    payload: BasePriceUpdate,
    _=Depends(require_vehicle_master_access),
):
    """Update vehicle base price."""
    return await service.update_base_price(
        variant_id,
        payload.model_dump(exclude_none=True),
    )


# ==========================================================
# DEACTIVATE VEHICLE
# ==========================================================

@router.delete("/{variant_id}")
async def deactivate_vehicle(
    variant_id: int,
    _=Depends(require_vehicle_master_access),
):
    """Soft-delete vehicle."""
    return await service.deactivate_vehicle(variant_id)


# ==========================================================
# BULK OPERATIONS
# ==========================================================

@router.post("/pricing/bulk")
async def bulk_update_pricing(
    updates: list[dict],
    _=Depends(require_vehicle_master_access),
):
    """Bulk update base prices."""
    return await service.bulk_update_prices(updates)


# ==========================================================
# HEALTH
# ==========================================================

@router.get("/health")
async def health_check():
    """Health check for vehicle master module."""
    return {
        "module": "Vehicle Master",
        "status": "healthy",
        "version": "1.0.0",
    }
