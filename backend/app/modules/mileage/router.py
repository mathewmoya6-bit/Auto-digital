# app/modules/mileage/router.py

"""
Mileage Router
==============

API endpoints for mileage operations.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.core.dependencies import (
    get_current_user,
    get_current_admin_user,
    get_current_user_optional
)
from .schemas import (
    MileageCreate,
    MileageUpdate,
    MileageResponse,
    MileageListResponse,
    MileageAnalytics,
    MileageValidationRequest,
    MileageValidationResponse,
    MileageAlertResponse,
    MileageSummaryResponse,
)
from .service import MileageService

router = APIRouter(
    prefix="/mileage",
    tags=["Mileage"]
)


# ─── Mileage Record Endpoints ─────────────────────────────────────

@router.post(
    "/records",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create mileage record",
    description="Create a new mileage record for a vehicle"
)
async def create_mileage_record(
    data: MileageCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new mileage record.
    
    - **vehicle_id**: ID of the vehicle
    - **mileage**: Current mileage in kilometers
    - **location**: Optional location of recording
    - **notes**: Optional notes about the recording
    """
    service = MileageService()
    result = await service.create_mileage(data, current_user["id"])
    return {
        "status": "success",
        "message": "Mileage record created successfully",
        "data": result
    }


@router.get(
    "/records/{record_id}",
    response_model=dict,
    summary="Get mileage record",
    description="Get a specific mileage record by ID"
)
async def get_mileage_record(
    record_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a mileage record by ID.
    """
    service = MileageService()
    record = await service.repository.get_by_id(record_id)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mileage record not found"
        )
    
    return {
        "status": "success",
        "data": record
    }


@router.get(
    "/vehicles/{vehicle_id}/records",
    response_model=dict,
    summary="Get vehicle mileage records",
    description="Get all mileage records for a vehicle"
)
async def get_vehicle_mileage_records(
    vehicle_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get mileage records for a specific vehicle.
    
    - **vehicle_id**: ID of the vehicle
    - **limit**: Number of records to return (1-100)
    - **offset**: Number of records to skip
    """
    service = MileageService()
    result = await service.get_vehicle_mileage(vehicle_id, limit, offset)
    
    return {
        "status": "success",
        "data": result
    }


@router.put(
    "/records/{record_id}",
    response_model=dict,
    summary="Update mileage record",
    description="Update a mileage record"
)
async def update_mileage_record(
    record_id: str,
    data: MileageUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a mileage record.
    """
    service = MileageService()
    result = await service.update_mileage(record_id, data, current_user["id"])
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mileage record not found"
        )
    
    return {
        "status": "success",
        "message": "Mileage record updated successfully",
        "data": result
    }


@router.delete(
    "/records/{record_id}",
    response_model=dict,
    summary="Delete mileage record",
    description="Delete a mileage record"
)
async def delete_mileage_record(
    record_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a mileage record.
    """
    service = MileageService()
    result = await service.delete_mileage(record_id, current_user["id"])
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mileage record not found"
        )
    
    return {
        "status": "success",
        "message": "Mileage record deleted successfully"
    }


# ─── Validation Endpoints ─────────────────────────────────────────

@router.post(
    "/validate",
    response_model=MileageValidationResponse,
    summary="Validate mileage",
    description="Validate mileage data for anomalies"
)
async def validate_mileage(
    data: MileageValidationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Validate mileage data.
    
    - **vehicle_id**: Vehicle ID
    - **mileage**: Mileage to validate
    - **previous_mileage**: Optional previous mileage
    """
    service = MileageService()
    return await service.validate_mileage(
        data.vehicle_id,
        data.mileage,
        data.previous_mileage
    )


# ─── Analytics Endpoints ──────────────────────────────────────────

@router.get(
    "/vehicles/{vehicle_id}/analytics",
    response_model=dict,
    summary="Get mileage analytics",
    description="Get mileage analytics for a vehicle"
)
async def get_mileage_analytics(
    vehicle_id: str,
    period: str = Query("month", regex="^(day|week|month|year)$"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get mileage analytics for a vehicle.
    
    - **vehicle_id**: Vehicle ID
    - **period**: Analysis period (day, week, month, year)
    """
    service = MileageService()
    analytics = await service.get_analytics(vehicle_id, period)
    
    return {
        "status": "success",
        "data": analytics
    }


@router.get(
    "/vehicles/{vehicle_id}/latest",
    response_model=dict,
    summary="Get latest mileage",
    description="Get the latest mileage record for a vehicle"
)
async def get_latest_mileage(
    vehicle_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the latest mileage record for a vehicle.
    """
    service = MileageService()
    record = await service.get_latest_mileage(vehicle_id)
    
    return {
        "status": "success",
        "data": record
    }


@router.get(
    "/vehicles/{vehicle_id}/service-check",
    response_model=MileageAlertResponse,
    summary="Check service due",
    description="Check if a vehicle is due for service"
)
async def check_service_due(
    vehicle_id: str,
    current_mileage: int = Query(..., description="Current mileage"),
    service_interval: int = Query(15000, description="Service interval in KM"),
    current_user: dict = Depends(get_current_user)
):
    """
    Check if a vehicle is due for service.
    
    - **vehicle_id**: Vehicle ID
    - **current_mileage**: Current mileage
    - **service_interval**: Service interval in kilometers (default: 15000)
    """
    service = MileageService()
    result = await service.check_service_due(
        vehicle_id,
        current_mileage,
        service_interval
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No mileage records found for this vehicle"
        )
    
    return result


@router.post(
    "/records/{record_id}/verify",
    response_model=dict,
    summary="Verify mileage record",
    description="Verify a mileage record (admin only)"
)
async def verify_mileage_record(
    record_id: str,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Verify a mileage record. Admin only.
    """
    service = MileageService()
    result = await service.verify_mileage(record_id, current_user["id"])
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mileage record not found"
        )
    
    return {
        "status": "success",
        "message": "Mileage record verified successfully",
        "data": result
    }


@router.get(
    "/summary/vehicles/{vehicle_id}",
    response_model=dict,
    summary="Get mileage summary",
    description="Get a summary of mileage for a vehicle"
)
async def get_mileage_summary(
    vehicle_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a summary of mileage for a vehicle.
    """
    service = MileageService()
    
    # Get latest record
    latest = await service.get_latest_mileage(vehicle_id)
    
    # Get statistics
    stats = await service.repository.get_statistics(vehicle_id)
    
    # Get service alert
    if latest:
        service_alert = await service.check_service_due(
            vehicle_id,
            latest.get("mileage", 0)
        )
    else:
        service_alert = None
    
    return {
        "status": "success",
        "data": {
            "vehicle_id": vehicle_id,
            "current_mileage": latest.get("mileage") if latest else 0,
            "last_updated": latest.get("date_recorded") if latest else None,
            "total_records": stats.get("count", 0),
            "average_mileage": stats.get("avg_mileage", 0),
            "service_alert": service_alert.dict() if service_alert else None
        }
    }


# ─── Admin Endpoints ──────────────────────────────────────────────

@router.get(
    "/admin/vehicles/{vehicle_id}/history",
    response_model=dict,
    summary="Get full mileage history (admin)",
    description="Get complete mileage history for admin review"
)
async def get_mileage_history(
    vehicle_id: str,
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Get full mileage history for admin review.
    """
    service = MileageService()
    history = await service.repository.get_mileage_history(vehicle_id, days)
    
    return {
        "status": "success",
        "data": {
            "vehicle_id": vehicle_id,
            "days": days,
            "records": history
        }
    }
