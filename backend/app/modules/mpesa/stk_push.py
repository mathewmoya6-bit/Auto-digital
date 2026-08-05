# app/modules/mpesa/stk_push.py
"""
Auto-D Kenya - M-Pesa STK Push Service
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


# ============================================================
# Helpers
# ============================================================

def normalize_phone(phone: str) -> str:
    """
    Convert Kenyan phone numbers to 2547XXXXXXXX format.
    
    Args:
        phone: Phone number in any format (e.g., 0712345678, +254712345678, 254712345678)
    
    Returns:
        Normalized phone number in 2547XXXXXXXX format
    
    Raises:
        ValueError: If phone number is invalid
    """
    if not phone:
        raise ValueError("Phone number is required")

    # Remove all non-digit characters
    phone = "".join(ch for ch in str(phone) if ch.isdigit())

    # Format to 254...
    if phone.startswith("254"):
        pass
    elif phone.startswith("0"):
        phone = "254" + phone[1:]
    elif phone.startswith("7"):
        phone = "254" + phone
    else:
        raise ValueError("Invalid Kenyan phone number")

    if len(phone) != 12:
        raise ValueError(f"Invalid phone number length: {len(phone)} (expected 12)")

    return phone


def mask_sensitive(value: Optional[str]) -> str:
    """
    Mask sensitive values for logs.
    
    Args:
        value: String to mask
    
    Returns:
        Masked string with only first 3 and last 3 characters visible
    """
    if not value:
        return "***"

    value = str(value)

    if len(value) <= 6:
        return "***"

    return f"{value[:3]}***{value[-3:]}"


# ============================================================
# STK Push Service
# ============================================================

class StkPushService:
    """
    Safaricom Daraja STK Push client.
    
    Handles:
        - OAuth token acquisition and caching
        - STK Push initiation
        - Payment status queries
        - Health checks
        - Callback verification
    """

    TOKEN_BUFFER_SECONDS = 60

    def __init__(self):
        """Initialize the STK Push service with configuration from settings."""
        
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE

        self.callback_url = settings.MPESA_CALLBACK_URL
        self.base_url = settings.get_mpesa_base_url()

        self.timeout = settings.get_mpesa_timeout()

        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    # ============================================================
    # OAuth
    # ============================================================

    async def get_access_token(self) -> str:
        """
        Get a valid OAuth access token from Safaricom.
        
        Returns:
            Access token string
        
        Raises:
            AppException: If token acquisition fails
        """
        now = datetime.now(timezone.utc)

        # Return cached token if still valid
        if (
            self._access_token
            and self._token_expiry
            and now < self._token_expiry
        ):
            return self._access_token

        if not self.consumer_key or not self.consumer_secret:
            raise AppException("M-Pesa credentials are not configured")

        # Encode credentials
        credentials = f"{self.consumer_key}:{self.consumer_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Basic {encoded}"},
                )

            if response.status_code != 200:
                logger.error(
                    "OAuth failed | %s | %s",
                    response.status_code,
                    response.text,
                )
                raise AppException("Unable to obtain M-Pesa access token")

            data = response.json()
            token = data.get("access_token")

            if not token:
                raise AppException("M-Pesa returned no access token")

            expires = int(data.get("expires_in", 3600))

            # Cache token with buffer
            self._access_token = token
            self._token_expiry = now + timedelta(
                seconds=expires - self.TOKEN_BUFFER_SECONDS
            )

            logger.info("M-Pesa OAuth token refreshed")
            return token

        except httpx.TimeoutException:
            logger.error("OAuth request timed out")
            raise AppException("M-Pesa OAuth request timed out")
        except Exception as e:
            logger.exception("OAuth failed")
            raise AppException(f"OAuth failed: {str(e)}")

    # ============================================================
    # Helpers
    # ============================================================

    def _generate_timestamp(self) -> str:
        """Generate Safaricom timestamp in YYYYMMDDHHMMSS format."""
        return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    def _generate_password(self, timestamp: str) -> str:
        """
        Generate STK push password.
        
        Args:
            timestamp: Timestamp in YYYYMMDDHHMMSS format
        
        Returns:
            Base64 encoded password string
        """
        raw = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(raw.encode("utf-8")).decode("utf-8")

    # ============================================================
    # STK Push Initiation
    # ============================================================

    async def initiate_push(
        self,
        *,
        phone: str,
        amount: float,
        description: str,
        user_id: Optional[str] = None,
        service_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Initiate an STK Push request.

        Compatible with MpesaService.initiate_payment().

        Args:
            phone: Customer phone number
            amount: Amount to charge
            description: Transaction description
            user_id: Optional user ID (for reference)
            service_id: Optional service ID (for reference)

        Returns:
            Dict containing:
                - status: "pending"
                - checkout_request_id: M-Pesa checkout request ID
                - merchant_request_id: M-Pesa merchant request ID
                - customer_message: Message for customer
                - response_code: M-Pesa response code
                - response_description: M-Pesa response description

        Raises:
            AppException: If STK Push fails
        """
        if not self.shortcode:
            raise AppException("MPESA_SHORTCODE is not configured")

        if not self.passkey:
            raise AppException("MPESA_PASSKEY is not configured")

        if not self.callback_url:
            raise AppException("MPESA_CALLBACK_URL is not configured")

        # Normalize phone
        phone = normalize_phone(phone)

        # Ensure amount is an integer (M-Pesa expects whole numbers)
        amount = int(round(float(amount)))

        if amount <= 0:
            raise AppException("Amount must be greater than 0")

        # Generate credentials
        timestamp = self._generate_timestamp()
        password = self._generate_password(timestamp)

        # Prepare payload
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": self.shortcode,
            "PhoneNumber": phone,
            "CallBackURL": self.callback_url,
            "AccountReference": str(service_id or "AUTOD")[:20],
            "TransactionDesc": description[:50] if description else "Auto-D Kenya Payment",
        }

        # Get access token
        token = await self.get_access_token()

        logger.info(
            "Initiating STK Push | phone=%s amount=%s service=%s user=%s",
            mask_sensitive(phone),
            amount,
            service_id,
            user_id,
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            if response.status_code != 200:
                logger.error(
                    "STK Push HTTP Error | %s | %s",
                    response.status_code,
                    response.text,
                )
                raise AppException("Failed to initiate STK Push")

            data = response.json()

            # Check response
            if data.get("ResponseCode") != "0":
                error_msg = data.get(
                    "ResponseDescription",
                    "STK Push rejected"
                )
                logger.error("STK rejected request | %s", error_msg)
                raise AppException(error_msg)

            logger.info(
                "STK Push accepted | checkout=%s",
                mask_sensitive(data.get("CheckoutRequestID")),
            )

            return {
                "status": "pending",
                "response_code": data.get("ResponseCode"),
                "response_description": data.get("ResponseDescription"),
                "checkout_request_id": data.get("CheckoutRequestID"),
                "merchant_request_id": data.get("MerchantRequestID"),
                "customer_message": data.get("CustomerMessage"),
            }

        except httpx.TimeoutException:
            logger.error("STK Push request timed out")
            raise AppException("STK Push request timed out")
        except AppException:
            raise
        except Exception as e:
            logger.exception("STK Push failed")
            raise AppException(f"STK Push failed: {str(e)}")

    # ============================================================
    # STK Query
    # ============================================================

    async def query_payment(
        self,
        checkout_request_id: str,
    ) -> Dict[str, Any]:
        """
        Query the payment status from Safaricom.

        Args:
            checkout_request_id: M-Pesa checkout request ID

        Returns:
            Dict containing:
                - status: "completed", "pending", "failed", or "cancelled"
                - result_code: M-Pesa result code
                - result_desc: M-Pesa result description
                - checkout_request_id: Original checkout request ID

        Raises:
            AppException: If query fails
        """
        if not checkout_request_id:
            raise AppException("Checkout request ID is required")

        timestamp = self._generate_timestamp()
        password = self._generate_password(timestamp)

        token = await self.get_access_token()

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        logger.info(
            "Querying payment | checkout=%s",
            mask_sensitive(checkout_request_id),
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/mpesa/stkpushquery/v1/query",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            if response.status_code != 200:
                logger.error(
                    "Query failed | %s | %s",
                    response.status_code,
                    response.text,
                )
                raise AppException("Unable to query payment status")

            data = response.json()

            # Map result codes to statuses
            status_map = {
                "0": "completed",
                "1": "failed",
                "1032": "cancelled",
                "1037": "failed",
                "2001": "pending",
            }

            result_code = str(data.get("ResultCode", "2001"))
            status = status_map.get(result_code, "pending")

            logger.info(
                "Query result | checkout=%s status=%s result_code=%s",
                mask_sensitive(checkout_request_id),
                status,
                result_code,
            )

            return {
                "status": status,
                "result_code": result_code,
                "result_desc": data.get("ResultDesc", "Unknown status"),
                "checkout_request_id": checkout_request_id,
                "amount": data.get("Amount"),
                "receipt": data.get("MpesaReceiptNumber"),
                "transaction_date": data.get("TransactionDate"),
            }

        except httpx.TimeoutException:
            logger.error("Query request timed out")
            raise AppException("Payment status query timed out")
        except AppException:
            raise
        except Exception as e:
            logger.exception("Query failed")
            raise AppException(f"Payment status query failed: {str(e)}")

    # ============================================================
    # Cleanup
    # ============================================================

    async def cleanup_stale_payments(self) -> int:
        """
        Cleanup hook for stale pending payments.

        The payment repository/service owns payment state, so this
        method simply exists to satisfy MpesaService and can be
        extended later if automatic expiry is required.
        """
        logger.info("Running stale payment cleanup")
        return 0

    # ============================================================
    # Health Check
    # ============================================================

    async def health_check(self) -> Dict[str, Any]:
        """
        Verify M-Pesa configuration and connectivity.
        
        Returns:
            Dict with health status and check results
        """
        status = {
            "service": "mpesa",
            "status": "healthy",
            "environment": settings.MPESA_ENVIRONMENT,
            "base_url": self.base_url,
            "checks": {
                "credentials": True,
                "oauth": False,
            },
        }

        # Check credentials
        if not all([
            self.consumer_key,
            self.consumer_secret,
            self.passkey,
            self.shortcode,
            self.callback_url,
        ]):
            status["status"] = "unhealthy"
            status["checks"]["credentials"] = False
            status["message"] = "Missing required credentials"
            return status

        # Check OAuth connectivity
        try:
            await self.get_access_token()
            status["checks"]["oauth"] = True
        except Exception as exc:
            logger.exception("OAuth health check failed")
            status["status"] = "degraded"
            status["message"] = str(exc)

        return status

    # ============================================================
    # Callback Verification
    # ============================================================

    def verify_callback_secret(
        self,
        callback_secret: Optional[str],
    ) -> bool:
        """
        Verify callback secret if configured.

        Returns True when:
            • no callback secret is configured
            • supplied secret matches configuration

        Args:
            callback_secret: The secret from the request

        Returns:
            True if valid or no secret required
        """
        configured = getattr(settings, "MPESA_CALLBACK_SECRET", "")

        if not configured:
            return True

        return callback_secret == configured

    # ============================================================
    # Convenience Methods
    # ============================================================

    def is_configured(self) -> bool:
        """
        Returns True if all required credentials exist.
        """
        return all([
            self.consumer_key,
            self.consumer_secret,
            self.passkey,
            self.shortcode,
            self.callback_url,
            self.base_url,
        ])

    async def close(self) -> None:
        """
        Reserved for future shared HTTP client cleanup.
        """
        return
