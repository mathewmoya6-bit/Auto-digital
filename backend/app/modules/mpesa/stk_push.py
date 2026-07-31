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
        
        # Log configuration at startup
        self._log_configuration()
    
    def _log_configuration(self) -> None:
        """Log M-Pesa configuration for debugging."""
        logger.info(f"=== M-Pesa Configuration ===")
        logger.info(f"Environment: {settings.MPESA_ENVIRONMENT}")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Shortcode: {self.shortcode}")
        logger.info(f"Callback URL: {self.callback_url}")
        logger.info(f"Consumer Key Present: {bool(self.consumer_key)}")
        logger.info(f"Consumer Secret Present: {bool(self.consumer_secret)}")
        logger.info(f"Passkey Present: {bool(self.passkey)}")
        logger.info(f"============================")
    
    async def _get_access_token(self) -> str:
        """
        Get OAuth access token using GET request.
        
        Returns:
            str: Access token
            
        Raises:
            AppException: If token retrieval fails
        """
        # Check cached token
        if self.access_token and self.token_expiry and datetime.utcnow() < self.token_expiry:
            logger.debug("Using cached access token (valid until {})".format(
                self.token_expiry.isoformat()
            ))
            return self.access_token
        
        # Prepare authentication
        auth = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()
        
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        
        logger.info(f"Requesting OAuth token from: {url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Basic {auth}",
                    "Accept": "application/json"
                },
                timeout=30.0
            )
        
        # Log response details
        logger.info(f"OAuth Status: {response.status_code}")
        logger.info(f"OAuth Headers: {dict(response.headers)}")
        logger.info(f"OAuth Body: {response.text[:500]}...")
        
        # Check response status
        response.raise_for_status()
        
        # Parse JSON safely
        try:
            data = response.json()
        except ValueError as e:
            logger.error(f"OAuth returned non-JSON response: {response.text}")
            raise AppException(
                f"OAuth returned non-JSON response: {response.text[:200]}",
                503
            )
        
        # --- ✅ FIX: Safe token extraction with validation ---
        token = data.get("access_token")
        
        if not token:
            error_msg = data.get("error", data.get("error_description", "Unknown error"))
            logger.error(f"OAuth error: {error_msg}")
            raise AppException(
                f"OAuth failed: {error_msg}",
                503
            )
        
        # ✅ FIX: Safely parse expires_in with type checking
        try:
            expires_in = int(data.get("expires_in", 3600))
        except (TypeError, ValueError):
            logger.warning(f"Invalid expires_in value: {data.get('expires_in')}, using default 3600")
            expires_in = 3600
        
        # Store token with expiry
        self.access_token = token
        self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        
        logger.info(f"OAuth token obtained successfully, expires in {expires_in}s")
        logger.debug(f"Token will expire at: {self.token_expiry.isoformat()}")
        
        return token
    
    def _generate_password(self, timestamp: str) -> str:
        """Generate password for STK push."""
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(password_str.encode()).decode()
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to 254 format."""
        # Remove any non-digit characters
        phone = ''.join(filter(str.isdigit, phone))
        
        # If it starts with 0, remove it
        if phone.startswith('0'):
            phone = phone[1:]
        
        # If it starts with 254, keep as is
        if phone.startswith('254'):
            return phone
        
        # Otherwise prepend 254
        return f"254{phone}"
    
    async def initiate_push(
        self,
        phone: str,
        amount: float,
        description: str,
        checkout_request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        service_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initiate STK Push payment.
        
        Args:
            phone: Phone number (without country code)
            amount: Amount to charge
            description: Transaction description
            checkout_request_id: Optional custom ID
            user_id: Optional user ID for tracking
            service_id: Optional service ID for tracking
            
        Returns:
            Dict with checkout_request_id and status
            
        Raises:
            AppException: If STK push fails
        """
        # Ensure phone is in correct format
        phone = self._normalize_phone(phone)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        password = self._generate_password(timestamp)
        
        if not checkout_request_id:
            checkout_request_id = f"STK-{secrets.token_hex(8)}"
        
        # Build payload
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
        
        logger.info(f"Initiating STK Push for {phone}: {amount} KES (Ref: {checkout_request_id})")
        logger.debug(f"Payload: {payload}")
        
        # Get access token (with caching)
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
        
        logger.info(f"STK Push Status: {response.status_code}")
        logger.info(f"STK Push Response: {response.text[:500]}")
        
        if response.status_code != 200:
            logger.error(f"STK push HTTP error: {response.text}")
            raise AppException(
                f"Payment initiation failed: {response.text[:200]}",
                502
            )
        
        # Parse response safely
        try:
            data = response.json()
        except ValueError:
            logger.error(f"STK Push non-JSON response: {response.text}")
            raise AppException("Payment initiation failed: Invalid response", 502)
        
        # Check response code
        response_code = data.get("ResponseCode")
        response_desc = data.get("ResponseDescription", "Unknown error")
        
        if response_code != "0":
            logger.error(f"STK push failed: {response_code} - {response_desc}")
            raise AppException(
                f"STK push failed: {response_desc}",
                400
            )
        
        logger.info(f"STK Push successful: {data.get('CustomerMessage')}")
        
        return {
            "checkout_request_id": data.get("CheckoutRequestID", checkout_request_id),
            "merchant_request_id": data.get("MerchantRequestID"),
            "response_code": data.get("ResponseCode"),
            "response_description": data.get("ResponseDescription"),
            "customer_message": data.get("CustomerMessage")
        }
    
    def clear_token_cache(self) -> None:
        """Clear the cached access token to force refresh."""
        self.access_token = None
        self.token_expiry = None
        logger.info("Token cache cleared")
