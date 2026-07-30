# app/integrations/resend.py
# Auto-D Kenya - Resend Email Integration
# ================================================================
# TYPE: INTEGRATION - Resend email client

import logging
from typing import Dict, Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ResendClient:
    """Resend email client."""
    
    def __init__(self):
        self.api_key = settings.get("RESEND_API_KEY", "")
        self.from_email = settings.get("SMTP_FROM_EMAIL", "noreply@auto-d.ke")
        self.base_url = "https://api.resend.com"
    
    async def send_email(self, to: str, subject: str, html: str, text: str = None) -> Dict[str, Any]:
        """Send an email via Resend."""
        if not self.api_key:
            logger.warning("Resend API key not configured")
            return {"status": "failed", "error": "API key not configured"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/emails",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": self.from_email,
                        "to": [to],
                        "subject": subject,
                        "html": html,
                        "text": text or html
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {"status": "sent", "id": data.get("id")}
                else:
                    return {"status": "failed", "error": response.text}
                    
        except Exception as e:
            logger.error(f"Resend email error: {str(e)}")
            return {"status": "failed", "error": str(e)}
