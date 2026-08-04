# app/modules/admin/router.py
# Auto-D Kenya - Admin Router
# ================================================================

from typing import Optional
from datetime import datetime, date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_user, get_admin_user
from app.core.exceptions import NotFoundException, ValidationException

from .schemas import (
    AdminStatsResponse,
    AdminUsersResponse,
    AdminUserDetailResponse,
    AdminPaymentsResponse,
    AdminVehiclesResponse,
    AdminServicesResponse,
    AdminAnalyticsResponse,
    AdminStatusResponse,
    RevenueReportResponse,
    ServicePricesResponse,
    UserServicesResponse,
    CreateServiceRequest,
    ServiceResponse,
    UpdateServiceRequest,
    UpdateServicePriceRequest,
    UpdateUserServiceRequest,
    UpdateUserServiceResponse,
    DeleteUserResponse,
    DeleteServiceResponse,
    AdminHealthResponse,
    SuccessResponse,
)
from .service import AdminService

router = APIRouter(prefix="/admin", tags=["Admin"])


# ─── DASHBOARD & STATS ──────────────────────────────────────────

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> AdminStatsResponse:
    """Get admin dashboard statistics."""
    return await service.get_stats()


# ─── USER MANAGEMENT ─────────────────────────────────────────────

@router.get("/users", response_model=AdminUsersResponse)
async def get_users(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    search: Optional[str] = Query(None, description="Search term"),
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> AdminUsersResponse:
    """Get list of users."""
    return await service.get_users(limit=limit, offset=offset, search=search)


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
async def get_user_detail(
    user_id: UUID,
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> AdminUserDetailResponse:
    """Get detailed user information."""
    try:
        user = await service.get_user_detail(user_id)
        return AdminUserDetailResponse(success=True, data=user)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/users/{user_id}", response_model=DeleteUserResponse)
async def delete_user(
    user_id: UUID,
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> DeleteUserResponse:
    """Delete a user."""
    try:
        return await service.delete_user(user_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ─── PAYMENT MANAGEMENT ──────────────────────────────────────────

@router.get("/payments", response_model=AdminPaymentsResponse)
async def get_payments(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    status: Optional[str] = Query(None, description="Filter by status"),
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> AdminPaymentsResponse:
    """Get list of payments."""
    return await service.get_payments(
        limit=limit,
        offset=offset,
        status=status,
        user_id=user_id,
    )


# ─── VEHICLE MANAGEMENT ──────────────────────────────────────────

@router.get("/vehicles", response_model=AdminVehiclesResponse)
async def get_vehicles(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    verified: Optional[bool] = Query(None, description="Filter by verification status"),
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> AdminVehiclesResponse:
    """Get list of vehicles."""
    return await service.get_vehicles(
        limit=limit,
        offset=offset,
        user_id=user_id,
        verified=verified,
    )


# ─── SERVICE MANAGEMENT ──────────────────────────────────────────

@router.get("/services", response_model=AdminServicesResponse)
async def get_services(
    active_only: bool = Query(False, description="Only return active services"),
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> AdminServicesResponse:
    """Get list of services."""
    return await service.get_services(active_only=active_only)


@router.post("/services", response_model=ServiceResponse)
async def create_service(
    request: CreateServiceRequest,
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> ServiceResponse:
    """Create a new service."""
    try:
        result = await service.create_service(request)
        return ServiceResponse(success=True, message="Service created successfully", service=result)
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/services/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: UUID,
    request: UpdateServiceRequest,
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> ServiceResponse:
    """Update a service."""
    try:
        result = await service.update_service(service_id, request)
        return ServiceResponse(success=True, message="Service updated successfully", service=result)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/services/{service_id}/price", response_model=ServiceResponse)
async def update_service_price(
    service_id: UUID,
    request: UpdateServicePriceRequest,
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> ServiceResponse:
    """Update service price."""
    try:
        result = await service.update_service_price(service_id, request)
        return ServiceResponse(success=True, message="Price updated successfully", service=result)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/services/{service_id}", response_model=DeleteServiceResponse)
async def delete_service(
    service_id: UUID,
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> DeleteServiceResponse:
    """Delete a service."""
    try:
        return await service.delete_service(service_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ─── USER SERVICE MANAGEMENT ─────────────────────────────────────

@router.get("/users/{user_id}/services", response_model=UserServicesResponse)
async def get_user_services(
    user_id: UUID,
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> UserServicesResponse:
    """Get services for a specific user."""
    try:
        return await service.get_user_services(user_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/users/{user_id}/services/{service_id}", response_model=UpdateUserServiceResponse)
async def update_user_service(
    user_id: UUID,
    service_id: UUID,
    request: UpdateUserServiceRequest,
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> UpdateUserServiceResponse:
    """Update a user's service status."""
    try:
        return await service.update_user_service(user_id, service_id, request)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ─── ANALYTICS ────────────────────────────────────────────────────

@router.get("/analytics", response_model=AdminAnalyticsResponse)
async def get_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> AdminAnalyticsResponse:
    """Get analytics data."""
    return await service.get_analytics(days=days)


@router.get("/revenue", response_model=RevenueReportResponse)
async def get_revenue_report(
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> RevenueReportResponse:
    """Get revenue report."""
    return await service.get_revenue_report(start_date=start_date, end_date=end_date)


@router.get("/service-prices", response_model=ServicePricesResponse)
async def get_service_prices(
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> ServicePricesResponse:
    """Get all service prices."""
    return await service.get_service_prices()


# ─── SYSTEM STATUS ───────────────────────────────────────────────

@router.get("/status", response_model=AdminStatusResponse)
async def get_system_status(
    admin_user: dict = Depends(get_admin_user),
    service: AdminService = Depends(),
) -> AdminStatusResponse:
    """Get system status."""
    return await service.get_system_status()


@router.get("/health", response_model=AdminHealthResponse)
async def health_check() -> AdminHealthResponse:
    """Health check endpoint."""
    return AdminHealthResponse(
        status="healthy",
        service="admin",
        timestamp=datetime.utcnow(),
    )
