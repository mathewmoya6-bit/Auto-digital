# app/modules/admin/router.py

import logging
from datetime import datetime
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import require_admin
from app.modules.admin.service import AdminService
from app.modules.admin.schemas import (
    AdminAnalyticsResponse,
    AdminHealthResponse,
    AdminPaymentsResponse,
    AdminServicesResponse,
    AdminStatsResponse,
    AdminStatusResponse,
    AdminUserDetailResponse,
    AdminUsersResponse,
    AdminVehiclesResponse,
    CreateServiceRequest,
    DeleteServiceResponse,
    DeleteUserResponse,
    RevenueReportResponse,
    ServicePricesResponse,
    ServiceResponse,
    UpdateServicePriceRequest,
    UpdateServiceRequest,
    UpdateUserServiceRequest,
    UpdateUserServiceResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)

service = AdminService()

# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------


@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats():
    return await service.get_stats()


@router.get("/analytics", response_model=AdminAnalyticsResponse)
async def get_analytics(
    days: int = Query(30, ge=1, le=365),
):
    return await service.get_platform_analytics(days)


@router.get("/status", response_model=AdminStatusResponse)
async def get_status():
    return await service.get_system_status()


@router.get("/health", response_model=AdminHealthResponse)
async def health():
    return {
        "status": "healthy",
        "service": "admin",
        "timestamp": datetime.utcnow(),
    }


# ------------------------------------------------------------------
# Users
# ------------------------------------------------------------------


@router.get("/users", response_model=AdminUsersResponse)
async def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
):
    return await service.get_users(limit, offset, search)


@router.get(
    "/users/{user_id}",
    response_model=AdminUserDetailResponse,
)
async def get_user(user_id: UUID):
    return {
        "success": True,
        "data": await service.get_user_by_id(str(user_id)),
    }


@router.delete(
    "/users/{user_id}",
    response_model=DeleteUserResponse,
)
async def delete_user(user_id: UUID):
    return await service.delete_user(str(user_id))


# ------------------------------------------------------------------
# Payments
# ------------------------------------------------------------------


@router.get(
    "/payments",
    response_model=AdminPaymentsResponse,
)
async def payments(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
):
    return await service.get_all_payments(
        limit=limit,
        offset=offset,
        status=status,
    )


# ------------------------------------------------------------------
# Vehicles
# ------------------------------------------------------------------


@router.get(
    "/vehicles",
    response_model=AdminVehiclesResponse,
)
async def vehicles(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    verified: Optional[bool] = None,
):
    return await service.get_all_vehicles(
        limit=limit,
        offset=offset,
        verified=verified,
    )


# ------------------------------------------------------------------
# Services
# ------------------------------------------------------------------


@router.get(
    "/services",
    response_model=AdminServicesResponse,
)
async def services():
    return await service.get_all_services()


@router.post(
    "/services",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_service(
    request: CreateServiceRequest,
):
    return await service.create_service(
        request.model_dump(exclude_none=True)
    )


@router.put(
    "/services/{service_id}",
    response_model=ServiceResponse,
)
async def update_service(
    service_id: UUID,
    request: UpdateServiceRequest,
):
    return await service.update_service(
        str(service_id),
        request.model_dump(exclude_none=True),
    )


@router.delete(
    "/services/{service_id}",
    response_model=DeleteServiceResponse,
)
async def delete_service(service_id: UUID):
    return await service.delete_service(str(service_id))


# ------------------------------------------------------------------
# Service Prices
# ------------------------------------------------------------------


@router.get(
    "/service-prices",
    response_model=ServicePricesResponse,
)
async def service_prices():
    return await service.get_service_prices()


@router.put(
    "/service-prices/{service_code}",
    response_model=ServiceResponse,
)
async def update_service_price(
    service_code: str,
    request: UpdateServicePriceRequest,
):
    return await service.update_service_price(
        service_code=service_code,
        price=float(request.price),
        currency=request.currency,
    )


# ------------------------------------------------------------------
# User Services
# ------------------------------------------------------------------


@router.put(
    "/user-services",
    response_model=UpdateUserServiceResponse,
)
async def update_user_service(
    request: UpdateUserServiceRequest,
):
    return await service.update_user_service(
        user_id=str(request.user_id),
        service_id=str(request.service_id),
        status=request.status,
    )


# ------------------------------------------------------------------
# Reports
# ------------------------------------------------------------------


@router.get(
    "/revenue-report",
    response_model=RevenueReportResponse,
)
async def revenue_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    return await service.get_revenue_report(
        start_date=start_date,
        end_date=end_date,
    )
