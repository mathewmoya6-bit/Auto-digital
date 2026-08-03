# app/modules/admin/router.py

import logging
from datetime import datetime, UTC
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import require_admin
from app.modules.admin.service import AdminService
from app.modules.admin.schemas import (
    AdminAnalyticsResponse,
    AdminPaymentsResponse,
    AdminServicesResponse,
    AdminStatsResponse,
    AdminStatusResponse,
    AdminUsersResponse,
    AdminVehiclesResponse,
    CreateServiceRequest,
    RevenueReportResponse,
    ServicePricesResponse,
    UpdateServicePriceRequest,
    UpdateServiceRequest,
    UpdateUserServiceRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])
admin_service = AdminService()
