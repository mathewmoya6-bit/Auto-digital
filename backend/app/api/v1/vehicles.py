# backend/app/api/v1/vehicles.py

"""
Vehicle Routes
GET /api/v1/makes - Get Makes
GET /api/v1/models/{make_id} - Get Models
GET /api/v1/variants/{model_id} - Get Variants
GET /api/v1/{variant_id} - Get Vehicle
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel

from app.core.dependencies import get_current_user, get_optional_user
from app.services.vehicle_service import get_vehicle_service, VehicleService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Vehicles"])


# ─── Response Models ──────────────────────────────────────────────

class MakeResponse(BaseModel):
    """Vehicle make response"""
    id: str
    name: str
    country: Optional[str] = None
    logo_url: Optional[str] = None


class ModelResponse(BaseModel):
    """Vehicle model response"""
    id: str
    name: str
    make_id: str
    body_type: Optional[str] = None
    body_style: Optional[str] = None


class VariantResponse(BaseModel):
    """Vehicle variant response"""
    id: str
    name: str
    model_id: str
    make_id: str
    year: Optional[int] = None
    engine_cc: Optional[float] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    fuel_consumption: Optional[float] = None
    market_value: Optional[float] = None


class VehicleDetailResponse(VariantResponse):
    """Detailed vehicle response"""
    make_name: Optional[str] = None
    model_name: Optional[str] = None
    insurance_group: Optional[str] = None
    service_interval: Optional[int] = None
    tyre_size: Optional[str] = None
    depreciation_class: Optional[str] = None
    tyre_cost: Optional[float] = None
    service_cost: Optional[float] = None


# ─── Endpoints ────────────────────────────────────────────────────

@router.get("/makes", response_model=List[MakeResponse])
async def get_makes(
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """
    GET /api/v1/makes - Get all vehicle makes.
    
    Returns a list of all vehicle makes with their details.
    """
    try:
        service = get_vehicle_service()
        makes = service.get_makes()
        
        if not makes:
            return []
        
        return [
            MakeResponse(
                id=m.get("id"),
                name=m.get("name"),
                country=m.get("country"),
                logo_url=m.get("logo_url")
            )
            for m in makes
        ]
        
    except Exception as e:
        logger.error(f"Error getting makes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch vehicle makes"
        )


@router.get("/models/{make_id}", response_model=List[ModelResponse])
async def get_models_by_make(
    make_id: str,
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """
    GET /api/v1/models/{make_id} - Get models by make ID.
    
    Returns all vehicle models for a specific make.
    """
    try:
        service = get_vehicle_service()
        models = service.get_models_by_make(make_id)
        
        if not models:
            return []
        
        return [
            ModelResponse(
                id=m.get("id"),
                name=m.get("name"),
                make_id=m.get("make_id"),
                body_type=m.get("body_type"),
                body_style=m.get("body_style")
            )
            for m in models
        ]
        
    except Exception as e:
        logger.error(f"Error getting models for make {make_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch vehicle models"
        )


@router.get("/variants/{model_id}", response_model=List[VariantResponse])
async def get_variants_by_model(
    model_id: str,
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """
    GET /api/v1/variants/{model_id} - Get variants by model ID.
    
    Returns all vehicle variants for a specific model.
    """
    try:
        service = get_vehicle_service()
        variants = service.get_variants_by_model(model_id)
        
        if not variants:
            return []
        
        return [
            VariantResponse(
                id=v.get("id"),
                name=v.get("name"),
                model_id=v.get("model_id"),
                make_id=v.get("make_id"),
                year=v.get("year"),
                engine_cc=v.get("engine_cc"),
                fuel_type=v.get("fuel_type"),
                transmission=v.get("transmission"),
                fuel_consumption=v.get("fuel_consumption"),
                market_value=v.get("market_value")
            )
            for v in variants
        ]
        
    except Exception as e:
        logger.error(f"Error getting variants for model {model_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch vehicle variants"
        )


@router.get("/{variant_id}", response_model=VehicleDetailResponse)
async def get_vehicle(
    variant_id: str,
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """
    GET /api/v1/{variant_id} - Get vehicle details by variant ID.
    
    Returns complete vehicle details including make, model, and all specifications.
    """
    try:
        service = get_vehicle_service()
        vehicle = service.get_vehicle_details(variant_id)
        
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle with variant ID {variant_id} not found"
            )
        
        return vehicle
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting vehicle {variant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch vehicle details"
        )


# ─── Additional Helper Endpoints ──────────────────────────────────

@router.get("/search")
async def search_vehicles(
    q: Optional[str] = Query(None, description="Search query"),
    make: Optional[str] = Query(None, description="Filter by make"),
    model: Optional[str] = Query(None, description="Filter by model"),
    year_from: Optional[int] = Query(None, description="Year from"),
    year_to: Optional[int] = Query(None, description="Year to"),
    fuel_type: Optional[str] = Query(None, description="Filter by fuel type"),
    transmission: Optional[str] = Query(None, description="Filter by transmission"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    sort_by: Optional[str] = Query("market_value", description="Sort by field"),
    sort_order: Optional[str] = Query("asc", description="Sort order (asc/desc)"),
    limit: Optional[int] = Query(20, description="Limit results"),
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """
    Search vehicles with filters.
    """
    try:
        service = get_vehicle_service()
        
        filters = {
            "make": make,
            "model": model,
            "year_from": year_from,
            "year_to": year_to,
            "fuel_type": fuel_type,
            "transmission": transmission,
            "min_price": min_price,
            "max_price": max_price,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "limit": limit,
            "search_term": q
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        result = service.advanced_search(filters)
        
        return {
            "items": result.get("items", []),
            "total": result.get("total", 0),
            "limit": result.get("limit", 20),
            "offset": result.get("offset", 0)
        }
        
    except Exception as e:
        logger.error(f"Error searching vehicles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search vehicles"
        )


@router.get("/makes/{make_id}/models")
async def get_models_by_make_detailed(
    make_id: str,
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """
    Get models by make ID with detailed information.
    """
    try:
        service = get_vehicle_service()
        models = service.get_models_by_make(make_id)
        
        if not models:
            return []
        
        # Get make info
        makes = service.get_makes()
        make = next((m for m in makes if m.get("id") == make_id), None)
        
        return {
            "make": make,
            "models": models,
            "count": len(models)
        }
        
    except Exception as e:
        logger.error(f"Error getting models for make {make_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch models"
        )


@router.get("/variants/{model_id}/detailed")
async def get_variants_by_model_detailed(
    model_id: str,
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """
    Get variants by model ID with detailed information.
    """
    try:
        service = get_vehicle_service()
        variants = service.get_variants_by_model(model_id)
        
        if not variants:
            return {"variants": [], "count": 0}
        
        # Get model info
        models = service.get_models_by_make("all")  # This would need adjustment
        model = next((m for m in models if m.get("id") == model_id), None)
        
        return {
            "model": model,
            "variants": variants,
            "count": len(variants)
        }
        
    except Exception as e:
        logger.error(f"Error getting variants for model {model_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch variants"
        )
