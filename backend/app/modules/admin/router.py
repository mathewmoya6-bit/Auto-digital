# app/modules/admin/router.py
# Auto-D Kenya - Admin Routes
# ================================================================
# TYPE: MODULE - Admin API routes

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_user, require_admin
from app.modules.admin.service import AdminService
from app.modules.admin.schemas import (
    AdminStatsResponse,
    AdminUsersResponse,
    AdminPaymentsResponse,
    AdminVehiclesResponse,
    AdminServicesResponse,
    AdminAnalyticsResponse,
    AdminStatusResponse,
    UpdateServiceRequest,
    UpdateServicePriceRequest,
    UpdateUserServiceRequest,
    CreateServiceRequest,
    RevenueReportResponse,
    ServicePricesResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()
admin_service = AdminService()


# ─── AUTH CHECK ──────────────────────────────────────────────────

async def verify_admin(current_user: dict = Depends(get_current_user)):
    """Verify that the current user is an admin."""
    # Check if user has admin role in metadata
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Check for admin role
    is_admin = current_user.get("app_metadata", {}).get("role") == "admin"
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


# ─── STATISTICS ──────────────────────────────────────────────────

@router.get("/admin/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    current_user: dict = Depends(verify_admin)
):
    """
    Get admin statistics.
    
    Returns:
        AdminStatsResponse: User, vehicle, payment, and revenue statistics
    """
    try:
        return await admin_service.get_stats()
    except Exception as e:
        logger.error(f"Error getting admin stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get admin stats: {str(e)}"
        )


# ─── USERS ──────────────────────────────────────────────────────

@router.get("/admin/users", response_model=AdminUsersResponse)
async def get_users(
    limit: int = Query(50, ge=1, le=200, description="Number of users to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    search: Optional[str] = Query(None, description="Search term for email or name"),
    current_user: dict = Depends(verify_admin)
):
    """
    Get all users with pagination and search.
    
    Returns:
        AdminUsersResponse: List of users with pagination info
    """
    try:
        return await admin_service.get_users(limit=limit, offset=offset, search=search)
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get users: {str(e)}"
        )


@router.get("/admin/users/{user_id}")
async def get_user_by_id(
    user_id: str,
    current_user: dict = Depends(verify_admin)
):
    """
    Get a specific user by ID.
    
    Returns:
        User details with services and payments
    """
    try:
        return await admin_service.get_user_by_id(user_id)
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )


@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(verify_admin)
):
    """
    Delete a user (admin action).
    
    Returns:
        Success message
    """
    try:
        return await admin_service.delete_user(user_id)
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


# ─── PAYMENTS ──────────────────────────────────────────────────

@router.get("/admin/payments", response_model=AdminPaymentsResponse)
async def get_all_payments(
    limit: int = Query(50, ge=1, le=200, description="Number of payments to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    status: Optional[str] = Query(None, description="Filter by status (pending, completed, failed)"),
    current_user: dict = Depends(verify_admin)
):
    """
    Get all payments with pagination and filtering.
    
    Returns:
        AdminPaymentsResponse: List of payments with pagination info
    """
    try:
        return await admin_service.get_all_payments(limit=limit, offset=offset, status=status)
    except Exception as e:
        logger.error(f"Error getting payments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payments: {str(e)}"
        )


# ─── REVENUE REPORT ──────────────────────────────────────────

@router.get("/admin/revenue", response_model=RevenueReportResponse)
async def get_revenue_report(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    current_user: dict = Depends(verify_admin)
):
    """
    Get revenue report for a date range.
    
    Returns:
        RevenueReportResponse: Revenue breakdown
    """
    try:
        return await admin_service.get_revenue_report(start_date=start_date, end_date=end_date)
    except Exception as e:
        logger.error(f"Error getting revenue report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get revenue report: {str(e)}"
        )


# ─── VEHICLES ──────────────────────────────────────────────────

@router.get("/admin/vehicles", response_model=AdminVehiclesResponse)
async def get_all_vehicles(
    limit: int = Query(50, ge=1, le=200, description="Number of vehicles to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    verified: Optional[bool] = Query(None, description="Filter by verification status"),
    current_user: dict = Depends(verify_admin)
):
    """
    Get all vehicles with pagination and filtering.
    
    Returns:
        AdminVehiclesResponse: List of vehicles with pagination info
    """
    try:
        return await admin_service.get_all_vehicles(limit=limit, offset=offset, verified=verified)
    except Exception as e:
        logger.error(f"Error getting vehicles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get vehicles: {str(e)}"
        )


# ─── SERVICES ──────────────────────────────────────────────────

@router.get("/admin/services", response_model=AdminServicesResponse)
async def get_all_services(
    current_user: dict = Depends(verify_admin)
):
    """
    Get all services with prices and purchase counts.
    
    Returns:
        AdminServicesResponse: List of services
    """
    try:
        return await admin_service.get_all_services()
    except Exception as e:
        logger.error(f"Error getting services: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get services: {str(e)}"
        )


@router.post("/admin/services", response_model=dict)
async def create_service(
    request: CreateServiceRequest,
    current_user: dict = Depends(verify_admin)
):
    """
    Create a new service (admin action).
    
    Returns:
        Created service data
    """
    try:
        return await admin_service.create_service(request.model_dump())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create service: {str(e)}"
        )


@router.put("/admin/services/{service_id}", response_model=dict)
async def update_service(
    service_id: int,
    request: UpdateServiceRequest,
    current_user: dict = Depends(verify_admin)
):
    """
    Update a service (admin action).
    
    Returns:
        Updated service data
    """
    try:
        return await admin_service.update_service(
            service_id=service_id,
            data=request.model_dump(exclude_unset=True)
        )
    except Exception as e:
        logger.error(f"Error updating service {service_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update service: {str(e)}"
        )


@router.delete("/admin/services/{service_id}", response_model=dict)
async def delete_service(
    service_id: int,
    current_user: dict = Depends(verify_admin)
):
    """
    Delete a service (admin action).
    
    Returns:
        Success message
    """
    try:
        return await admin_service.delete_service(service_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting service {service_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete service: {str(e)}"
        )


@router.put("/admin/services/price/{service_code}", response_model=dict)
async def update_service_price(
    service_code: str,
    request: UpdateServicePriceRequest,
    current_user: dict = Depends(verify_admin)
):
    """
    Update a service price (admin action).
    
    Returns:
        Updated service data
    """
    try:
        return await admin_service.update_service_price(
            service_code=service_code,
            price=request.price,
            currency=request.currency
        )
    except Exception as e:
        logger.error(f"Error updating service price {service_code}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update service price: {str(e)}"
        )


@router.get("/admin/services/prices", response_model=ServicePricesResponse)
async def get_service_prices(
    current_user: dict = Depends(verify_admin)
):
    """
    Get all service prices from the database.
    
    Returns:
        ServicePricesResponse: Service prices
    """
    try:
        return await admin_service.get_service_prices()
    except Exception as e:
        logger.error(f"Error getting service prices: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service prices: {str(e)}"
        )


# ─── USER SERVICES ──────────────────────────────────────────

@router.put("/admin/user-services", response_model=dict)
async def update_user_service(
    request: UpdateUserServiceRequest,
    current_user: dict = Depends(verify_admin)
):
    """
    Update a user's service status (admin action).
    
    Returns:
        Updated service data
    """
    try:
        return await admin_service.update_user_service(
            user_id=request.user_id,
            service_id=request.service_id,
            status=request.status
        )
    except Exception as e:
        logger.error(f"Error updating user service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user service: {str(e)}"
        )


# ─── ANALYTICS ──────────────────────────────────────────────────

@router.get("/admin/analytics", response_model=AdminAnalyticsResponse)
async def get_platform_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: dict = Depends(verify_admin)
):
    """
    Get platform analytics for the specified period.
    
    Returns:
        AdminAnalyticsResponse: Daily analytics data
    """
    try:
        return await admin_service.get_platform_analytics(days=days)
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )


# ─── SYSTEM STATUS ──────────────────────────────────────────

@router.get("/admin/status", response_model=AdminStatusResponse)
async def get_system_status(
    current_user: dict = Depends(verify_admin)
):
    """
    Get system status for admin dashboard.
    
    Returns:
        AdminStatusResponse: System health status
    """
    try:
        return await admin_service.get_system_status()
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system status: {str(e)}"
        )


# ─── HEALTH ──────────────────────────────────────────────────

@router.get("/admin/health")
async def admin_health():
    """
    Health check for admin service.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "admin",
        "timestamp": datetime.utcnow().isoformat()
    }
