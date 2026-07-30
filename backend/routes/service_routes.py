# routes/service_routes.py
# Auto-D Kenya - Service Management Routes
# ================================================================
# TYPE: ROUTES - Service endpoints

from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime

from database import get_supabase
from schemas import ServiceResponse, ServiceRequestCreate
from auth import get_current_user

router = APIRouter()


@router.get("/mpesa/services")
async def get_services():
    """Get all available services."""
    try:
        supabase = get_supabase()
        response = supabase.table("services").select("*").eq("active", True).order("display_order").execute()
        return {"services": response.data, "count": len(response.data)}
    except Exception as e:
        # Return fallback services if database fails
        return {
            "services": [
                {"id": "1", "code": "mileage", "name": "Mileage Calculator", "price": 100, "currency": "KES", "icon": "📈", "active": True},
                {"id": "2", "code": "valuation", "name": "Instant Vehicle Value", "price": 150, "currency": "KES", "icon": "💰", "active": True},
                {"id": "3", "code": "ownership", "name": "Ownership Cost Report", "price": 200, "currency": "KES", "icon": "📊", "active": True}
            ],
            "count": 3
        }


@router.get("/mpesa/user/services")
async def get_user_services(current_user: dict = Depends(get_current_user)):
    """Get services purchased by the user."""
    try:
        supabase = get_supabase()
        response = supabase.table("user_services").select("*, services(*)").eq("user_id", current_user["id"]).execute()
        return {"services": response.data, "count": len(response.data)}
    except Exception as e:
        return {"services": [], "count": 0}


@router.post("/service-requests")
async def create_service_request(
    request: ServiceRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new service request."""
    try:
        supabase = get_supabase()
        
        # Get vehicle details
        vehicle = supabase.table("vehicles").select("*").eq("id", request.vehicle_id).eq("user_id", current_user["id"]).execute()
        if not vehicle.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found"
            )
        
        # Get service details
        service = supabase.table("services").select("*").eq("id", request.service_id).eq("active", True).execute()
        if not service.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )
        
        service_data = service.data[0]
        vehicle_data = vehicle.data[0]
        
        data = {
            "user_id": current_user["id"],
            "vehicle_id": request.vehicle_id,
            "vehicle_plate": vehicle_data["plate"],
            "service_id": request.service_id,
            "service_name": service_data["name"],
            "amount": float(service_data["price"]),
            "notes": request.notes,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        
        response = supabase.table("service_requests").insert(data).execute()
        
        if response.data:
            return {"message": "Service request created", "request": response.data[0]}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create request"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/service-requests")
async def get_user_requests(current_user: dict = Depends(get_current_user)):
    """Get all service requests for the current user."""
    try:
        supabase = get_supabase()
        response = supabase.table("service_requests").select("*").eq("user_id", current_user["id"]).order("created_at", desc=True).execute()
        return {"data": response.data, "count": len(response.data)}
    except Exception as e:
        return {"data": [], "count": 0}


@router.put("/service-requests/{request_id}/status")
async def update_request_status(
    request_id: str,
    status: str,
    current_user: dict = Depends(get_current_user)
):
    """Update the status of a service request."""
    try:
        supabase = get_supabase()
        
        # Verify ownership
        existing = supabase.table("service_requests").select("*").eq("id", request_id).eq("user_id", current_user["id"]).execute()
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found"
            )
        
        response = supabase.table("service_requests").update({"status": status}).eq("id", request_id).execute()
        
        if response.data:
            return {"message": f"Request status updated to {status}", "request": response.data[0]}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update status"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
