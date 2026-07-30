# app/modules/notifications/schemas.py
# Auto-D Kenya - Notifications Schemas
# ================================================================
# TYPE: MODULE - Notifications Pydantic schemas

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr


class EmailRequest(BaseModel):
    to: EmailStr
    subject: str
    body: str
    html_body: Optional[str] = None


class SMSRequest(BaseModel):
    phone: str
    message: str


class NotificationResponse(BaseModel):
    id: str
    type: str
    recipient: str
    subject: Optional[str] = None
    body: str
    status: str
    created_at: datetime
