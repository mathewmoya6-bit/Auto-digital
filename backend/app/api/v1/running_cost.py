"""
Running Cost API - Calculate running costs for vehicles
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.schemas.request import RunningCostRequest
from app.schemas.response import RunningCostResponse
from app.services.vehicle_service import VehicleService
from app.engines.running_cost_engine import RunningCostEngine
from app.core.security import get_current_user_optional

# ─── Router ──────────────────────────────────────────────────────────
router = APIRouter()
logger = logging.getLogger(__name__)

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


# ─── Calculate Running Cost ────────────────────────────────────────
@router.post("/calculate")
async def calculate_running_cost(
    request: RunningCostRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
) -> dict:
    """
    Calculate running cost for a vehicle.
    
    Works anonymously; if a valid Supabase session token is supplied,
    current_user will be populated for saving the report.
    """
    try:
        logger.info(f"Running cost request for variant {request.variant_id}")

        # Get vehicle details
        vehicle = vehicle_service.get_variant(request.variant_id)
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle variant '{request.variant_id}' not found."
            )

        # Calculate running cost
        result = running_cost_engine.calculate(vehicle, request)

        # Return response
        return {
            "status": "success",
            "message": "Running cost calculated successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "data": result,
            "user_id": current_user.get("id") if current_user else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Running cost calculation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
