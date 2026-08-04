# app/modules/admin/schemas.py
# ================================================================
# Auto-D Kenya - Admin Schemas
# ================================================================
# TYPE: MODULE - Admin Pydantic schemas
# ================================================================

from datetime import datetime
from datetime import date as DateType
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ================================================================
# DASHBOARD & STATS
# ================================================================

class AdminStatsResponse(BaseModel):
    """Admin dashboard statistics response."""

    total_users: int = Field(0, description="Total number of users")
    total_vehicles: int = Field(0, description="Total number of vehicles")
    total_payments: int = Field(0, description="Total number of payments")
    total_revenue: Decimal = Field(Decimal(0), description="Total revenue from payments")
    total_services_purchased: int = Field(0, description="Total services purchased")
    new_users_this_week: int = Field(0, description="New users in the last 7 days")
    active_services: int = Field(0, description="Number of active services")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    error: Optional[str] = Field(None, description="Error message if any")


# ================================================================
# USER MANAGEMENT
# ================================================================

class AdminUser(BaseModel):
    """Admin user list item."""

    id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field("", description="User full name")
    created_at: datetime = Field(..., description="User creation timestamp")
    last_sign_in_at: Optional[datetime] = Field(None, description="Last sign-in timestamp")
    confirmed_at: Optional[datetime] = Field(None, description="Email confirmation timestamp")
    phone: Optional[str] = Field(None, description="User phone number")
    services: List[Dict[str, Any]] = Field(default_factory=list, description="User services")


class AdminUsersResponse(BaseModel):
    """Admin users list response."""

    users: List[AdminUser] = Field(default_factory=list, description="List of users")
    total: int = Field(0, description="Total number of users")
    limit: int = Field(20, description="Items per page")
    offset: int = Field(0, description="Items offset")


class AdminPayment(BaseModel):
    """Admin payment item."""

    id: UUID = Field(..., description="Payment ID")
    user_id: Optional[UUID] = Field(None, description="User ID")
    service_id: Optional[UUID] = Field(None, description="Service ID")
    service_name: Optional[str] = Field(None, description="Service name")
    service_code: Optional[str] = Field(None, description="Service code")
    amount: Decimal = Field(..., description="Payment amount")
    currency: str = Field("KES", description="Currency code")
    status: str = Field(..., description="Payment status")
    phone: Optional[str] = Field(None, description="Customer phone number")
    checkout_request_id: Optional[str] = Field(None, description="M-Pesa checkout request ID")
    mpesa_receipt: Optional[str] = Field(None, description="M-Pesa receipt number")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


class AdminUserDetail(BaseModel):
    """Detailed user information."""

    id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field("", description="User full name")
    created_at: datetime = Field(..., description="User creation timestamp")
    last_sign_in_at: Optional[datetime] = Field(None, description="Last sign-in timestamp")
    confirmed_at: Optional[datetime] = Field(None, description="Email confirmation timestamp")
    phone: Optional[str] = Field(None, description="User phone number")
    services: List[Dict[str, Any]] = Field(default_factory=list, description="User services")
    app_metadata: Dict[str, Any] = Field(default_factory=dict, description="App metadata")
    user_metadata: Dict[str, Any] = Field(default_factory=dict, description="User metadata")
    payments: List[AdminPayment] = Field(default_factory=list, description="User payments")


class AdminUserDetailResponse(BaseModel):
    """Admin user detail response wrapper."""

    success: bool = Field(True, description="Operation success status")
    data: AdminUserDetail = Field(..., description="User details")


class DeleteUserResponse(BaseModel):
    """Delete user response."""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation message")
    user_id: UUID = Field(..., description="Deleted user ID")
    deleted_at: datetime = Field(default_factory=datetime.utcnow, description="Deletion timestamp")


# ================================================================
# PAYMENT MANAGEMENT
# ================================================================

class AdminPaymentsResponse(BaseModel):
    """Admin payments list response."""

    payments: List[AdminPayment] = Field(default_factory=list, description="List of payments")
    total: int = Field(0, description="Total number of payments")
    limit: int = Field(20, description="Items per page")
    offset: int = Field(0, description="Items offset")


# ================================================================
# VEHICLE MANAGEMENT
# ================================================================

class AdminVehicle(BaseModel):
    """Admin vehicle item."""

    id: UUID = Field(..., description="Vehicle ID")
    user_id: Optional[UUID] = Field(None, description="User ID")
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    year: Optional[int] = Field(None, description="Vehicle year")
    variant: Optional[str] = Field(None, description="Vehicle variant")
    verified: bool = Field(False, description="Verification status")
    created_at: datetime = Field(..., description="Creation timestamp")


class AdminVehiclesResponse(BaseModel):
    """Admin vehicles list response."""

    vehicles: List[AdminVehicle] = Field(default_factory=list, description="List of vehicles")
    total: int = Field(0, description="Total number of vehicles")
    limit: int = Field(20, description="Items per page")
    offset: int = Field(0, description="Items offset")


# ================================================================
# SERVICE MANAGEMENT
# ================================================================

class AdminServiceItem(BaseModel):
    """Admin service item."""

    id: UUID = Field(..., description="Service ID")
    code: str = Field(..., description="Service code")
    name: str = Field(..., description="Service name")
    price: Decimal = Field(..., description="Service price")
    currency: str = Field("KES", description="Currency code")
    description: Optional[str] = Field(None, description="Service description")
    icon: Optional[str] = Field(None, description="Service icon")
    active: bool = Field(True, description="Service active status")
    display_order: int = Field(0, description="Display order")
    purchase_count: int = Field(0, description="Number of purchases")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class AdminServicesResponse(BaseModel):
    """Admin services list response."""

    services: List[AdminServiceItem] = Field(default_factory=list, description="List of services")
    total: int = Field(0, description="Total number of services")


class CreateServiceRequest(BaseModel):
    """Create service request."""

    code: str = Field(..., description="Service code")
    name: str = Field(..., description="Service name")
    price: Decimal = Field(..., gt=0, description="Service price")
    currency: str = Field("KES", description="Currency code")
    description: Optional[str] = Field(None, description="Service description")
    icon: Optional[str] = Field(None, description="Service icon")
    display_order: int = Field(0, description="Display order")
    active: bool = Field(True, description="Service active status")

    @field_validator('price')
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        return v


class UpdateServiceRequest(BaseModel):
    """Update service request."""

    name: Optional[str] = Field(None, description="Service name")
    description: Optional[str] = Field(None, description="Service description")
    icon: Optional[str] = Field(None, description="Service icon")
    active: Optional[bool] = Field(None, description="Service active status")
    display_order: Optional[int] = Field(None, description="Display order")


class UpdateServicePriceRequest(BaseModel):
    """Update service price request."""

    price: Decimal = Field(..., gt=0, description="New service price")
    currency: str = Field("KES", description="Currency code")

    @field_validator('price')
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        return v


class ServiceResponse(BaseModel):
    """Service operation response wrapper."""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation message")
    service: AdminServiceItem = Field(..., description="Service details")


class DeleteServiceResponse(BaseModel):
    """Delete service response."""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation message")
    service_id: UUID = Field(..., description="Deleted service ID")
    deleted_at: datetime = Field(default_factory=datetime.utcnow, description="Deletion timestamp")


# ================================================================
# USER SERVICE MANAGEMENT
# ================================================================

class UserServiceItem(BaseModel):
    """User service item."""

    id: UUID = Field(..., description="User service ID")
    user_id: UUID = Field(..., description="User ID")
    service_id: UUID = Field(..., description="Service ID")
    status: str = Field(..., description="Service status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    service_details: Optional[AdminServiceItem] = Field(None, description="Service details")


class UserServicesResponse(BaseModel):
    """User services response."""

    user_id: UUID = Field(..., description="User ID")
    services: List[UserServiceItem] = Field(default_factory=list, description="User services")
    total: int = Field(0, description="Total number of services")


class UpdateUserServiceRequest(BaseModel):
    """Update user service request."""

    status: str = Field(..., description="New service status")


class UpdateUserServiceResponse(BaseModel):
    """Update user service response."""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation message")
    user_id: UUID = Field(..., description="User ID")
    service_id: UUID = Field(..., description="Service ID")
    status: str = Field(..., description="Updated status")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")


# ================================================================
# ANALYTICS
# ================================================================

class AnalyticsDay(BaseModel):
    """Single day analytics data.

    NOTE: the `date` field was previously typed as `date` (i.e. field name
    == type name). During class construction, the class attribute
    `date = Field(...)` overwrites the name `date` in the class namespace,
    so when Pydantic resolves the string annotation "date" to build the
    schema, it resolves to the FieldInfo object instead of datetime.date.
    Pydantic then treats the field's type as itself a FieldInfo and tries
    to build/repr a schema for it -> infinite self-referential recursion.
    This is the root cause of the RecursionError. Fixed by importing the
    type under an alias (DateType) so the field name and type name never
    collide.
    """

    date: DateType = Field(..., description="Date")
    users: int = Field(0, description="New users")
    payments: int = Field(0, description="Payments count")
    revenue: Decimal = Field(Decimal(0), description="Revenue")
    vehicles: int = Field(0, description="New vehicles")


class AnalyticsTotals(BaseModel):
    """Analytics totals."""

    users: int = Field(0, description="Total users")
    payments: int = Field(0, description="Total payments")
    revenue: Decimal = Field(Decimal(0), description="Total revenue")
    vehicles: int = Field(0, description="Total vehicles")


class AdminAnalyticsResponse(BaseModel):
    """Admin analytics response."""

    period_days: int = Field(..., description="Number of days in period")
    start_date: DateType = Field(..., description="Period start date")
    end_date: DateType = Field(..., description="Period end date")
    daily_stats: List[AnalyticsDay] = Field(default_factory=list, description="Daily statistics")
    totals: AnalyticsTotals = Field(default_factory=AnalyticsTotals, description="Totals")


# ================================================================
# REVENUE REPORT
# ================================================================

class RevenueReportResponse(BaseModel):
    """Revenue report response."""

    total_revenue: Decimal = Field(Decimal(0), description="Total revenue")
    total_transactions: int = Field(0, description="Total transactions")
    revenue_by_service: Dict[str, Decimal] = Field(default_factory=dict, description="Revenue by service")
    start_date: Optional[datetime] = Field(None, description="Report start date")
    end_date: Optional[datetime] = Field(None, description="Report end date")
    error: Optional[str] = Field(None, description="Error message if any")


# ================================================================
# SERVICE PRICES
# ================================================================

class ServicePriceItem(BaseModel):
    """Service price item."""

    price: Decimal = Field(..., description="Service price")
    currency: str = Field("KES", description="Currency code")
    name: str = Field(..., description="Service name")


class ServicePricesResponse(BaseModel):
    """Service prices response."""

    prices: Dict[str, ServicePriceItem] = Field(default_factory=dict, description="Prices by service code")
    services: List[AdminServiceItem] = Field(default_factory=list, description="Services list")
    total: int = Field(0, description="Total number of services")


# ================================================================
# SYSTEM STATUS
# ================================================================

class ComponentStatuses(BaseModel):
    """Component statuses."""

    supabase: str = Field("unknown", description="Supabase status")
    database: str = Field("unknown", description="Database status")
    mpesa: str = Field("unknown", description="M-Pesa status")


class AdminStatusResponse(BaseModel):
    """Admin system status response."""

    status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Status timestamp")
    components: ComponentStatuses = Field(default_factory=ComponentStatuses, description="Component statuses")


# ================================================================
# HEALTH CHECK
# ================================================================

class AdminHealthResponse(BaseModel):
    """Admin health check response."""

    status: str = Field(..., description="Health status")
    service: str = Field("admin", description="Service name")
    version: str = Field("1.0", description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current timestamp")


# ================================================================
# SUCCESS RESPONSE
# ================================================================

class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")


# ================================================================
# PAGINATION
# ================================================================

class Pagination(BaseModel):
    """Pagination parameters."""

    page: int = Field(1, description="Current page")
    limit: int = Field(20, description="Items per page")
    total: int = Field(0, description="Total items")
    pages: int = Field(0, description="Total pages")


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    # Dashboard & Stats
    "AdminStatsResponse",

    # User Management
    "AdminUser",
    "AdminUsersResponse",
    "AdminPayment",
    "AdminUserDetailResponse",
    "AdminUserDetail",
    "DeleteUserResponse",

    # Payment Management
    "AdminPaymentsResponse",

    # Vehicle Management
    "AdminVehicle",
    "AdminVehiclesResponse",

    # Service Management
    "AdminServiceItem",
    "AdminServicesResponse",
    "CreateServiceRequest",
    "UpdateServiceRequest",
    "UpdateServicePriceRequest",
    "DeleteServiceResponse",
    "ServiceResponse",

    # User Service Management
    "UserServiceItem",
    "UserServicesResponse",
    "UpdateUserServiceRequest",
    "UpdateUserServiceResponse",

    # Analytics
    "AnalyticsDay",
    "AnalyticsTotals",
    "AdminAnalyticsResponse",

    # Revenue Report
    "RevenueReportResponse",

    # Service Prices
    "ServicePriceItem",
    "ServicePricesResponse",

    # System Status
    "ComponentStatuses",
    "AdminStatusResponse",

    # Health Check
    "AdminHealthResponse",

    # Success Response
    "SuccessResponse",

    # Pagination
    "Pagination",
]
