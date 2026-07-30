# app/modules/mpesa/schemas.py
# Auto-D Kenya - M-Pesa Schemas
# ================================================================
# TYPE: MODULE - M-Pesa Pydantic schemas

import re
from typing import Optional
from pydantic import BaseModel, validator


class MpesaPaymentRequest(BaseModel):
    phone: str
    service_id: str
    description: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    amount: Optional[float] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        phone = re.sub(r'\D', '', v)
        if phone.startswith('254'):
            phone = phone[3:]
        if phone.startswith('0'):
            phone = phone[1:]
        if not re.match(r'^(7\d{8}|11\d{7})$', phone):
            raise ValueError('Invalid phone number. Must be a Safaricom number (07X or 011X)')
        return phone


class MpesaPaymentResponse(BaseModel):
    checkout_request_id: str
    message: str
    status: str
