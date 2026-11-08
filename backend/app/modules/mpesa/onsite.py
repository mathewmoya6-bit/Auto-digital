# app/modules/mpesa/stk_push.py
"""
Auto-D Kenya - M-Pesa STK Push Service
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

import httpx

from app.core.config import settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)

NAIROBI_TZ = ZoneInfo("Africa/Nairobi")


# ============================================================
# Helpers
# ============================================================

def normalize_phone(phone: str) -> str:
    """
    Convert Kenyan phone numbers to 2547XXXXXXXX / 2541XXXXXXXX format.

    Accepts 0712345678, +254712345678, 254712345678, 712345678.

    Raises:
        ValueError: If the phone number is invalid.
    """
    if not phone:
        raise ValueError("Phone number is required")

    phone = "".join(ch for ch in str(phone) if ch.isdigit())

    if phone.startswith("254"):
        pass
    elif phone.startswith("0"):
        phone = "254" + phone[1:]
    elif phone.startswith(("7", "1")):
        phone = "254" + phone
    else:
        raise ValueError("Invalid Kenyan phone number")

    if len(phone) != 12:
        raise ValueError(
            f"Invalid phone number length: {len(phone)} (expected 12)"
        )

    return phone


def mask_sensitive(value: Optional[str]) -> str:
    """Mask sensitive values for logs (first 3 and last 3 characters only)."""
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

    # Daraja returns this error from the query endpoint while the
    # customer is still completing the prompt.
    _STILL_PROCESSING_CODE = "500.001.1001"

    def __init__(self):
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
        """Return a valid OAuth access token, using the cache when possible."""
        now = datetime.now(timezone.utc)

        if (
            self._access_token
            and self._token_expiry
            and now < self._token_expiry
        ):
            return self._access_token

        if not self.consumer_key or not self.consumer_secret:
            raise AppException("M-Pesa credentials are not configured")

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

            self._access_token = token
            self._token_expiry = now + timedelta(
                seconds=expires - self.TOKEN_BUFFER_SECONDS
            )

            logger.info("M-Pesa OAuth token refreshed")
            return token

        except httpx.TimeoutException:
            logger.error("OAuth request timed out")
            raise AppException("M-Pesa OAuth request timed out")
        except AppException:
            raise
        except Exception as e:
            logger.exception("OAuth failed")
            raise AppException(f"OAuth failed: {str(e)}")

    # ============================================================
    # Helpers
    # ============================================================

    def _generate_timestamp(self) -> str:
        """Safaricom timestamp (YYYYMMDDHHMMSS) in Nairobi time."""
        return datetime.now(NAIROBI_TZ).strftime("%Y%m%d%H%M%S")

    def _generate_password(self, timestamp: str) -> str:
        """Base64(shortcode + passkey + timestamp)."""
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
        service_id: Optional[Any] = None,
        account_reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Initiate an STK Push request.

        Args:
            phone: Customer phone number
            amount: Amount to charge (rounded to whole shillings)
            description: Transaction description
            user_id: Optional user ID (logging only)
            service_id: Optional service ID, used as the account
                reference when account_reference is not given
            account_reference: Reference shown to the customer
                (max 12 characters)

        Returns:
            Dict with status, checkout_request_id, merchant_request_id,
            customer_message, response_code and response_description.

        Raises:
            AppException: If the STK Push fails.
        """
        if not self.shortcode:
            raise AppException("MPESA_SHORTCODE is not configured")

        if not self.passkey:
            raise AppException("MPESA_PASSKEY is not configured")

        if not self.callback_url:
            raise AppException("MPESA_CALLBACK_URL is not configured")

        try:
            phone = normalize_phone(phone)
        except ValueError as exc:
            raise AppException(str(exc))

        amount = int(round(float(amount)))

        if amount <= 0:
            raise AppException("Amount must be greater than 0")

        timestamp = self._generate_timestamp()
        password = self._generate_password(timestamp)

        reference = str(account_reference or service_id or "AUTOD")[:12]

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
            "AccountReference": reference,
            "TransactionDesc": (
                description[:50] if description else "Auto-D Kenya Payment"
            ),
        }

        token = await self.get_access_token()

        logger.info(
            "Initiating STK Push | phone=%s amount=%s ref=%s user=%s",
            mask_sensitive(phone),
            amount,
            reference,
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

            if str(data.get("ResponseCode")) != "0":
                error_msg = data.get("ResponseDescription", "STK Push rejected")
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

    async def query_payment(self, checkout_request_id: str) -> Dict[str, Any]:
        """
        Query the payment status from Safaricom.

        Returns a dict with:
            status: "completed", "pending", "failed" or "cancelled"
            result_code, result_desc, checkout_request_id,
            amount, receipt, transaction_date

        A transaction that is still being processed is reported as
        "pending" instead of raising.

        Raises:
            AppException: If the query fails for any other reason.
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
                try:
                    err = response.json()
                except Exception:
                    err = {}

                if err.get("errorCode") == self._STILL_PROCESSING_CODE:
                    return {
                        "status": "pending",
                        "result_code": "2001",
                        "result_desc": err.get(
                            "errorMessage",
                            "Transaction is being processed",
                        ),
                        "checkout_request_id": checkout_request_id,
                        "amount": None,
                        "receipt": None,
                        "transaction_date": None,
                    }

                logger.error(
                    "Query failed | %s | %s",
                    response.status_code,
                    response.text,
                )
                raise AppException("Unable to query payment status")

            data = response.json()

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
        exists to satisfy MpesaService and can be extended later.
        """
        logger.info("Running stale payment cleanup")
        return 0

    # ============================================================
    # Health Check
    # ============================================================

    async def health_check(self) -> Dict[str, Any]:
        """Verify M-Pesa configuration and connectivity."""
        status: Dict[str, Any] = {
            "service": "mpesa",
            "status": "healthy",
            "environment": settings.MPESA_ENVIRONMENT,
            "base_url": self.base_url,
            "checks": {
                "credentials": True,
                "oauth": False,
            },
        }

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

    def verify_callback_secret(self, callback_secret: Optional[str]) -> bool:
        """
        Verify the callback secret if one is configured.

        Returns True when no secret is configured or the supplied
        secret matches.
        """
        configured = getattr(settings, "MPESA_CALLBACK_SECRET", "")

        if not configured:
            return True

        return callback_secret == configured

    # ============================================================
    # Convenience Methods
    # ============================================================

    def is_configured(self) -> bool:
        """True if all required credentials exist."""
        return all([
            self.consumer_key,
            self.consumer_secret,
            self.passkey,
            self.shortcode,
            self.callback_url,
            self.base_url,
        ])

    async def close(self) -> None:
        """Reserved for future shared HTTP client cleanup."""
        return
