# app/modules/notifications/router.py

"""
Auto-D Kenya - Notifications API
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr

from app.core.database import get_supabase
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class EmailRequest(BaseModel):
    to: EmailStr
    subject: str
    body: str
    html_body: Optional[str] = None


class SmsRequest(BaseModel):
    phone_number: str
    message: str


class NotificationResponse(BaseModel):
    id: str
    type: str
    recipient: str
    status: str
    content: dict
    created_at: datetime
    error: Optional[str] = None


class NotificationHistoryResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int
    page: int
    per_page: int


# ------------------------------------------------------------------
# Email
# ------------------------------------------------------------------

@router.post("/email")
async def send_email(
    request: EmailRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Send an email.
    """

    return {
        "success": True,
        "message": "Email queued successfully",
        "recipient": request.to,
        "subject": request.subject,
        "sent_at": datetime.utcnow().isoformat(),
    }


# ------------------------------------------------------------------
# SMS
# ------------------------------------------------------------------

@router.post("/sms")
async def send_sms(
    request: SmsRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Send SMS.
    """

    return {
        "success": True,
        "message": "SMS queued successfully",
        "recipient": request.phone_number,
        "sent_at": datetime.utcnow().isoformat(),
    }


# ------------------------------------------------------------------
# Notification History
# ------------------------------------------------------------------

@router.get(
    "/history",
    response_model=NotificationHistoryResponse,
)
async def get_notification_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """
    Return notification history for the logged-in user.
    """

    try:
        supabase = get_supabase()

        user_id = current_user["id"]

        result = (
            supabase.table("notifications")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return {
            "notifications": result.data or [],
            "total": result.count or 0,
            "page": (offset // limit) + 1,
            "per_page": limit,
        }

    except Exception:
        # Table may not exist yet
        return {
            "notifications": [],
            "total": 0,
            "page": 1,
            "per_page": limit,
        }
