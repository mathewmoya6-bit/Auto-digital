# app/modules/notifications/service.py
# Auto-D Kenya - Notifications Service
# ================================================================
# TYPE: MODULE - Notifications business logic

import logging
from typing import Dict, Any
from datetime import datetime

from app.core.database import get_supabase
from app.modules.notifications.email import EmailService
from app.modules.notifications.sms import SMSService

logger = logging.getLogger(__name__)


class NotificationService:
    """Notification service for sending notifications."""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.email_service = EmailService()
        self.sms_service = SMSService()
    
    async def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Send an email notification."""
        try:
            result = await self.email_service.send(to, subject, body)
            
            # Log notification
            self.supabase.table("notifications").insert({
                "type": "email",
                "recipient": to,
                "subject": subject,
                "body": body,
                "status": result.get("status", "sent"),
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def send_sms(self, phone: str, message: str) -> Dict[str, Any]:
        """Send an SMS notification."""
        try:
            result = await self.sms_service.send(phone, message)
            
            # Log notification
            self.supabase.table("notifications").insert({
                "type": "sms",
                "recipient": phone,
                "body": message,
                "status": result.get("status", "sent"),
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def get_history(self, user_id: str) -> list:
        """Get notification history for a user."""
        try:
            response = self.supabase.table("notifications").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting notification history: {str(e)}")
            return []
