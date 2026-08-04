"""
Auto-D Kenya - Admin Schemas
================================================
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr


# ==========================================================
# Base
# ==========================================================

class Schema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )


# ==========================================================
# Dashboard
# ==========================================================

class DashboardResponse(Schema):
    total_users: int
    total_vehicles: int
    total_payments: int
    total_revenue: Decimal
    total_services_purchased: int
    active_services: int
    new_users_this_week: int
    updated_at: datetime
    error: Optional[str] = None


# ==========================================================
# Users
# ==========================================================

class UserResponse(Schema):
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[datetime] = None


class UsersResponse(Schema):
    users: List[UserResponse]
    total: int
    limit: int
    offset: int


# ==========================================================
# Payments
# ==========================================================

class PaymentResponse(Schema):
    id: str
    user_id: Optional[str] = None
    service_id: Optional[int] = None
    amount: Decimal
    currency: str = "KES"
    status: str
    phone: Optional[str] = None
    checkout_request_id: Optional[str] = None
    mpesa_receipt: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PaymentsResponse(Schema):
    payments: List[PaymentResponse]
    total: int
    limit: int
    offset: int


# ==========================================================
# Services
# ==========================================================

class ServiceResponse(Schema):
    id: int
    code: str
    name: str
    price: Decimal
    currency: str = "KES"
    description: Optional[str] = None
    icon: Optional[str] = None
    active: bool = True
    display_order: int = 0


class ServicesResponse(Schema):
    services: List[ServiceResponse]
    total: int


# ==========================================================
# Update Service
# ==========================================================

class UpdateServiceRequest(Schema):
    name: Optional[str] = None
    price: Optional[Decimal] = None
    currency: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    active: Optional[bool] = None
    display_order: Optional[int] = None


# ==========================================================
# Revenue Report
# ==========================================================

class RevenueReportResponse(Schema):
    total_revenue: Decimal
    total_transactions: int
    revenue_by_service: dict
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    error: Optional[str] = None


# ==========================================================
# Health
# ==========================================================

class HealthResponse(Schema):
    status: str
    service: str
    timestamp: datetime
    error: Optional[str] = None
