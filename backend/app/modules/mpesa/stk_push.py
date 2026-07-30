# app/modules/mpesa/stk_push.py
# Auto-D Kenya - M-Pesa STK Push
# ================================================================
# TYPE: MODULE - M-Pesa STK Push logic

import base64
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import httpx

from app.core.config import settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


class StkPushService:
    """M-Pesa STK Push service."""
    
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
    
    async def _get_access_token(self) -> str:
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
            logger.error(f"M-Pesa token error: {response.text}")
            raise AppException("M-Pesa service unavailable", 503)
        
        data = response.json()
        self.access_token = data.get("access_token")
        self.token_expiry = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))
        return self.access_token
    
    def _generate_password(self, timestamp: str) -> str:
        """Generate password for STK push."""
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(password_str.encode()).decode()
    
    async def initiate_push(
        self,
        phone: str,
        amount: float,
        description: str,
        checkout_request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initiate STK Push payment.
        
        Args:
            phone: Phone number (without country code)
            amount: Amount to charge
            description: Transaction description
            checkout_request_id: Optional custom ID
            
        Returns:
            Dict with checkout_request_id and status
        """
        # Ensure phone is in correct format
        if not phone.startswith("254"):
            phone = "254" + phone
        
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        password = self._generate_password(timestamp)
        
        if not checkout_request_id:
            checkout_request_id = f"STK-{secrets.token_hex(8)}"
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": str(int(amount)),
            "PartyA": phone,
            "PartyB": self.shortcode,
            "PhoneNumber": phone,
            "CallBackURL": self.callback_url,
            "AccountReference": checkout_request_id[:12],
            "TransactionDesc": description[:36]
        }
        
        token = await self._get_access_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30.0
            )
        
        if response.status_code != 200:
            logger.error(f"STK push error: {response.text}")
            raise AppException("Payment initiation failed", 502)
        
        data = response.json()
        
        if data.get("ResponseCode") != "0":
            raise AppException(data.get("ResponseDescription", "STK push failed"), 400)
        
        return {
            "checkout_request_id": data.get("CheckoutRequestID", checkout_request_id),
            "merchant_request_id": data.get("MerchantRequestID"),
            "response_code": data.get("ResponseCode"),
            "response_description": data.get("ResponseDescription"),
            "customer_message": data.get("CustomerMessage")
        }
