# app/modules/admin/schemas.py
# Auto-D Kenya - Admin Schemas
# ================================================================
# TYPE: MODULE - Admin Pydantic schemas

from typing import Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ─── CONSTANTS ──────────────────────────────────────────────────

SERVICE_CODES = Literal["valuation", "mileage", "ownership", "tco"]
USER_SERVICE_STATUS = Literal["active", "suspended", "cancelled"]
PAYMENT_STATUS = Literal[
    "pending",
    "processing",
    "completed",
    "paid",
    "success",
    "failed",
    "cancelled",
    "expired"
]
COMPONENT_STATUS = Literal["healthy", "unhealthy", "degraded"]


# ─── REQUEST SCHEMAS ──────────────────────────────────────────────

class UpdateServiceRequest(BaseModel):
    """Update service request."""
    model_config = ConfigDict(from_attributes=True)
    
    name: str | None = Field(None, description="Service name", examples=["Vehicle Valuation"])
    price: float | None = Field(None, ge=0, description="Service price", examples=[500.0])
    currency: str | None = Field("KES", description="Currency code", examples=["KES", "USD"])
    description: str | None = Field(None, description="Service description", examples=["Get instant vehicle valuation"])
    icon: str | None = Field(None, description="Service icon", examples=["💰"])
    active: bool | None = Field(None, description="Whether service is active", examples=[True])
    display_order: int | None = Field(None, ge=0, description="Display order", examples=[1])


class UpdateServicePriceRequest(BaseModel):
    """Update service price request."""
    model_config = ConfigDict(from_attributes=True)
    
    price: float = Field(..., gt=0, description="Service price", examples=[500.0])
    currency: str = Field("KES", description="Currency code", examples=["KES"])


class CreateServiceRequest(BaseModel):
    """Create service request."""
    model_config = ConfigDict(from_attributes=True)
    
    code: str = Field(..., description="Service code (unique)", examples=["valuation"])
    name: str = Field(..., description="Service name", examples=["Vehicle Valuation"])
    price: float = Field(..., gt=0, description="Service price", examples=[500.0])
    currency: str = Field("KES", description="Currency code", examples=["KES"])
    description: str | None = Field(None, description="Service description", examples=["Get instant vehicle valuation"])
    icon: str | None = Field(None, description="Service icon", examples=["💰"])
    active: bool = Field(True, description="Whether service is active")
    display_order: int = Field(0, ge=0, description="Display order", examples=[1])


class UpdateUserServiceRequest(BaseModel):
    """Update user service request."""
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str = Field(..., description="User ID", examples=["abc-123-def-456"])
    service_id: str = Field(..., description="Service ID", examples=["123e4567-e89b-12d3-a456-426614174000"])
    status: USER_SERVICE_STATUS = Field(..., description="Service status", examples=["active"])


# ─── RESPONSE SCHEMAS ─────────────────────────────────────────────

class AdminStatsResponse(BaseModel):
    """Admin statistics response."""
    model_config = ConfigDict(from_attributes=True)
    
    total_users: int = Field(..., description="Total users")
    total_vehicles: int = Field(..., description="Total vehicles")
    total_payments: int = Field(..., description="Total payments")
    total_revenue: float = Field(..., description="Total revenue")
    total_services_purchased: int = Field(..., description="Total services purchased")
    new_users_this_week: int = Field(..., description="New users this week")
    active_services: int = Field(..., description="Active services")
    updated_at: datetime = Field(..., description="Last updated timestamp")
    error: str | None = Field(None, description="Error message if any")


class AdminUserService(BaseModel):
    """User service item."""
    model_config = ConfigDict(from_attributes=True)
    
    service_id: str = Field(..., description="Service ID")
    service_name: str = Field(..., description="Service name")
    service_code: str = Field(..., description="Service code")
    status: USER_SERVICE_STATUS = Field(..., description="Service status")


class AdminUser(BaseModel):
    """Admin user item."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_sign_in_at: datetime | None = Field(None, description="Last sign-in timestamp")
    confirmed_at: datetime | None = Field(None, description="Confirmation timestamp")
    phone: str | None = Field(None, description="Phone number")
    services: list[AdminUserService] = Field(default_factory=list, description="User services")


class AdminPayment(BaseModel):
    """Admin payment item."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="Payment ID")
    user_id: str | None = Field(None, description="User ID")
    service_id: str | None = Field(None, description="Service ID")
    service_name: str | None = Field(None, description="Service name")
    service_code: str | None = Field(None, description="Service code")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field("KES", description="Currency code")
    status: PAYMENT_STATUS = Field(..., description="Payment status")
    phone: str | None = Field(None, description="Phone number")
    checkout_request_id: str | None = Field(None, description="Checkout request ID")
    mpesa_receipt: str | None = Field(None, description="M-Pesa receipt")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")


class AdminUserDetail(AdminUser):
    """Detailed admin user with payments."""
    model_config = ConfigDict(from_attributes=True)
    
    app_metadata: dict[str, Any] = Field(default_factory=dict, description="App metadata")
    user_metadata: dict[str, Any] = Field(default_factory=dict, description="User metadata")
    payments: list[AdminPayment] = Field(default_factory=list, description="User payments")


class AdminUsersResponse(BaseModel):
    """Admin users response."""
    model_config = ConfigDict(from_attributes=True)
    
    users: list[AdminUser] = Field(..., description="List of users")
    total: int = Field(..., description="Total users")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


class AdminPaymentsResponse(BaseModel):
    """Admin payments response."""
    model_config = ConfigDict(from_attributes=True)
    
    payments: list[AdminPayment] = Field(..., description="List of payments")
    total: int = Field(..., description="Total payments")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


class AdminVehicle(BaseModel):
    """Admin vehicle item."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="Vehicle ID")
    user_id: str | None = Field(None, description="User ID")
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    year: int | None = Field(None, description="Vehicle year")
    variant: str | None = Field(None, description="Vehicle variant")
    verified: bool = Field(False, description="Verification status")
    created_at: datetime = Field(..., description="Creation timestamp")


class AdminVehiclesResponse(BaseModel):
    """Admin vehicles response."""
    model_config = ConfigDict(from_attributes=True)
    
    vehicles: list[AdminVehicle] = Field(..., description="List of vehicles")
    total: int = Field(..., description="Total vehicles")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


class AdminService(BaseModel):
    """Admin service item."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="Service ID")
    code: str = Field(..., description="Service code")
    name: str = Field(..., description="Service name")
    price: float = Field(..., description="Service price")
    currency: str = Field("KES", description="Currency code")
    description: str | None = Field(None, description="Service description")
    icon: str | None = Field(None, description="Service icon")
    active: bool = Field(True, description="Whether service is active")
    display_order: int = Field(0, description="Display order")
    purchase_count: int = Field(0, description="Number of purchases")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last updated timestamp")


class AdminServicesResponse(BaseModel):
    """Admin services response."""
    model_config = ConfigDict(from_attributes=True)
    
    services: list[AdminService] = Field(..., description="List of services")
    total: int = Field(..., description="Total services")


class AnalyticsDay(BaseModel):
    """Analytics day item."""
    model_config = ConfigDict(from_attributes=True)
    
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    users: int = Field(0, description="New users on this day")
    payments: int = Field(0, description="Payments on this day")
    revenue: float = Field(0, description="Revenue on this day")
    vehicles: int = Field(0, description="Vehicles added on this day")


class AnalyticsTotals(BaseModel):
    """Analytics totals."""
    model_config = ConfigDict(from_attributes=True)
    
    users: int = Field(..., description="Total users")
    payments: int = Field(..., description="Total payments")
    revenue: float = Field(..., description="Total revenue")
    vehicles: int = Field(..., description="Total vehicles")


class AdminAnalyticsResponse(BaseModel):
    """Admin analytics response."""
    model_config = ConfigDict(from_attributes=True)
    
    period_days: int = Field(..., description="Period in days")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    daily_stats: list[AnalyticsDay] = Field(..., description="Daily statistics")
    totals: AnalyticsTotals = Field(..., description="Total statistics")


class ComponentStatus(BaseModel):
    """System component status."""
    model_config = ConfigDict(from_attributes=True)
    
    supabase: COMPONENT_STATUS = Field(..., description="Supabase status")
    database: COMPONENT_STATUS = Field(..., description="Database status")
    mpesa: COMPONENT_STATUS = Field(..., description="M-Pesa status")


class AdminStatusResponse(BaseModel):
    """Admin system status response."""
    model_config = ConfigDict(from_attributes=True)
    
    status: Literal["healthy", "degraded"] = Field(..., description="Overall system status")
    timestamp: datetime = Field(..., description="Status timestamp")
    components: ComponentStatus = Field(..., description="Component statuses")


class RevenueReportResponse(BaseModel):
    """Revenue report response."""
    model_config = ConfigDict(from_attributes=True)
    
    total_revenue: float = Field(..., description="Total revenue")
    total_transactions: int = Field(..., description="Total transactions")
    revenue_by_service: dict[str, float] = Field(..., description="Revenue breakdown by service")
    start_date: str | None = Field(None, description="Start date (ISO format)")
    end_date: str | None = Field(None, description="End date (ISO format)")
    error: str | None = Field(None, description="Error message if any")


class ServicePriceItem(BaseModel):
    """Service price item."""
    model_config = ConfigDict(from_attributes=True)
    
    price: float = Field(..., description="Service price")
    currency: str = Field("KES", description="Currency code")
    name: str = Field(..., description="Service name")


class ServicePricesResponse(BaseModel):
    """Service prices response."""
    model_config = ConfigDict(from_attributes=True)
    
    prices: dict[str, ServicePriceItem] = Field(..., description="Service prices by code")
    services: list[AdminService] = Field(..., description="Full service list")
    total: int = Field(..., description="Total services")


# ─── USER SERVICE RESPONSE ──────────────────────────────────────

class UserServiceItem(BaseModel):
    """User service item."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="User service ID")
    user_id: str = Field(..., description="User ID")
    service_id: str = Field(..., description="Service ID")
    status: USER_SERVICE_STATUS = Field(..., description="Service status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last updated timestamp")
    service: AdminService | None = Field(None, description="Service details")


class UserServicesResponse(BaseModel):
    """User services response."""
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str = Field(..., description="User ID")
    services: list[UserServiceItem] = Field(..., description="List of user services")
    total: int = Field(..., description="Total services")


# ─── GENERIC RESPONSE SCHEMAS ────────────────────────────────────

class SuccessResponse(BaseModel):
    """Generic success response."""
    model_config = ConfigDict(from_attributes=True)
    
    success: bool = Field(True, description="Success status")
    message: str = Field("Success", description="Success message")


class DeleteResponse(BaseModel):
    """Delete response."""
    model_config = ConfigDict(from_attributes=True)
    
    success: bool = Field(True, description="Success status")
    message: str = Field(..., description="Delete message")
    id: str | int | None = Field(None, description="Deleted entity ID")
    deleted_at: datetime | None = Field(None, description="Deletion timestamp")


class CreateServiceResponse(SuccessResponse):
    """Create service response."""
    model_config = ConfigDict(from_attributes=True)
    
    service: AdminService = Field(..., description="Created service")


class UpdateServiceResponse(SuccessResponse):
    """Update service response."""
    model_config = ConfigDict(from_attributes=True)
    
    service: AdminService = Field(..., description="Updated service")


class UpdateServicePriceResponse(SuccessResponse):
    """Update service price response."""
    model_config = ConfigDict(from_attributes=True)
    
    service: AdminService = Field(..., description="Updated service")


class UpdateUserServiceResponse(SuccessResponse):
    """Update user service response."""
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str = Field(..., description="User ID")
    service_id: str = Field(..., description="Service ID")
    status: USER_SERVICE_STATUS = Field(..., description="Updated status")
    updated_at: datetime = Field(..., description="Update timestamp")


class DeleteUserResponse(DeleteResponse):
    """Delete user response."""
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str = Field(..., description="Deleted user ID")


class DeleteServiceResponse(DeleteResponse):
    """Delete service response."""
    model_config = ConfigDict(from_attributes=True)
    
    service_id: str = Field(..., description="Deleted service ID")


# ─── HEALTH RESPONSE ─────────────────────────────────────────────

class AdminHealthResponse(BaseModel):
    """Admin health response."""
    model_config = ConfigDict(from_attributes=True)
    
    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Health status")
    service: str = Field("admin", description="Service name")
    timestamp: datetime = Field(..., description="Health check timestamp")


# ─── USER DETAIL RESPONSE ────────────────────────────────────────

class AdminUserDetailResponse(BaseModel):
    """Admin user detail response."""
    model_config = ConfigDict(from_attributes=True)
    
    success: bool = Field(True, description="Success status")
    data: AdminUserDetail = Field(..., description="User details")
