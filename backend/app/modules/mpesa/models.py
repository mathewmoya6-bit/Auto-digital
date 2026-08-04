# app/modules/mpesa/models.py
# ================================================================
# Auto-D Kenya - M-Pesa Models
# ================================================================

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from decimal import Decimal

from pydantic import BaseModel, Field


class MpesaTransaction(BaseModel):
    """M-Pesa transaction model."""
    
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID = Field(..., description="Foreign key to User")
    service_id: Optional[UUID] = Field(None, description="Foreign key to Service")
    
    # Transaction details
    checkout_request_id: str = Field(..., description="M-Pesa checkout request ID")
    merchant_request_id: Optional[str] = Field(None, description="Merchant request ID")
    
    # Payment details
    amount: Decimal = Field(..., gt=0, description="Transaction amount")
    currency: str = Field("KES", description="Currency code")
    phone: str = Field(..., description="Customer phone number")
    account_reference: str = Field(..., max_length=12, description="Account reference")
    transaction_desc: str = Field(..., max_length=13, description="Transaction description")
    
    # Status
    status: str = Field("pending", description="Transaction status")
    result_code: Optional[int] = Field(None, description="M-Pesa result code")
    result_desc: Optional[str] = Field(None, description="M-Pesa result description")
    mpesa_receipt: Optional[str] = Field(None, description="M-Pesa receipt number")
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    
    # Webhook
    callback_data: Optional[Dict[str, Any]] = Field(None, description="Callback data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class MpesaStkPushRequest(BaseModel):
    """M-Pesa STK Push request model."""
    
    phone: str = Field(..., description="Customer phone number (2547XXXXXXXX)")
    amount: Decimal = Field(..., gt=0, description="Transaction amount")
    account_reference: str = Field(..., max_length=12, description="Account reference")
    transaction_desc: str = Field("Payment", max_length=13, description="Transaction description")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Remove leading zeros or plus
        if v.startswith('0'):
            v = '254' + v[1:]
        elif v.startswith('+'):
            v = v[1:]
        if not v.startswith('254'):
            raise ValueError("Phone number must start with 254")
        if len(v) != 12:
            raise ValueError("Phone number must be 12 digits")
        return v


class MpesaStkPushResponse(BaseModel):
    """M-Pesa STK Push response model."""
    
    checkout_request_id: str = Field(..., description="Checkout request ID")
    merchant_request_id: str = Field(..., description="Merchant request ID")
    response_code: str = Field(..., description="Response code")
    response_description: str = Field(..., description="Response description")
    customer_message: str = Field(..., description="Customer message")


class MpesaCallbackData(BaseModel):
    """M-Pesa callback data model."""
    
    body: Dict[str, Any] = Field(..., description="Callback body")
    
    @property
    def result_code(self) -> Optional[int]:
        """Extract result code from callback."""
        return self.body.get('stkCallback', {}).get('ResultCode')
    
    @property
    def result_desc(self) -> Optional[str]:
        """Extract result description from callback."""
        return self.body.get('stkCallback', {}).get('ResultDesc')
    
    @property
    def checkout_request_id(self) -> Optional[str]:
        """Extract checkout request ID from callback."""
        return self.body.get('stkCallback', {}).get('CheckoutRequestID')
    
    @property
    def mpesa_receipt(self) -> Optional[str]:
        """Extract M-Pesa receipt from callback."""
        metadata = self.body.get('stkCallback', {}).get('CallbackMetadata', {})
        for item in metadata.get('Item', []):
            if item.get('Name') == 'MpesaReceiptNumber':
                return item.get('Value')
        return None
    
    @property
    def amount(self) -> Optional[Decimal]:
        """Extract amount from callback."""
        metadata = self.body.get('stkCallback', {}).get('CallbackMetadata', {})
        for item in metadata.get('Item', []):
            if item.get('Name') == 'Amount':
                return Decimal(str(item.get('Value', 0)))
        return None


class MpesaTransactionStatus(BaseModel):
    """M-Pesa transaction status model."""
    
    checkout_request_id: str = Field(..., description="Checkout request ID")
    status: str = Field(..., description="Transaction status")
    result_code: Optional[int] = Field(None, description="Result code")
    result_desc: Optional[str] = Field(None, description="Result description")
    mpesa_receipt: Optional[str] = Field(None, description="M-Pesa receipt number")
    amount: Optional[Decimal] = Field(None, description="Transaction amount")
    transaction_date: Optional[str] = Field(None, description="Transaction date")


class MpesaTransactionResponse(BaseModel):
    """M-Pesa transaction response model."""
    
    id: UUID
    user_id: UUID
    checkout_request_id: str
    amount: Decimal
    currency: str
    phone: str
    account_reference: str
    transaction_desc: str
    status: str
    mpesa_receipt: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


__all__ = [
    "MpesaTransaction",
    "MpesaStkPushRequest",
    "MpesaStkPushResponse",
    "MpesaCallbackData",
    "MpesaTransactionStatus",
    "MpesaTransactionResponse",
]
