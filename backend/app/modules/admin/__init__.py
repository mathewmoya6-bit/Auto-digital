# app/modules/admin/__init__.py
# Auto-D Kenya - Admin Module
# ================================================================

"""Admin module for Auto-D Kenya.

This module provides administrative functions including:
- User management (list, view, delete)
- Payment management and reporting
- Service management (create, update, delete, price management)
- Platform analytics and statistics
- Revenue reporting
- System status monitoring
- User service access management
"""

from .router import router
from .service import AdminService
from .schemas import (
    # Request Schemas
    UpdateServiceRequest,
    UpdateServicePriceRequest,
    CreateServiceRequest,
    UpdateUserServiceRequest,
    
    # Response Schemas
    AdminStatsResponse,
    AdminUserItem,
    AdminUsersResponse,
    AdminPaymentItem,
    AdminPaymentsResponse,
    AdminVehicleItem,
    AdminVehiclesResponse,
    AdminServiceItem,
    AdminServicesResponse,
    AdminAnalyticsDay,
    AdminAnalyticsResponse,
    AdminStatusResponse,
    RevenueReportResponse,
    ServicePriceItem,
    ServicePricesResponse,
    UserServiceItem,
    UserServicesResponse,
    AdminHealthResponse,
)

__all__ = [
    # Router
    "router",
    
    # Service
    "AdminService",
    
    # Request Schemas
    "UpdateServiceRequest",
    "UpdateServicePriceRequest",
    "CreateServiceRequest",
    "UpdateUserServiceRequest",
    
    # Response Schemas
    "AdminStatsResponse",
    "AdminUserItem",
    "AdminUsersResponse",
    "AdminPaymentItem",
    "AdminPaymentsResponse",
    "AdminVehicleItem",
    "AdminVehiclesResponse",
    "AdminServiceItem",
    "AdminServicesResponse",
    "AdminAnalyticsDay",
    "AdminAnalyticsResponse",
    "AdminStatusResponse",
    "RevenueReportResponse",
    "ServicePriceItem",
    "ServicePricesResponse",
    "UserServiceItem",
    "UserServicesResponse",
    "AdminHealthResponse",
]

__version__ = "1.0.0"
__author__ = "Auto-D Kenya"
__description__ = "Admin module for vehicle intelligence platform"
