# app/modules/running_cost/router.py
"""
Auto-D Kenya - Running Cost Routes
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException

from app.core.dependencies import get_current_user, get_current_user_optional
from app.modules.running_cost.schemas import (
    RunningCostRequest,
    RunningCostResponse,
    LegacyRunningCostResponse,
    ProjectionYear,
)
from app.modules.running_cost.service import RunningCostService

# FIX: main.py already applies prefix=settings.API_V1_PREFIX ("/api/v1") when
# including this router. Hardcoding it again here doubled every path to
# /api/v1/api/v1/... (confirmed via openapi.json — operationIds literally
# contained "api_v1_api_v1"). Do not add a prefix here.
router = APIRouter(tags=["Running Cost"])


# ============================================================
# VEHICLE ENDPOINTS
# ============================================================

@router.get("/makes")
async def get_makes(
    current_user: dict = Depends(get_current_user_optional)
):
    """
    GET /api/v1/makes
    Get all vehicle makes.
    """
    try:
        service = RunningCostService()
        makes = await service.get_makes()
        return {"status": "success", "data": makes, "count": len(makes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{make_id}")
async def get_models(
    make_id: int,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    GET /api/v1/models/{make_id}
    Get models by make ID.
    """
    try:
        service = RunningCostService()
        models = await service.get_models(make_id)
        return {"status": "success", "data": models, "count": len(models)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generations/{model_id}")
async def get_generations(
    model_id: int,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    GET /api/v1/generations/{model_id}
    Get generations by model ID.
    """
    try:
        service = RunningCostService()
        generations = await service.get_generations(model_id)
        return {"status": "success", "data": generations, "count": len(generations)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/variants/{generation_id}")
async def get_variants(
    generation_id: int,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    GET /api/v1/variants/{generation_id}
    Get variants by generation ID.
    """
    try:
        service = RunningCostService()
        variants = await service.get_variants(generation_id)
        return {"status": "success", "data": variants, "count": len(variants)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/variant/{variant_id}")
async def get_variant(
    variant_id: int,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    GET /api/v1/variant/{variant_id}
    Get variant by ID.
    """
    try:
        service = RunningCostService()
        variant = await service.get_variant(variant_id)
        if not variant:
            raise HTTPException(status_code=404, detail=f"Variant {variant_id} not found")
        return {"status": "success", "data": variant}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_vehicles(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    GET /api/v1/search
    Search vehicles by make, model, or variant name.
    """
    try:
        service = RunningCostService()
        results = await service.search_vehicles(q, limit)
        return {"status": "success", "data": results, "count": len(results), "query": q}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vehicles")
async def get_user_vehicles(
    current_user: dict = Depends(get_current_user)
):
    """
    GET /api/v1/vehicles
    Get user vehicles (requires authentication).

    NOTE: this duplicates GET /api/v1/vehicles already implemented properly
    in app/modules/vehicles/router.py against the real `vehicles` table.
    This copy is a stub returning an empty list — main.py registers the
    Vehicles module's router separately, so whichever one FastAPI resolves
    first for this exact path wins. Recommend deleting this duplicate route
    entirely once confirmed the Vehicles module version is the one in use.
    """
    try:
        return {"status": "success", "data": [], "message": "Stub — use /api/v1/vehicles from the Vehicles module instead"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# RUNNING COST CALCULATION
# ============================================================

@router.post("/running-cost/calculate", response_model=None)
async def calculate_running_cost(
    request: RunningCostRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    POST /api/v1/running-cost/calculate
    Calculate vehicle running costs.
    Requires authentication.
    
    Returns a dynamic response with all cost breakdowns including:
    - Trip summary (total, per km, breakdown)
    - Per km costs (fuel, service, tyres, insurance, depreciation)
    - Monthly costs
    - Annual costs
    - 5-year projection
    - Vehicle details
    - Finance calculation
    - Driving factors
    - Depreciation breakdown
    """
    try:
        service = RunningCostService()
        result = await service.calculate_running_cost(
            request=request,
            user_id=current_user["id"],
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# HEALTH ENDPOINT
# ============================================================

@router.get("/running-cost/health")
async def health():
    """
    GET /api/v1/running-cost/health
    Health check for running cost service.
    """
    return {
        "status": "healthy",
        "service": "running_cost",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================
# LEGACY ENDPOINTS (backward compatibility)
# ============================================================

@router.post("/running-cost/calculate-legacy", response_model=None)
async def calculate_running_cost_legacy(
    request: RunningCostRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    POST /api/v1/running-cost/calculate-legacy
    Legacy endpoint that returns the old field names.
    
    Returns a flat response with legacy field names for backward compatibility.
    """
    try:
        service = RunningCostService()
        result = await service.calculate_running_cost(
            request=request,
            user_id=current_user["id"],
        )
        # Return the result directly - the service already includes legacy fields
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# VEHICLE DETAILS (full hierarchy)
# ============================================================

@router.get("/vehicle-details/{variant_id}")
async def get_vehicle_details(
    variant_id: int,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    GET /api/v1/vehicle-details/{variant_id}
    Get full vehicle details including hierarchy.
    """
    try:
        service = RunningCostService()
        details = await service.get_variant_with_details(variant_id)
        if not details:
            raise HTTPException(status_code=404, detail=f"Variant {variant_id} not found")
        return {"status": "success", "data": details}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# TEST ENDPOINT (for debugging)
# ============================================================

@router.post("/running-cost/test")
async def test_running_cost(
    request: RunningCostRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    POST /api/v1/running-cost/test
    Test endpoint that returns the raw calculation without any formatting.
    Useful for debugging.
    """
    try:
        service = RunningCostService()
        
        # Log the request
        print(f"📊 Test Request: variant_id={request.variant_id}, distance={request.distance}")
        
        result = await service.calculate_running_cost(
            request=request,
            user_id=current_user["id"],
        )
        
        # Return the raw result
        return {
            "status": "success",
            "debug": {
                "variant_id": request.variant_id,
                "distance": request.distance,
                "annual_mileage": request.annual_mileage,
                "fuel_price": request.fuel_price,
            },
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# PUBLIC CALCULATION (no auth required - for demo)
# ============================================================

@router.post("/running-cost/calculate-public", response_model=None)
async def calculate_running_cost_public(
    request: RunningCostRequest,
):
    """
    POST /api/v1/running-cost/calculate-public
    Calculate vehicle running costs (public endpoint, no authentication required).
    Useful for testing and demo purposes.
    """
    try:
        service = RunningCostService()
        result = await service.calculate_running_cost(
            request=request,
            user_id=0,  # Public user
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
