# app/modules/mpesa/stk_push.py
# ================================================================
# Auto-D Kenya - M-Pesa STK Push Service
# ================================================================

import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


class StkPushService:
    """
    M-Pesa STK Push service for initiating and checking payments.
    """

    def __init__(self):
        """Initialize the STK Push service."""
        self.enabled = settings.MPESA_ENABLED
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE
        self.callback_url = settings.MPESA_CALLBACK_URL
        self.environment = settings.MPESA_ENVIRONMENT  # "sandbox" or "production"

        # Set base URLs
        if self.environment == "sandbox":
            self.base_url = "https://sandbox.safaricom.co.ke"
        else:
            self.base_url = "https://api.safaricom.co.ke"

        self._access_token = None
        self._token_expiry = None

    # ================================================================
    # AUTHENTICATION
    # ================================================================

    async def _get_access_token(self) -> str:
        """
        Get OAuth access token from Safaricom.

        Returns:
            Access token string

        Raises:
            HTTPException: If token retrieval fails
        """
        # Check if token is still valid
        if self._access_token and self._token_expiry:
            if datetime.now(timezone.utc) < self._token_expiry:
                return self._access_token

        if not self.consumer_key or not self.consumer_secret:
            raise HTTPException(
                status_code=500,
                detail="M-Pesa credentials not configured"
            )

        # Encode credentials
        credentials = f"{self.consumer_key}:{self.consumer_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
                    headers={
                        "Authorization": f"Basic {encoded_credentials}",
                        "Content-Type": "application/json",
                    },
                )

                response.raise_for_status()
                data = response.json()

                token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)

                if not token:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to get access token"
                    )

                # Cache token with 60-second buffer
                self._access_token = token
                self._token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)

                logger.info("M-Pesa access token obtained successfully")
                return token

        except httpx.TimeoutException:
            logger.error("M-Pesa token request timed out")
            raise HTTPException(
                status_code=504,
                detail="M-Pesa service timeout"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"M-Pesa token request failed: {e.response.text}")
            raise HTTPException(
                status_code=502,
                detail=f"M-Pesa service error: {e.response.status_code}"
            )
        except Exception as e:
            logger.exception(f"M-Pesa token request failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get M-Pesa token: {str(e)}"
            )

    # ================================================================
    # STK PUSH INITIATION
    # ================================================================

    async def initiate_stk_push(
        self,
        phone: str,
        amount: float,
        account_reference: str,
        transaction_desc: str,
        callback_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Initiate an STK Push payment request.

        Args:
            phone: Customer phone number (2547XXXXXXXX format)
            amount: Amount to charge
            account_reference: Reference for the transaction
            transaction_desc: Description of the transaction
            callback_url: Optional override for callback URL

        Returns:
            Dict containing checkout_request_id and customer_message

        Raises:
            HTTPException: If STK Push fails
        """
        if not self.enabled:
            raise HTTPException(
                status_code=503,
                detail="M-Pesa service is currently disabled"
            )

        # Format phone number (ensure 2547XXXXXXXX format)
        formatted_phone = self._format_phone_number(phone)

        if not self.shortcode:
            raise HTTPException(
                status_code=500,
                detail="M-Pesa shortcode not configured"
            )

        if not self.passkey:
            raise HTTPException(
                status_code=500,
                detail="M-Pesa passkey not configured"
            )

        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        # Generate password
        password = self._generate_password(timestamp)

        # Prepare payload
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": formatted_phone,
            "PartyB": self.shortcode,
            "PhoneNumber": formatted_phone,
            "CallBackURL": callback_url or self.callback_url,
            "AccountReference": account_reference[:20],  # Max 20 characters
            "TransactionDesc": transaction_desc[:20],    # Max 20 characters
        }

        logger.info(
            f"Initiating STK Push | "
            f"phone=***{phone[-4:]} "
            f"amount={amount} "
            f"reference={account_reference}"
        )

        try:
            token = await self._get_access_token()

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                response.raise_for_status()
                data = response.json()

                logger.info(
                    f"STK Push response | "
                    f"checkout_request_id={data.get('CheckoutRequestID')} "
                    f"result_code={data.get('ResponseCode')}"
                )

                # Check response
                result_code = data.get("ResponseCode")
                if result_code != "0":
                    error_message = data.get("ResponseDescription", "STK Push failed")
                    logger.error(f"STK Push failed: {error_message}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"STK Push failed: {error_message}"
                    )

                return {
                    "checkout_request_id": data.get("CheckoutRequestID"),
                    "customer_message": data.get("CustomerMessage", "STK Push sent successfully."),
                    "merchant_request_id": data.get("MerchantRequestID"),
                    "response_code": result_code,
                }

        except httpx.TimeoutException:
            logger.error("STK Push request timed out")
            raise HTTPException(
                status_code=504,
                detail="M-Pesa service timeout"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"STK Push request failed: {e.response.text}")
            raise HTTPException(
                status_code=502,
                detail=f"M-Pesa service error: {e.response.status_code}"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"STK Push failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"STK Push failed: {str(e)}"
            )

    # ================================================================
    # PAYMENT STATUS CHECK
    # ================================================================

    async def check_payment_status(
        self,
        checkout_request_id: str,
    ) -> Dict[str, Any]:
        """
        Check the status of an STK Push payment.

        Args:
            checkout_request_id: The checkout request ID from initiation

        Returns:
            Dict containing status, result_code, and result_desc

        Raises:
            HTTPException: If status check fails
        """
        if not self.enabled:
            raise HTTPException(
                status_code=503,
                detail="M-Pesa service is currently disabled"
            )

        if not self.shortcode:
            raise HTTPException(
                status_code=500,
                detail="M-Pesa shortcode not configured"
            )

        if not self.passkey:
            raise HTTPException(
                status_code=500,
                detail="M-Pesa passkey not configured"
            )

        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        # Generate password
        password = self._generate_password(timestamp)

        # Prepare payload
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        logger.info(f"Checking payment status: {checkout_request_id}")

        try:
            token = await self._get_access_token()

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/mpesa/stkpushquery/v1/query",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                response.raise_for_status()
                data = response.json()

                result_code = data.get("ResultCode")
                status_map = {
                    "0": "completed",      # Success
                    "1": "failed",         # Failed
                    "1032": "failed",      # Cancelled by user
                    "1037": "failed",      # Transaction failed
                    "2000": "pending",     # Processing
                    "2001": "pending",     # Processing
                }

                status = status_map.get(result_code, "pending")

                logger.info(
                    f"Payment status: {checkout_request_id} -> {status} "
                    f"(result_code={result_code})"
                )

                return {
                    "status": status,
                    "result_code": result_code,
                    "result_desc": data.get("ResultDesc", "Unknown status"),
                    "amount": data.get("Amount"),
                    "receipt_number": data.get("MpesaReceiptNumber"),
                    "transaction_date": data.get("TransactionDate"),
                }

        except httpx.TimeoutException:
            logger.error(f"Payment status check timed out: {checkout_request_id}")
            raise HTTPException(
                status_code=504,
                detail="M-Pesa service timeout"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Payment status check failed: {e.response.text}")
            raise HTTPException(
                status_code=502,
                detail=f"M-Pesa service error: {e.response.status_code}"
            )
        except Exception as e:
            logger.exception(f"Payment status check failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to check payment status: {str(e)}"
            )

    # ================================================================
    # HELPERS
    # ================================================================

    def _generate_password(self, timestamp: str) -> str:
        """
        Generate the M-Pesa password.

        Args:
            timestamp: Timestamp in YYYYMMDDHHMMSS format

        Returns:
            Base64 encoded password string
        """
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password_bytes = password_str.encode("ascii")
        encoded = base64.b64encode(password_bytes)
        return encoded.decode("ascii")

    def _format_phone_number(self, phone: str) -> str:
        """
        Format phone number to 2547XXXXXXXX format.

        Args:
            phone: Raw phone number

        Returns:
            Formatted phone number
        """
        # Remove any whitespace, dashes, or plus signs
        cleaned = ''.join(filter(str.isdigit, phone))

        # If it starts with 0, replace with 254
        if cleaned.startswith('0'):
            cleaned = '254' + cleaned[1:]
        # If it starts with 7, add 254
        elif cleaned.startswith('7'):
            cleaned = '254' + cleaned
        # If it starts with 254, keep as is
        elif cleaned.startswith('254'):
            pass
        # If it starts with +254, remove the plus
        elif cleaned.startswith('254'):
            pass
        else:
            # Assume it's a local number, add 254
            cleaned = '254' + cleaned

        # Ensure length is correct (254 + 9 digits = 12)
        if len(cleaned) != 12:
            logger.warning(f"Phone number length is {len(cleaned)}, expected 12 digits")

        return cleaned

    # ================================================================
    # HEALTH CHECK
    # ================================================================

    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the STK Push service.

        Returns:
            Dict with health status
        """
        if not self.enabled:
            return {
                "status": "disabled",
                "message": "M-Pesa service is disabled",
            }

        status = {
            "status": "healthy",
            "service": "stk_push",
            "enabled": self.enabled,
            "environment": self.environment,
            "checks": {
                "credentials": False,
                "connectivity": False,
            },
        }

        # Check credentials
        if self.consumer_key and self.consumer_secret and self.passkey and self.shortcode:
            status["checks"]["credentials"] = True

        # Check connectivity by trying to get token
        try:
            token = await self._get_access_token()
            if token:
                status["checks"]["connectivity"] = True
        except Exception:
            status["checks"]["connectivity"] = False

        # Determine overall status
        if not status["checks"]["credentials"]:
            status["status"] = "unhealthy"
            status["message"] = "Missing credentials"
        elif not status["checks"]["connectivity"]:
            status["status"] = "degraded"
            status["message"] = "Cannot connect to M-Pesa"
        else:
            status["status"] = "healthy"
            status["message"] = "Service is operational"

        return status
