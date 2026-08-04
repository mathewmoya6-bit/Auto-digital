# app/modules/admin/schemas.py
# Auto-D Kenya - Admin Schemas
# ================================================================
# TYPE: MODULE - Admin Pydantic schemas

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from enum import Enum
from typing_extensions import Annotated

from pydantic import (
    BaseModel, 
    Field, 
    ConfigDict, 
    EmailStr, 
    field_validator,
    StringConstraints,
    PositiveFloat,
    NonNegativeInt,
)

# ─── BASE SCHEMAS ────────────────────────────────────────────────

class Schema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
        populate_by_name=True,
        use_enum_values=True,
    )


class Pagination(Schema):
    """Pagination fields."""
    total: NonNegativeInt = Field(..., description="Total items")
    limit: NonNegativeInt = Field(..., description="Items per page")
    offset: NonNegativeInt = Field(..., description="Pagination offset")


class SuccessResponse(Schema):
    """Generic success response."""
    success: bool = Field(True, description="Success status")
    message: str = Field("Success", description="Success message")


class DeleteResponse(Schema):
    """Generic delete response."""
    success: bool = Field(True, description="Success status")
    message: str = Field(..., description="Delete message")
    deleted_at: Optional[datetime] = Field(None, description="Deletion timestamp")


# ─── ENUMS ────────────────────────────────────────────────────────

class ServiceCode(str, Enum):
    """Service code enum."""
    VALUATION = "valuation"
    MILEAGE = "mileage"
    OWNERSHIP = "ownership"
    TCO = "tco"


class UserServiceStatus(str, Enum):
    """User service status enum."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Payment status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PAID = "paid"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ComponentStatus(str, Enum):
    """Component status enum."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


# ─── TYPE ALIASES ────────────────────────────────────────────────

Metadata = Dict[str, Any]
CurrencyCode = Annotated[str, StringConstraints(min_length=3, max_length=3)]


# ─── REQUEST SCHEMAS ──────────────────────────────────────────────

class UpdateServiceRequest(Schema):
    """Update service request."""
    name: Optional[str] = Field(None, description="Service name")
    price: Optional[PositiveFloat] = Field(None, description="Service price")
    currency: Optional[CurrencyCode] = Field("KES", description="Currency code")
    description: Optional[str] = Field(None, description="Service description")
    icon: Optional[str] = Field(None, description="Service icon")
    active: Optional[bool] = Field(None, description="Whether service is active")
    display_order: Optional[NonNegativeInt] = Field(None, description="Display order")

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: Optional[str]) -> Optional[str]:
        """Normalize currency to uppercase."""
        if v:
            return v.upper()
        return v


class UpdateServicePriceRequest(Schema):
    """Update service price request."""
    price: PositiveFloat = Field(..., description="Service price")
    currency: CurrencyCode = Field("KES", description="Currency code")

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: str) -> str:
        """Normalize currency to uppercase."""
        return v.upper()


class CreateServiceRequest(Schema):
    """Create service request."""
    code: ServiceCode = Field(..., description="Service code (unique)")
    name: str = Field(..., description="Service name")
    price: PositiveFloat = Field(..., description="Service price")
    currency: CurrencyCode = Field("KES", description="Currency code")
    description: Optional[str] = Field(None, description="Service description")
    icon: Optional[str] = Field(None, description="Service icon")
    active: bool = Field(True, description="Whether service is active")
    display_order: NonNegativeInt = Field(0, description="Display order")

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: str) -> str:
        """Normalize currency to uppercase."""
        return v.upper()


class UpdateUserServiceRequest(Schema):
    """Update user service request."""
    user_id: UUID = Field(..., description="User ID")
    service_id: UUID = Field(..., description="Service ID")
    status: UserServiceStatus = Field(..., description="Service status")


# ─── RESPONSE SCHEMAS ─────────────────────────────────────────────

class AdminStatsResponse(Schema):
    """Admin statistics response."""
    total_users: NonNegativeInt = Field(..., description="Total users")
    total_vehicles: NonNegativeInt = Field(..., description="Total vehicles")
    total_payments: NonNegativeInt = Field(..., description="Total payments")
    total_revenue: Decimal = Field(..., description="Total revenue")
    total_services_purchased: NonNegativeInt = Field(..., description="Total services purchased")
    new_users_this_week: NonNegativeInt = Field(..., description="New users this week")
    active_services: NonNegativeInt = Field(..., description="Active services")
    updated_at: datetime = Field(..., description="Last updated timestamp")
    error: Optional[str] = Field(None, description="Error message if any")


class AdminUserService(Schema):
    """User service item."""
    service_id: UUID = Field(..., description="Service ID")
    service_name: str = Field(..., description="Service name")
    service_code: ServiceCode = Field(..., description="Service code")
    status: UserServiceStatus = Field(..., description="Service status")


class AdminUser(Schema):
    """Admin user item."""
    id: UUID = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_sign_in_at: Optional[datetime] = Field(None, description="Last sign-in timestamp")
    confirmed_at: Optional[datetime] = Field(None, description="Confirmation timestamp")
    phone: Optional[str] = Field(None, description="Phone number")
    services: List[AdminUserService] = Field(default_factory=list, description="User services")


class AdminPayment(Schema):
    """Admin payment item."""
    id: UUID = Field(..., description="Payment ID")
    user_id: Optional[UUID] = Field(None, description="User ID")
    service_id: Optional[UUID] = Field(None, description="Service ID")
    service_name: Optional[str] = Field(None, description="Service name")
    service_code: Optional[ServiceCode] = Field(None, description="Service code")
    amount: Decimal = Field(..., description="Payment amount")
    currency: CurrencyCode = Field("KES", description="Currency code")
    status: PaymentStatus = Field(..., description="Payment status")
    phone: Optional[str] = Field(None, description="Phone number")
    checkout_request_id: Optional[str] = Field(None, description="Checkout request ID")
    mpesa_receipt: Optional[str] = Field(None, description="M-Pesa receipt")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


class AdminUserDetail(Schema):
    """Detailed admin user with payments."""
    id: UUID = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_sign_in_at: Optional[datetime] = Field(None, description="Last sign-in timestamp")
    confirmed_at: Optional[datetime] = Field(None, description="Confirmation timestamp")
    phone: Optional[str] = Field(None, description="Phone number")
    services: List[AdminUserService] = Field(default_factory=list, description="User services")
    app_metadata: Metadata = Field(default_factory=dict, description="App metadata")
    user_metadata: Metadata = Field(default_factory=dict, description="User metadata")
    payments: List[AdminPayment] = Field(default_factory=list, description="User payments")


class AdminUsersResponse(Pagination):
    """Admin users response."""
    users: List[AdminUser] = Field(..., description="List of users")


class AdminPaymentsResponse(Pagination):
    """Admin payments response."""
    payments: List[AdminPayment] = Field(..., description="List of payments")


class AdminVehicle(Schema):
    """Admin vehicle item."""
    id: UUID = Field(..., description="Vehicle ID")
    user_id: Optional[UUID] = Field(None, description="User ID")
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    year: Optional[int] = Field(None, description="Vehicle year")
    variant: Optional[str] = Field(None, description="Vehicle variant")
    verified: bool = Field(False, description="Verification status")
    created_at: datetime = Field(..., description="Creation timestamp")


class AdminVehiclesResponse(Pagination):
    """Admin vehicles response."""
    vehicles: List[AdminVehicle] = Field(..., description="List of vehicles")


# Renamed to avoid conflict with service class
class AdminServiceItem(Schema):
    """Admin service item."""
    id: UUID = Field(..., description="Service ID")
    code: ServiceCode = Field(..., description="Service code")
    name: str = Field(..., description="Service name")
    price: Decimal = Field(..., description="Service price")
    currency: CurrencyCode = Field("KES", description="Currency code")
    description: Optional[str] = Field(None, description="Service description")
    icon: Optional[str] = Field(None, description="Service icon")
    active: bool = Field(True, description="Whether service is active")
    display_order: NonNegativeInt = Field(0, description="Display order")
    purchase_count: NonNegativeInt = Field(0, description="Number of purchases")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last updated timestamp")


class AdminServicesResponse(Schema):
    """Admin services response."""
    services: List[AdminServiceItem] = Field(..., description="List of services")
    total: NonNegativeInt = Field(..., description="Total services")


class AnalyticsDay(Schema):
    """Analytics day item."""
    date: date = Field(..., description="Date")
    users: NonNegativeInt = Field(0, description="New users on this day")
    payments: NonNegativeInt = Field(0, description="Payments on this day")
    revenue: Decimal = Field(Decimal(0), description="Revenue on this day")
    vehicles: NonNegativeInt = Field(0, description="Vehicles added on this day")


class AnalyticsTotals(Schema):
    """Analytics totals."""
    users: NonNegativeInt = Field(..., description="Total users")
    payments: NonNegativeInt = Field(..., description="Total payments")
    revenue: Decimal = Field(..., description="Total revenue")
    vehicles: NonNegativeInt = Field(..., description="Total vehicles")


class AdminAnalyticsResponse(Schema):
    """Admin analytics response."""
    period_days: NonNegativeInt = Field(..., description="Period in days")
    start_date: date = Field(..., description="Start date")
    end_date: date = Field(..., description="End date")
    daily_stats: List[AnalyticsDay] = Field(..., description="Daily statistics")
    totals: AnalyticsTotals = Field(..., description="Total statistics")


class ComponentStatuses(Schema):
    """System component statuses."""
    supabase: ComponentStatus = Field(..., description="Supabase status")
    database: ComponentStatus = Field(..., description="Database status")
    mpesa: ComponentStatus = Field(..., description="M-Pesa status")


class AdminStatusResponse(Schema):
    """Admin system status response."""
    status: ComponentStatus = Field(..., description="Overall system status")
    timestamp: datetime = Field(..., description="Status timestamp")
    components: ComponentStatuses = Field(..., description="Component statuses")


class RevenueReportResponse(Schema):
    """Revenue report response."""
    total_revenue: Decimal = Field(..., description="Total revenue")
    total_transactions: NonNegativeInt = Field(..., description="Total transactions")
    revenue_by_service: Dict[str, Decimal] = Field(..., description="Revenue breakdown by service")
    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date")
    error: Optional[str] = Field(None, description="Error message if any")


class ServicePriceItem(Schema):
    """Service price item."""
    price: Decimal = Field(..., description="Service price")
    currency: CurrencyCode = Field("KES", description="Currency code")
    name: str = Field(..., description="Service name")


class ServicePricesResponse(Schema):
    """Service prices response."""
    prices: Dict[ServiceCode, ServicePriceItem] = Field(..., description="Service prices by code")
    services: List[AdminServiceItem] = Field(..., description="Full service list")
    total: NonNegativeInt = Field(..., description="Total services")


# ─── USER SERVICE RESPONSE ──────────────────────────────────────

class UserServiceItem(Schema):
    """User service item."""
    id: UUID = Field(..., description="User service ID")
    user_id: UUID = Field(..., description="User ID")
    service_id: UUID = Field(..., description="Service ID")
    status: UserServiceStatus = Field(..., description="Service status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last updated timestamp")
    # Use a separate field to avoid circular reference
    service_details: Optional[AdminServiceItem] = Field(None, description="Service details", alias="service")


class UserServicesResponse(Schema):
    """User services response."""
    user_id: UUID = Field(..., description="User ID")
    services: List[UserServiceItem] = Field(..., description="List of user services")
    total: NonNegativeInt = Field(..., description="Total services")


# ─── SERVICE RESPONSE SCHEMAS ────────────────────────────────────

class ServiceResponse(SuccessResponse):
    """Generic service response."""
    service: AdminServiceItem = Field(..., description="Service data")


# ─── DELETE RESPONSE SCHEMAS ────────────────────────────────────

class DeleteUserResponse(DeleteResponse):
    """Delete user response."""
    user_id: UUID = Field(..., description="Deleted user ID")


class DeleteServiceResponse(DeleteResponse):
    """Delete service response."""
    service_id: UUID = Field(..., description="Deleted service ID")


class UpdateUserServiceResponse(SuccessResponse):
    """Update user service response."""
    user_id: UUID = Field(..., description="User ID")
    service_id: UUID = Field(..., description="Service ID")
    status: UserServiceStatus = Field(..., description="Updated status")
    updated_at: datetime = Field(..., description="Update timestamp")


# ─── HEALTH RESPONSE ─────────────────────────────────────────────

class AdminHealthResponse(Schema):
    """Admin health response."""
    status: ComponentStatus = Field(..., description="Health status")
    service: str = Field("admin", description="Service name")
    timestamp: datetime = Field(..., description="Health check timestamp")


# ─── USER DETAIL RESPONSE ────────────────────────────────────────

class AdminUserDetailResponse(Schema):
    """Admin user detail response."""
    success: bool = Field(True, description="Success status")
    data: AdminUserDetail = Field(..., description="User details")


# ─── PAGINATED WRAPPER ──────────────────────────────────────────

class PaginatedResponse(Schema):
    """Generic paginated response wrapper."""
    items: List[Any] = Field(..., description="List of items")
    total: NonNegativeInt = Field(..., description="Total items")
    limit: NonNegativeInt = Field(..., description="Items per page")
    offset: NonNegativeInt = Field(..., description="Pagination offset")
    has_more: bool = Field(False, description="Whether there are more items")


# ─── FORWARD REFERENCES ──────────────────────────────────────────

# Resolve forward references - explicitly rebuild all models with potential circular refs
AdminUserDetail.model_rebuild()
AdminUserDetailResponse.model_rebuild()
UserServicesResponse.model_rebuild()
