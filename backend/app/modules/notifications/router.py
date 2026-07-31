# app/modules/notifications/router.py
"""Notifications routes for Auto-D Kenya"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.core.database import get_supabase
from app.core.dependencies import get_current_user

router = APIRouter()

# ─── SCHEMAS ──────────────────────────────────────────────────────

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

# ─── ENDPOINTS ───────────────────────────────────────────────────

@router.post("/notifications/email")
async def send_email(
    request: EmailRequest,
    current_user = Depends(get_current_user)
):
    """
    Send an email notification.
    Requires authentication.
    """
    try:
        # Here you would integrate with an email service
        # For now, we'll log and return a success response
        return {
            "success": True,
            "message": "Email sent successfully",
            "to": request.to,
            "subject": request.subject,
            "sent_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/sms")
async def send_sms(
    request: SmsRequest,
    current_user = Depends(get_current_user)
):
    """
    Send an SMS notification.
    Requires authentication.
    """
    try:
        # Here you would integrate with an SMS service
        # For now, we'll log and return a success response
        return {
            "success": True,
            "message": "SMS sent successfully",
            "to": request.phone_number,
            "sent_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/notifications/history", response_model=NotificationHistoryResponse)
async def get_notification_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_user)
):
    """
    Get notification history for the current user.
    Requires authentication.
    """
    try:
        supabase = get_supabase()
        
        # Get total count
        count_result = supabase.table("notifications")\
            .select("*", count="exact")\
            .eq("user_id", current_user.id)\
            .execute()
        
        total = count_result.count if hasattr(count_result, 'count') else 0
        
        # Get paginated results
        result = supabase.table("notifications")\
            .select("*")\
            .eq("user_id", current_user.id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .offset(offset)\
            .execute()
        
        return {
            "notifications": result.data,
            "total": total,
            "page": offset // limit + 1 if limit > 0 else 1,
            "per_page": limit
        }
    except Exception as e:
        # If table doesn't exist yet, return empty history
        return {
            "notifications": [],
            "total": 0,
            "page": 1,
            "per_page": limit
        }
