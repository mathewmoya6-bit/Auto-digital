# app/modules/admin/schemas.py
# Auto-D Kenya - Admin Schemas
# ================================================================

from typing import Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ─── CONSTANTS ──────────────────────────────────────────────────

SERVICE_CODES = Literal["valuation", "mileage", "ownership", "tco"]
USER_SERVICE_STATUS = Literal["active", "suspended", "cancelled"]
PAYMENT_STATUS = Literal["pending", "processing", "completed", "paid", "success", "failed", "cancelled", "expired"]
COMPONENT_STATUS = Literal["healthy", "unhealthy", "degraded"]


# ─── REQUEST SCHEMAS ──────────────────────────────────────────────

class UpdateServiceRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str | None = Field(None, description="Service name")
    price: float | None = Field(None, ge=0, description="Service price")
    currency: str | None = Field("KES", description="Currency code")
    description: str | None = Field(None, description="Service description")
    icon: str | None = Field(None, description="Service icon")
    active: bool | None = Field(None, description="Whether service is active")
    display_order: int | None = Field(None, ge=0, description="Display order")


class UpdateServicePriceRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    price: float = Field(..., gt=0, description="Service price")
    currency: str = Field("KES", description="Currency code")


class CreateServiceRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str = Field(..., description="Service code")
    name: str = Field(..., description="Service name")
    price: float = Field(..., gt=0, description="Service price")
    currency: str = Field("KES", description="Currency code")
    description: str | None = Field(None, description="Service description")
    icon: str | None = Field(None, description="Service icon")
    active: bool = Field(True, description="Whether service is active")
    display_order: int = Field(0, ge=0, description="Display order")


class UpdateUserServiceRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: str = Field(..., description="User ID")
    service_id: str = Field(..., description="Service ID")
    status: USER_SERVICE_STATUS = Field(..., description="Service status")


# ─── RESPONSE SCHEMAS ─────────────────────────────────────────────

class AdminStatsResponse(BaseModel):
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
    model_config = ConfigDict(from_attributes=True)
    service_id: str = Field(..., description="Service ID")
    service_name: str = Field(..., description="Service name")
    service_code: str = Field(..., description="Service code")
    status: USER_SERVICE_STATUS = Field(..., description="Service status")


class AdminPayment(BaseModel):
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


class AdminUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_sign_in_at: datetime | None = Field(None, description="Last sign-in timestamp")
    confirmed_at: datetime | None = Field(None, description="Confirmation timestamp")
    phone: str | None = Field(None, description="Phone number")
    services: list[AdminUserService] = Field(default_factory=list, description="User services")


class AdminUserDetail(BaseModel):
    """No inheritance - flat structure to avoid recursion"""
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_sign_in_at: datetime | None = Field(None, description="Last sign-in timestamp")
    confirmed_at: datetime | None = Field(None, description="Confirmation timestamp")
    phone: str | None = Field(None, description="Phone number")
    services: list[AdminUserService] = Field(default_factory=list, description="User services")
    app_metadata: dict[str, Any] = Field(default_factory=dict, description="App metadata")
    user_metadata: dict[str, Any] = Field(default_factory=dict, description="User metadata")
    payments: list[AdminPayment] = Field(default_factory=list, description="User payments")


class AdminUsersResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    users: list[AdminUser] = Field(..., description="List of users")
    total: int = Field(..., description="Total users")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


class AdminPaymentsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    payments: list[AdminPayment] = Field(..., description="List of payments")
    total: int = Field(..., description="Total payments")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


class AdminVehicle(BaseModel):
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
    model_config = ConfigDict(from_attributes=True)
    vehicles: list[AdminVehicle] = Field(..., description="List of vehicles")
    total: int = Field(..., description="Total vehicles")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


class AdminService(BaseModel):
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
    model_config = ConfigDict(from_attributes=True)
    services: list[AdminService] = Field(..., description="List of services")
    total: int = Field(..., description="Total services")


class AnalyticsDay(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    users: int = Field(0, description="New users on this day")
    payments: int = Field(0, description="Payments on this day")
    revenue: float = Field(0, description="Revenue on this day")
    vehicles: int = Field(0, description="Vehicles added on this day")


class AnalyticsTotals(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    users: int = Field(..., description="Total users")
    payments: int = Field(..., description="Total payments")
    revenue: float = Field(..., description="Total revenue")
    vehicles: int = Field(..., description="Total vehicles")


class AdminAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    period_days: int = Field(..., description="Period in days")
    start_date: str = Field(..., description="Start date")
    end_date: str = Field(..., description="End date")
    daily_stats: list[AnalyticsDay] = Field(..., description="Daily statistics")
    totals: AnalyticsTotals = Field(..., description="Total statistics")


class ComponentStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    supabase: COMPONENT_STATUS = Field(..., description="Supabase status")
    database: COMPONENT_STATUS = Field(..., description="Database status")
    mpesa: COMPONENT_STATUS = Field(..., description="M-Pesa status")


class AdminStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: Literal["healthy", "degraded"] = Field(..., description="Overall system status")
    timestamp: datetime = Field(..., description="Status timestamp")
    components: ComponentStatus = Field(..., description="Component statuses")


class RevenueReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_revenue: float = Field(..., description="Total revenue")
    total_transactions: int = Field(..., description="Total transactions")
    revenue_by_service: dict[str, float] = Field(..., description="Revenue breakdown")
    start_date: str | None = Field(None, description="Start date")
    end_date: str | None = Field(None, description="End date")
    error: str | None = Field(None, description="Error message if any")


class ServicePriceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    price: float = Field(..., description="Service price")
    currency: str = Field("KES", description="Currency code")
    name: str = Field(..., description="Service name")


class ServicePricesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    prices: dict[str, ServicePriceItem] = Field(..., description="Service prices by code")
    services: list[AdminService] = Field(..., description="Full service list")
    total: int = Field(..., description="Total services")


class UserServiceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(..., description="User service ID")
    user_id: str = Field(..., description="User ID")
    service_id: str = Field(..., description="Service ID")
    status: USER_SERVICE_STATUS = Field(..., description="Service status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last updated timestamp")
    service: AdminService | None = Field(None, description="Service details")


class UserServicesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: str = Field(..., description="User ID")
    services: list[UserServiceItem] = Field(..., description="List of user services")
    total: int = Field(..., description="Total services")


class SuccessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    success: bool = Field(True, description="Success status")
    message: str = Field("Success", description="Success message")


class DeleteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    success: bool = Field(True, description="Success status")
    message: str = Field(..., description="Delete message")
    id: str | int | None = Field(None, description="Deleted entity ID")
    deleted_at: datetime | None = Field(None, description="Deletion timestamp")


class CreateServiceResponse(SuccessResponse):
    model_config = ConfigDict(from_attributes=True)
    service: AdminService = Field(..., description="Created service")


class UpdateServiceResponse(SuccessResponse):
    model_config = ConfigDict(from_attributes=True)
    service: AdminService = Field(..., description="Updated service")


class UpdateServicePriceResponse(SuccessResponse):
    model_config = ConfigDict(from_attributes=True)
    service: AdminService = Field(..., description="Updated service")


class UpdateUserServiceResponse(SuccessResponse):
    model_config = ConfigDict(from_attributes=True)
    user_id: str = Field(..., description="User ID")
    service_id: str = Field(..., description="Service ID")
    status: USER_SERVICE_STATUS = Field(..., description="Updated status")
    updated_at: datetime = Field(..., description="Update timestamp")


class DeleteUserResponse(DeleteResponse):
    model_config = ConfigDict(from_attributes=True)
    user_id: str = Field(..., description="Deleted user ID")


class DeleteServiceResponse(DeleteResponse):
    model_config = ConfigDict(from_attributes=True)
    service_id: str = Field(..., description="Deleted service ID")


class AdminHealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Health status")
    service: str = Field("admin", description="Service name")
    timestamp: datetime = Field(..., description="Health check timestamp")


class AdminUserDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    success: bool = Field(True, description="Success status")
    data: AdminUserDetail = Field(..., description="User details")


# ─── BACKWARD COMPATIBILITY ──────────────────────────────────────

AdminUserItem = AdminUser
