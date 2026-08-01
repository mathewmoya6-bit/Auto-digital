# app/modules/mpesa/schemas.py
# Auto-D Kenya - M-Pesa Schemas
# ================================================================
# TYPE: MODULE - M-Pesa Pydantic schemas

import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, validator


# ─── REQUEST SCHEMAS ──────────────────────────────────────────────

class MpesaPaymentRequest(BaseModel):
    """
    M-Pesa payment initiation request.
    """
    phone: str = Field(..., description="Phone number (07X or 011X format)")
    service_id: str = Field(..., description="Service code (e.g., 'valuation', 'mileage', 'ownership')")
    description: Optional[str] = Field(None, description="Transaction description (optional)")
    user_id: Optional[str] = Field(None, description="User ID (optional)")
    request_id: Optional[str] = Field(None, description="Request ID (optional)")
    amount: Optional[float] = Field(None, description="Amount to charge (optional, overrides service price)")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate and normalize phone number."""
        # Remove all non-digit characters
        phone = re.sub(r'\D', '', v)
        
        # Remove country code if present
        if phone.startswith('254'):
            phone = phone[3:]
        if phone.startswith('0'):
            phone = phone[1:]
        
        # Validate Safaricom number format
        if not re.match(r'^(7\d{8}|11\d{7})$', phone):
            raise ValueError('Invalid phone number. Must be a Safaricom number (07X or 011X)')
        
        return phone
    
    @field_validator('service_id')
    @classmethod
    def validate_service_id(cls, v: str) -> str:
        """Validate service ID."""
        allowed_services = ['valuation', 'mileage', 'ownership', 'tco', 'valuation_report']
        if v not in allowed_services:
            raise ValueError(f"Service ID must be one of: {', '.join(allowed_services)}")
        return v


class MpesaPaymentResponse(BaseModel):
    """M-Pesa payment initiation response."""
    checkout_request_id: str = Field(..., description="Checkout request ID for status tracking")
    message: str = Field(..., description="Response message")
    status: str = Field(..., description="Payment status (pending, completed, failed)")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = ['pending', 'completed', 'failed', 'paid', 'success']
        if v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v


# ─── PAYMENT STATUS SCHEMAS ───────────────────────────────────────

class PaymentStatusResponse(BaseModel):
    """Payment status response."""
    status: str = Field(..., description="Payment status")
    amount: float = Field(..., description="Payment amount")
    phone: str = Field(..., description="Phone number")
    created_at: str = Field(..., description="Creation timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    mpesa_receipt: Optional[str] = Field(None, description="M-Pesa receipt number")
    transaction_id: Optional[str] = Field(None, description="Transaction ID")


# ─── SERVICE ACCESS SCHEMAS ───────────────────────────────────────

class ServiceAccessResponse(BaseModel):
    """Service access check response."""
    has_access: bool = Field(..., description="Whether the user has access")
    status: str = Field(..., description="Access status (active, pending, expired, no_record)")
    expires_at: Optional[str] = Field(None, description="Access expiry timestamp")
    message: str = Field(..., description="Access message")


class UserServiceResponse(BaseModel):
    """User service response."""
    service_id: str = Field(..., description="Service code")
    name: str = Field(..., description="Service name")
    price: float = Field(..., description="Service price")
    description: Optional[str] = Field(None, description="Service description")
    icon: Optional[str] = Field(None, description="Service icon")
    has_access: bool = Field(..., description="Whether the user has access")
    expires_at: Optional[str] = Field(None, description="Access expiry timestamp")


class UserServicesResponse(BaseModel):
    """User services response."""
    services: Dict[str, bool] = Field(..., description="Service code to access status mapping")


# ─── AVAILABLE SERVICES SCHEMAS ──────────────────────────────────

class ServiceItem(BaseModel):
    """Available service item."""
    id: int = Field(..., description="Service ID")
    code: str = Field(..., description="Service code")
    name: str = Field(..., description="Service name")
    price: float = Field(..., description="Service price")
    currency: str = Field("KES", description="Currency code")
    description: Optional[str] = Field(None, description="Service description")
    icon: Optional[str] = Field(None, description="Service icon")
    active: bool = Field(True, description="Whether the service is active")
    display_order: int = Field(0, description="Display order")


class AvailableServicesResponse(BaseModel):
    """Available services response."""
    services: List[ServiceItem] = Field(..., description="List of available services")


# ─── PAYMENT HISTORY SCHEMAS ──────────────────────────────────────

class PaymentHistoryItem(BaseModel):
    """Payment history item."""
    id: int = Field(..., description="Payment ID")
    service_name: str = Field(..., description="Service name")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field("KES", description="Currency code")
    status: str = Field(..., description="Payment status")
    created_at: str = Field(..., description="Creation timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    mpesa_receipt: Optional[str] = Field(None, description="M-Pesa receipt number")


class PaymentHistoryResponse(BaseModel):
    """Payment history response."""
    payments: List[PaymentHistoryItem] = Field(..., description="List of payments")


# ─── CALLBACK SCHEMAS ─────────────────────────────────────────────

class StkCallbackItem(BaseModel):
    """STK callback item."""
    Name: str = Field(..., description="Item name")
    Value: str = Field(..., description="Item value")


class StkCallbackMetadata(BaseModel):
    """STK callback metadata."""
    Item: List[StkCallbackItem] = Field(..., description="Callback items")


class StkCallback(BaseModel):
    """STK callback body."""
    MerchantRequestID: str = Field(..., description="Merchant request ID")
    CheckoutRequestID: str = Field(..., description="Checkout request ID")
    ResultCode: int = Field(..., description="Result code (0 = success)")
    ResultDesc: str = Field(..., description="Result description")
    CallbackMetadata: Optional[StkCallbackMetadata] = Field(None, description="Callback metadata")


class MpesaCallbackBody(BaseModel):
    """M-Pesa callback body."""
    stkCallback: StkCallback = Field(..., description="STK callback")


class MpesaCallbackRequest(BaseModel):
    """M-Pesa callback request."""
    Body: MpesaCallbackBody = Field(..., description="Callback body")


# ─── WEBHOOK RESPONSE SCHEMAS ────────────────────────────────────

class WebhookResponse(BaseModel):
    """Webhook response."""
    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
    checkout_request_id: Optional[str] = Field(None, description="Checkout request ID")
    mpesa_receipt: Optional[str] = Field(None, description="M-Pesa receipt number")
    transaction_id: Optional[str] = Field(None, description="Transaction ID")


# ─── HEALTH CHECK SCHEMAS ─────────────────────────────────────────

class MpesaHealthResponse(BaseModel):
    """M-Pesa health check response."""
    status: str = Field(..., description="Service health status")
    service: str = Field("mpesa", description="Service name")
    version: str = Field("1.0", description="API version")
    timestamp: str = Field(..., description="ISO timestamp")
    environment: str = Field(..., description="Environment (sandbox/production)")
    shortcode: str = Field(..., description="M-Pesa shortcode")


# ─── FACTORY FUNCTIONS ────────────────────────────────────────────

def create_payment_response(
    checkout_request_id: str,
    message: str,
    status: str = "pending"
) -> MpesaPaymentResponse:
    """Create a payment response."""
    return MpesaPaymentResponse(
        checkout_request_id=checkout_request_id,
        message=message,
        status=status
    )


def create_service_access_response(
    has_access: bool,
    status: str,
    expires_at: Optional[str] = None,
    message: str = ""
) -> ServiceAccessResponse:
    """Create a service access response."""
    if not message:
        if has_access:
            message = "Access granted"
        elif status == "expired":
            message = "Access has expired"
        elif status == "no_record":
            message = "No access record found"
        else:
            message = f"Access status: {status}"
    
    return ServiceAccessResponse(
        has_access=has_access,
        status=status,
        expires_at=expires_at,
        message=message
    )


def create_webhook_response(
    status: str,
    message: str,
    checkout_request_id: Optional[str] = None,
    mpesa_receipt: Optional[str] = None,
    transaction_id: Optional[str] = None
) -> WebhookResponse:
    """Create a webhook response."""
    return WebhookResponse(
        status=status,
        message=message,
        checkout_request_id=checkout_request_id,
        mpesa_receipt=mpesa_receipt,
        transaction_id=transaction_id
    )


# ─── EXAMPLE RESPONSES ────────────────────────────────────────────

"""
EXAMPLE: MpesaPaymentResponse
{
    "checkout_request_id": "CHK-valu-123456",
    "message": "STK push sent successfully",
    "status": "pending"
}

EXAMPLE: ServiceAccessResponse
{
    "has_access": true,
    "status": "active",
    "expires_at": "2027-08-02T12:00:00.000Z",
    "message": "Access granted"
}

EXAMPLE: UserServicesResponse
{
    "services": {
        "valuation": true,
        "mileage": false,
        "ownership": true,
        "tco": false
    }
}

EXAMPLE: AvailableServicesResponse
{
    "services": [
        {
            "id": 1,
            "code": "valuation",
            "name": "Vehicle Valuation",
            "price": 500.00,
            "currency": "KES",
            "description": "Get instant vehicle valuation",
            "icon": "📊",
            "active": true,
            "display_order": 1
        }
    ]
}
"""
