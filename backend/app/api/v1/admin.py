# backend/app/api/v1/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from app.schemas.request import AdminSettingsRequest, FuelPriceRequest
from app.core.security import get_current_user
from app.core.database import supabase
from app.services.fuel_service import FuelService

router = APIRouter()
fuel_service = FuelService()

@router.put("/fuel-prices")
async def update_fuel_prices(
    request: FuelPriceRequest,
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
        # Update fuel price
        supabase.table("fuel_prices").update({
            "price": request.price
        }).eq("fuel_type", request.fuel_type).execute()
        
        return {"message": "Fuel price updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/settings")
async def update_settings(
    request: AdminSettingsRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update system settings (admin only)"""
    # Check if user is admin
    if not current_user.get("profile", {}).get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        # Update setting
        supabase.table("ownership_settings").upsert({
            "key": request.setting_key,
            "value": request.setting_value,
            "description": request.description
        }).execute()
        
        return {"message": "Settings updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/dashboard")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
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
        total_users = users_response.count
        
        # Get total vehicles
        vehicles_response = supabase.table("vehicle_variants").select("count", count="exact").execute()
        total_vehicles = vehicles_response.count
        
        # Get recent reports
        reports_response = supabase.table("mileage_reports").select("*").order("created_at", desc=True).limit(5).execute()
        
        return {
            "total_users": total_users,
            "total_vehicles": total_vehicles,
            "recent_reports": reports_response.data,
            "system_status": "operational"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
