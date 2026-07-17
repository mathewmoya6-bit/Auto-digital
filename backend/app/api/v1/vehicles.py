# backend/app/api/v1/vehicles.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from app.services.vehicle_service import VehicleService
from app.core.security import get_current_user

router = APIRouter()
vehicle_service = VehicleService()

@router.get("/makes")
async def get_makes() -> List[Dict[str, Any]]:
    """Get all vehicle makes"""
    return vehicle_service.get_makes()

@router.get("/models/{make_id}")
async def get_models(make_id: str) -> List[Dict[str, Any]]:
    """Get models by make ID"""
    models = vehicle_service.get_models_by_make(make_id)
    if not models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No models found for this make"
        )
    return models

@router.get("/variants/{model_id}")
async def get_variants(model_id: str) -> List[Dict[str, Any]]:
    """Get variants by model ID"""
    variants = vehicle_service.get_variants_by_model(model_id)
    if not variants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No variants found for this model"
        )
    return variants

@router.get("/{variant_id}")
async def get_vehicle(variant_id: str):
    """Get complete vehicle details by variant ID"""
    vehicle = vehicle_service.get_vehicle_details(variant_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    return vehicle
