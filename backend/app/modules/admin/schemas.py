"""
Auto-D Kenya - Admin Schemas
================================================
Pydantic models for the Admin module.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------

class DashboardStats(BaseModel):
    total_users: int = 0
    active_users: int = 0
    total_payments: int = 0
    completed_payments: int = 0
    pending_payments: int = 0
    failed_payments: int = 0
    total_revenue: float = 0
    services_sold: int = 0


# ------------------------------------------------------------------
# Users
# ------------------------------------------------------------------

class UserSummary(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[datetime] = None
    active: bool = True


# ------------------------------------------------------------------
# Payments
# ------------------------------------------------------------------

class PaymentSummary(BaseModel):
    id: int
    user_id: str
    service_name: str
    amount: float
    status: str
    phone: str
    created_at: datetime


# ------------------------------------------------------------------
# Services
# ------------------------------------------------------------------

class ServiceSummary(BaseModel):
    id: int
    code: str
    name: str
    price: float
    active: bool


# ------------------------------------------------------------------
# Dashboard Response
# ------------------------------------------------------------------

class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_users: List[UserSummary] = []
    recent_payments: List[PaymentSummary] = []
