# app/modules/mpesa/schemas.py
# Auto-D Kenya - M-Pesa Schemas
# ================================================================
# TYPE: MODULE - M-Pesa Pydantic schemas

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


# ================================================================
# REQUEST SCHEMAS
# ================================================================


class MpesaPaymentRequest(BaseModel):
    """
    M-Pesa STK Push request.

    Accepts:
    - service_id = 1
    - service_id = "valuation"
    """

    phone: str = Field(
        ...,
        description="Safaricom phone number"
    )

    service_id: Union[int, str] = Field(
        ...,
        description="Service ID or service code"
    )

    description: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    amount: Optional[float] = None


    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        """
        Normalize Kenyan phone number.
        Returns format:
        7XXXXXXXX / 1XXXXXXXX
        """

        phone = re.sub(
            r"\D",
            "",
            value
        )

        if phone.startswith("254"):
            phone = phone[3:]

        if phone.startswith("0"):
            phone = phone[1:]

        if not re.match(
            r"^(7\d{8}|1\d{8})$",
            phone
        ):
            raise ValueError(
                "Invalid Safaricom phone number"
            )

        return phone


    @field_validator("service_id")
    @classmethod
    def validate_service(
        cls,
        value: Union[int, str]
    ) -> Union[int, str]:

        allowed = {
            "valuation",
            "mileage",
            "ownership",
            "tco",
            "valuation_report"
        }

        if isinstance(value, int):

            if value <= 0:
                raise ValueError(
                    "service_id must be greater than zero"
                )

            return value


        if isinstance(value, str):

            value = value.strip().lower()

            if value.isdigit():
                return int(value)

            if value in allowed:
                return value


        raise ValueError(
            "Invalid service_id"
        )


# ================================================================
# PAYMENT RESPONSE
# ================================================================


class MpesaPaymentResponse(BaseModel):

    checkout_request_id: str

    message: str

    status: str = "pending"


    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str):

        allowed = {
            "pending",
            "completed",
            "failed",
            "paid",
            "success"
        }

        if value not in allowed:
            raise ValueError(
                "Invalid payment status"
            )

        return value



class PaymentStatusResponse(BaseModel):

    status: str

    amount: float

    phone: str

    created_at: str

    completed_at: Optional[str] = None

    mpesa_receipt: Optional[str] = None

    transaction_id: Optional[str] = None



# ================================================================
# SERVICE ACCESS
# ================================================================


class ServiceAccessResponse(BaseModel):

    has_access: bool

    status: str

    expires_at: Optional[str] = None

    message: str



class UserServiceResponse(BaseModel):

    service_id: str

    name: str

    price: float

    description: Optional[str] = None

    icon: Optional[str] = None

    has_access: bool

    expires_at: Optional[str] = None



class UserServicesResponse(BaseModel):

    services: Dict[str, bool]



# ================================================================
# AVAILABLE SERVICES
# ================================================================


class ServiceItem(BaseModel):

    id: int

    code: str

    name: str

    price: float

    currency: str = "KES"

    description: Optional[str] = None

    icon: Optional[str] = None

    active: bool = True

    display_order: int = 0



class AvailableServicesResponse(BaseModel):

    services: List[ServiceItem]



# ================================================================
# PAYMENT HISTORY
# ================================================================


class PaymentHistoryItem(BaseModel):

    id: int

    service_name: str

    amount: float

    currency: str = "KES"

    status: str

    created_at: str

    completed_at: Optional[str] = None

    mpesa_receipt: Optional[str] = None



class PaymentHistoryResponse(BaseModel):

    payments: List[PaymentHistoryItem]



# ================================================================
# STK CALLBACK
# ================================================================


class StkCallbackItem(BaseModel):

    Name: str

    Value: Optional[Any] = None



class StkCallbackMetadata(BaseModel):

    Item: List[StkCallbackItem] = Field(
        default_factory=list
    )



class StkCallback(BaseModel):

    MerchantRequestID: str

    CheckoutRequestID: str

    ResultCode: int

    ResultDesc: str

    CallbackMetadata: Optional[
        StkCallbackMetadata
    ] = None



class MpesaCallbackBody(BaseModel):

    stkCallback: StkCallback



class MpesaCallbackRequest(BaseModel):

    Body: MpesaCallbackBody



# ================================================================
# WEBHOOK RESPONSE
# ================================================================


class WebhookResponse(BaseModel):

    status: str

    message: str

    checkout_request_id: Optional[str] = None

    mpesa_receipt: Optional[str] = None

    transaction_id: Optional[str] = None



# ================================================================
# HEALTH
# ================================================================


class MpesaHealthResponse(BaseModel):

    status: str

    service: str = "mpesa"

    version: str = "1.0"

    timestamp: str

    environment: str

    shortcode: str



# ================================================================
# FACTORY HELPERS
# ================================================================


def create_payment_response(
    checkout_request_id: str,
    message: str,
    status: str = "pending"
) -> MpesaPaymentResponse:

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

    if not message:

        if has_access:
            message = "Access granted"

        elif status == "expired":
            message = "Access expired"

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

    return WebhookResponse(
        status=status,
        message=message,
        checkout_request_id=checkout_request_id,
        mpesa_receipt=mpesa_receipt,
        transaction_id=transaction_id
    )
