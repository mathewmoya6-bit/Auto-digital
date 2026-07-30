# app/integrations/daraja.py
# Auto-D Kenya - Daraja Integration
# ================================================================
# TYPE: INTEGRATION - M-Pesa Daraja API client

import base64
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class DarajaClient:
    """M-Pesa Daraja API client."""
    
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE
        self.callback_url = settings.MPESA_CALLBACK_URL
        
        self.base_url = (
            "https://api.safaricom.co.ke"
            if settings.MPESA_ENVIRONMENT == "production"
            else "https://sandbox.safaricom.co.ke"
        )
        
        self.access_token = None
        self.token_expiry = None
    
    async def get_access_token(self) -> str:
        """Get OAuth access token."""
        if self.access_token and self.token_expiry and datetime.utcnow() < self.token_expiry:
            return self.access_token
        
        auth = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
                headers={"Authorization": f"Basic {auth}"}
            )
        
        if response.status_code != 200:
            logger.error(f"Daraja token error: {response.text}")
            raise Exception("Failed to get access token")
        
        data = response.json()
        self.access_token = data.get("access_token")
        self.token_expiry = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))
        return self.access_token
    
    def generate_password(self, timestamp: str) -> str:
        """Generate password for STK push."""
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(password_str.encode()).decode()
