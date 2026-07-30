# app/modules/vehicles/router.py
# Auto-D Kenya - Vehicles Routes
# ================================================================
# TYPE: MODULE - Vehicles API routes

from fastapi import APIRouter, Depends, Query
from typing import Optional, List

from app.core.dependencies import get_current_user
from app.modules.vehicles.service import VehicleService
from app.modules.vehicles.schemas import VehicleRequest, VehicleResponse

router = APIRouter()
vehicle_service = VehicleService()


@router.get("/makes")
async def get_makes(category_id: Optional[str] = None):
    """Get all vehicle makes."""
    return await vehicle_service.get_makes(category_id)


@router.get("/models/{make_id}")
async def get_models(make_id: str):
    """Get models for a specific make."""
    return await vehicle_service.get_models(make_id)


@router.get("/generations/{model_id}")
async def get_generations(model_id: str):
    """Get generations for a specific model."""
    return await vehicle_service.get_generations(model_id)


@router.get("/variants/{generation_id}")
async def get_variants(generation_id: str):
    """Get variants for a specific generation."""
    return await vehicle_service.get_variants(generation_id)


@router.get("/variant/{variant_id}")
async def get_variant(variant_id: str):
    """Get detailed variant information."""
    return await vehicle_service.get_variant(variant_id)


@router.post("/vehicles", response_model=VehicleResponse)
async def add_vehicle(
    request: VehicleRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add a new vehicle."""
    data = request.dict(exclude_unset=True)
    result = await vehicle_service.add_vehicle(current_user["id"], data)
    return result


@router.get("/vehicles", response_model=List[VehicleResponse])
async def get_user_vehicles(current_user: dict = Depends(get_current_user)):
    """Get all vehicles for the current user."""
    return await vehicle_service.get_user_vehicles(current_user["id"])


@router.get("/vehicles/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(
    vehicle_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific vehicle."""
    return await vehicle_service.get_vehicle(vehicle_id, current_user["id"])


@router.put("/vehicles/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: str,
    request: VehicleRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update a vehicle."""
    data = request.dict(exclude_unset=True)
    return await vehicle_service.update_vehicle(vehicle_id, current_user["id"], data)


@router.delete("/vehicles/{vehicle_id}")
async def delete_vehicle(
    vehicle_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a vehicle."""
    await vehicle_service.delete_vehicle(vehicle_id, current_user["id"])
    return {"message": "Vehicle deleted successfully"}


@router.get("/search")
async def search_vehicles(q: str, limit: int = Query(10, le=50)):
    """Search for vehicles."""
    # Implementation would go here
    return {"message": "Search endpoint"}
