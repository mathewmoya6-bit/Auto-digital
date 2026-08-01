# app/modules/admin/schemas.py
# Auto-D Kenya - Admin Schemas
# ================================================================
# TYPE: MODULE - Admin Pydantic schemas

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# ─── REQUEST SCHEMAS ──────────────────────────────────────────────

class UpdateServiceRequest(BaseModel):
    """Update service request."""
    name: Optional[str] = Field(None, description="Service name")
    price: Optional[float] = Field(None, description="Service price", ge=0)
    currency: Optional[str] = Field("KES", description="Currency code")
    description: Optional[str] = Field(None, description="Service description")
    icon: Optional[str] = Field(None, description="Service icon")
    active: Optional[bool] = Field(None, description="Whether service is active")
    display_order: Optional[int] = Field(None, description="Display order")


class UpdateServicePriceRequest(BaseModel):
    """Update service price request."""
    price: float = Field(..., description="Service price", ge=0)
    currency: str = Field("KES", description="Currency code")


class CreateServiceRequest(BaseModel):
    """Create service request."""
    code: str = Field(..., description="Service code (unique)")
    name: str = Field(..., description="Service name")
    price: float = Field(..., description="Service price", ge=0)
    currency: str = Field("KES", description="Currency code")
    description: Optional[str] = Field(None, description="Service description")
    icon: Optional[str] = Field(None, description="Service icon")
    active: bool = Field(True, description="Whether service is active")
    display_order: int = Field(0, description="Display order")
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        allowed = ["valuation", "mileage", "ownership", "tco"]
        if v not in allowed:
            raise ValueError(f"Service code must be one of: {', '.join(allowed)}")
        return v


class UpdateUserServiceRequest(BaseModel):
    """Update user service request."""
    user_id: str = Field(..., description="User ID")
    service_id: str = Field(..., description="Service ID")
    status: str = Field(..., description="Status: active, suspended, cancelled")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = ["active", "suspended", "cancelled"]
        if v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v


# ─── RESPONSE SCHEMAS ─────────────────────────────────────────────

class AdminStatsResponse(BaseModel):
    """Admin statistics response."""
    total_users: int = Field(..., description="Total users")
    total_vehicles: int = Field(..., description="Total vehicles")
    total_payments: int = Field(..., description="Total payments")
    total_revenue: float = Field(..., description="Total revenue")
    total_services_purchased: int = Field(..., description="Total services purchased")
    new_users_this_week: int = Field(..., description="New users this week")
    active_services: int = Field(..., description="Active services")
    updated_at: str = Field(..., description="Last updated timestamp")
    error: Optional[str] = Field(None, description="Error message if any")


class AdminUserItem(BaseModel):
    """Admin user item."""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    created_at: str = Field(..., description="Creation timestamp")
    last_sign_in_at: Optional[str] = Field(None, description="Last sign-in timestamp")
    confirmed_at: Optional[str] = Field(None, description="Confirmation timestamp")
    phone: Optional[str] = Field(None, description="Phone number")
    services: List[Dict[str, Any]] = Field(default_factory=list, description="User services")


class AdminUsersResponse(BaseModel):
    """Admin users response."""
    users: List[AdminUserItem] = Field(..., description="List of users")
    total: int = Field(..., description="Total users")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


class AdminPaymentItem(BaseModel):
    """Admin payment item."""
    id: str = Field(..., description="Payment ID")
    user_id: Optional[str] = Field(None, description="User ID")
    service_id: Optional[str] = Field(None, description="Service ID")
    service_name: Optional[str] = Field(None, description="Service name")
    service_code: Optional[str] = Field(None, description="Service code")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field("KES", description="Currency code")
    status: str = Field(..., description="Payment status")
    phone: Optional[str] = Field(None, description="Phone number")
    checkout_request_id: Optional[str] = Field(None, description="Checkout request ID")
    mpesa_receipt: Optional[str] = Field(None, description="M-Pesa receipt")
    created_at: str = Field(..., description="Creation timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")


class AdminPaymentsResponse(BaseModel):
    """Admin payments response."""
    payments: List[AdminPaymentItem] = Field(..., description="List of payments")
    total: int = Field(..., description="Total payments")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


class AdminVehicleItem(BaseModel):
    """Admin vehicle item."""
    id: str = Field(..., description="Vehicle ID")
    user_id: Optional[str] = Field(None, description="User ID")
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    year: Optional[int] = Field(None, description="Vehicle year")
    variant: Optional[str] = Field(None, description="Vehicle variant")
    verified: bool = Field(False, description="Verification status")
    created_at: str = Field(..., description="Creation timestamp")


class AdminVehiclesResponse(BaseModel):
    """Admin vehicles response."""
    vehicles: List[AdminVehicleItem] = Field(..., description="List of vehicles")
    total: int = Field(..., description="Total vehicles")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


class AdminServiceItem(BaseModel):
    """Admin service item."""
    id: int = Field(..., description="Service ID")
    code: str = Field(..., description="Service code")
    name: str = Field(..., description="Service name")
    price: float = Field(..., description="Service price")
    currency: str = Field("KES", description="Currency code")
    description: Optional[str] = Field(None, description="Service description")
    icon: Optional[str] = Field(None, description="Service icon")
    active: bool = Field(True, description="Whether service is active")
    display_order: int = Field(0, description="Display order")
    purchase_count: int = Field(0, description="Number of purchases")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last updated timestamp")


class AdminServicesResponse(BaseModel):
    """Admin services response."""
    services: List[AdminServiceItem] = Field(..., description="List of services")
    total: int = Field(..., description="Total services")


class AdminAnalyticsDay(BaseModel):
    """Analytics day item."""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    users: int = Field(0, description="New users on this day")
    payments: int = Field(0, description="Payments on this day")
    revenue: float = Field(0, description="Revenue on this day")
    vehicles: int = Field(0, description="Vehicles added on this day")


class AdminAnalyticsResponse(BaseModel):
    """Admin analytics response."""
    period_days: int = Field(..., description="Period in days")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    daily_stats: List[AdminAnalyticsDay] = Field(..., description="Daily statistics")
    totals: Dict[str, Any] = Field(..., description="Total statistics")


class AdminStatusResponse(BaseModel):
    """Admin system status response."""
    status: str = Field(..., description="Overall system status (healthy, degraded)")
    timestamp: str = Field(..., description="Status timestamp")
    components: Dict[str, str] = Field(..., description="Component statuses (healthy/unhealthy)")


class RevenueReportResponse(BaseModel):
    """Revenue report response."""
    total_revenue: float = Field(..., description="Total revenue")
    total_transactions: int = Field(..., description="Total transactions")
    revenue_by_service: Dict[str, float] = Field(..., description="Revenue breakdown by service")
    start_date: Optional[str] = Field(None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(None, description="End date (ISO format)")
    error: Optional[str] = Field(None, description="Error message if any")


class ServicePriceItem(BaseModel):
    """Service price item."""
    price: float = Field(..., description="Service price")
    currency: str = Field("KES", description="Currency code")
    name: str = Field(..., description="Service name")


class ServicePricesResponse(BaseModel):
    """Service prices response."""
    prices: Dict[str, ServicePriceItem] = Field(..., description="Service prices by code")
    services: List[Dict[str, Any]] = Field(..., description="Full service list")
    total: int = Field(..., description="Total services")


# ─── USER SERVICE RESPONSE ──────────────────────────────────────

class UserServiceItem(BaseModel):
    """User service item."""
    id: int = Field(..., description="User service ID")
    user_id: str = Field(..., description="User ID")
    service_id: str = Field(..., description="Service ID")
    status: str = Field(..., description="Service status")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last updated timestamp")
    service: Optional[AdminServiceItem] = Field(None, description="Service details")


class UserServicesResponse(BaseModel):
    """User services response."""
    user_id: str = Field(..., description="User ID")
    services: List[UserServiceItem] = Field(..., description="List of user services")
    total: int = Field(..., description="Total services")


# ─── HEALTH RESPONSE ─────────────────────────────────────────────

class AdminHealthResponse(BaseModel):
    """Admin health response."""
    status: str = Field(..., description="Health status")
    service: str = Field("admin", description="Service name")
    timestamp: str = Field(..., description="Health check timestamp")
