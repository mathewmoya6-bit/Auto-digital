# app/modules/notifications/sms.py
# Auto-D Kenya - SMS Service
# ================================================================
# TYPE: MODULE - SMS sending service

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SMSService:
    """SMS service for sending SMS messages."""
    
    def __init__(self):
        # In production, initialize SMS provider (Africa's Talking, Twilio, etc.)
        pass
    
    async def send(self, phone: str, message: str) -> Dict[str, Any]:
        """Send an SMS."""
        try:
            # This is a placeholder - in production, use Africa's Talking or Twilio
            logger.info(f"Sending SMS to: {phone}")
            logger.info(f"Message: {message[:100]}...")
            
            return {
                "status": "sent",
                "to": phone
            }
            
        except Exception as e:
            logger.error(f"SMS send error: {str(e)}")
            return {"status": "failed", "error": str(e)}
