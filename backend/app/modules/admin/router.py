"""
Auto-D Kenya - Admin Router
================================================
TYPE: MODULE - Admin API Routes
"""

import logging

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_admin
from app.modules.admin.schemas import (
    AdminStatsResponse,
    AdminUsersResponse,
    AdminPaymentsResponse,
    AdminServicesResponse,
    AdminStatusResponse,
)
from app.modules.admin.service import AdminService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


def get_admin_service() -> AdminService:
    """
    Dependency for AdminService.
    Creates a fresh instance per request.
    """
    return AdminService()


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------

@router.get(
    "/dashboard",
    response_model=AdminStatsResponse,
    summary="Admin dashboard statistics",
)
async def dashboard(
    admin=Depends(get_current_admin),
    service: AdminService = Depends(get_admin_service),
):
    return await service.dashboard()


# ------------------------------------------------------------------
# Users
# ------------------------------------------------------------------

@router.get(
    "/users",
    response_model=AdminUsersResponse,
    summary="Get users",
)
async def get_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin=Depends(get_current_admin),
    service: AdminService = Depends(get_admin_service),
):
    return await service.get_users(
        limit=limit,
        offset=offset,
    )


# ------------------------------------------------------------------
# Payments
# ------------------------------------------------------------------

@router.get(
    "/payments",
    response_model=AdminPaymentsResponse,
    summary="Get payments",
)
async def get_payments(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin=Depends(get_current_admin),
    service: AdminService = Depends(get_admin_service),
):
    return await service.get_payments(
        limit=limit,
        offset=offset,
    )


# ------------------------------------------------------------------
# Services
# ------------------------------------------------------------------

@router.get(
    "/services",
    response_model=AdminServicesResponse,
    summary="Get services",
)
async def get_services(
    admin=Depends(get_current_admin),
    service: AdminService = Depends(get_admin_service),
):
    return await service.get_services()


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@router.get(
    "/health",
    response_model=AdminStatusResponse,
    summary="Admin module health",
)
async def health(
    service: AdminService = Depends(get_admin_service),
):
    return await service.health()
