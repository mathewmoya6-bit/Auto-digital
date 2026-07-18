# backend/app/api/v1/admin.py
"""
Admin API - Administrative endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from app.services.fuel_service import FuelService
from app.services.valuation_service import ValuationService
from app.core.security import get_current_user
from app.core.database import supabase
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
fuel_service = FuelService()
valuation_service = ValuationService()


@router.put("/fuel-prices")
async def update_fuel_prices(
    fuel_type: str,
    price: float,
    current_user: dict = Depends(get_current_user)
):
    """Update fuel prices (admin only)"""
    # Check if user is admin
    if not current_user.get("profile", {}).get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        result = fuel_service.update_fuel_price(fuel_type, price)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to update fuel price for {fuel_type}"
            )
        return {"message": f"Fuel price for {fuel_type} updated successfully", "data": result}
    except Exception as e:
        logger.error(f"Error updating fuel price: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update fuel price: {str(e)}"
        )


@router.get("/dashboard")
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user)
):
    """Get admin dashboard statistics (admin only)"""
    # Check if user is admin
    if not current_user.get("profile", {}).get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        # Get total users
        users_response = supabase.table("user_profiles").select("count", count="exact").execute()
        total_users = users_response.count or 0
        
        # Get total vehicles
        vehicles_response = supabase.table("vehicle_variants").select("count", count="exact").execute()
        total_vehicles = vehicles_response.count or 0
        
        # Get total valuations
        valuations_response = supabase.table("valuation_reports").select("count", count="exact").execute()
        total_valuations = valuations_response.count or 0
        
        # Get recent activity
        logs_response = supabase.table("admin_logs")\
            .select("*")\
            .order("created_at", desc=True)\
            .limit(10)\
            .execute()
        
        return {
            "total_users": total_users,
            "total_vehicles": total_vehicles,
            "total_valuations": total_valuations,
            "recent_activity": logs_response.data,
            "system_status": "operational"
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard statistics"
        )
