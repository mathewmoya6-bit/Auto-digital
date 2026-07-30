# app/modules/notifications/router.py
# Auto-D Kenya - Notifications Routes
# ================================================================
# TYPE: MODULE - Notifications API routes

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.modules.notifications.service import NotificationService

router = APIRouter()
notification_service = NotificationService()


@router.post("/notifications/email")
async def send_email(
    to: str,
    subject: str,
    body: str,
    current_user: dict = Depends(get_current_user)
):
    """Send an email notification."""
    result = await notification_service.send_email(to, subject, body)
    return result


@router.post("/notifications/sms")
async def send_sms(
    phone: str,
    message: str,
    current_user: dict = Depends(get_current_user)
):
    """Send an SMS notification."""
    result = await notification_service.send_sms(phone, message)
    return result


@router.get("/notifications/history")
async def get_notification_history(current_user: dict = Depends(get_current_user)):
    """Get notification history for the current user."""
    return await notification_service.get_history(current_user["id"])
