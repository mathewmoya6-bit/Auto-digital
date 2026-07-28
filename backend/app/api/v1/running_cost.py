"""
Running Cost API - Calculate running costs for vehicles
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.request import RunningCostRequest
from app.schemas.response import RunningCostResponse
from app.services.vehicle_service import VehicleService
from app.engines.running_cost_engine import RunningCostEngine
from app.core.security import get_current_user_optional

# ─── Router ──────────────────────────────────────────────────────────
router = APIRouter()  # ✅ MUST HAVE THIS

vehicle_service = VehicleService()
running_cost_engine = RunningCostEngine()


# ─── Test Endpoint ──────────────────────────────────────────────────
@router.get("/ping")
async def running_cost_ping():
    """Test endpoint to verify router is working"""
    return {
        "status": "ok",
        "message": "Running cost router is active",
        "timestamp": datetime.utcnow().isoformat()
    }


# ─── Main Endpoint ──────────────────────────────────────────────────
@router.post("/calculate")
async def calculate_running_cost(
    request: RunningCostRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
) -> RunningCostResponse:
    """Calculate running cost for a vehicle."""
    vehicle = vehicle_service.get_variant(request.variant_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    response = running_cost_engine.calculate(vehicle, request)
    return response
