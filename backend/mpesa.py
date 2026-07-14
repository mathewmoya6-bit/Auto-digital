"""
mpesa.py
────────
Thin client around Safaricom's Daraja API (Lipa Na M-Pesa Online / STK Push).

All secrets are read from environment variables — nothing is hardcoded.
Set them in a local ".env" file (see .env.example) which is loaded by app.py
via python-dotenv. Never commit ".env" to version control.
"""

from __future__ import annotations

import base64
import datetime
import logging
import os

import requests

logger = logging.getLogger("mpesa")

BASE_URLS = {
    "production": "https://api.safaricom.co.ke",
    "sandbox": "https://sandbox.safaricom.co.ke",
}


class MpesaConfigError(RuntimeError):
    """Raised when required M-Pesa environment variables are missing."""


class MpesaAPIError(RuntimeError):
    """Raised when the Daraja API returns an error response."""


class MpesaClient:
    def __init__(self) -> None:
        self.env = os.getenv("MPESA_ENV", "sandbox").lower()
        self.base_url = BASE_URLS.get(self.env, BASE_URLS["sandbox"])

        self.consumer_key = os.getenv("MPESA_CONSUMER_KEY")
        self.consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")
        self.shortcode = os.getenv("MPESA_SHORTCODE")
        self.passkey = os.getenv("MPESA_PASSKEY")
        self.transaction_type = os.getenv(
            "MPESA_TRANSACTION_TYPE", "CustomerPayBillOnline"
        )
        self.callback_url = os.getenv("MPESA_CALLBACK_URL")

        missing = [
            name
            for name, val in [
                ("MPESA_CONSUMER_KEY", self.consumer_key),
                ("MPESA_CONSUMER_SECRET", self.consumer_secret),
                ("MPESA_SHORTCODE", self.shortcode),
                ("MPESA_PASSKEY", self.passkey),
                ("MPESA_CALLBACK_URL", self.callback_url),
            ]
            if not val
        ]
        if missing:
            raise MpesaConfigError(
                f"Missing required M-Pesa environment variables: {', '.join(missing)}. "
                "Set them in your .env file (see .env.example)."
            )

    # ── Auth ────────────────────────────────────────────────────────────
    def get_access_token(self) -> str:
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        resp = requests.get(
            url,
            auth=(self.consumer_key, self.consumer_secret),
            timeout=15,
        )
        if resp.status_code != 200:
            logger.error("Failed to get access token: %s %s", resp.status_code, resp.text)
            raise MpesaAPIError(f"Could not authenticate with Daraja: {resp.text}")
        return resp.json()["access_token"]

    # ── Helpers ─────────────────────────────────────────────────────────
    @staticmethod
    def _timestamp() -> str:
        return datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    def _password(self, timestamp: str) -> str:
        raw = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(raw.encode()).decode()

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Convert local formats (07xx, +2547xx) to the 2547xxxxxxxx format Daraja expects."""
        phone = phone.strip().replace(" ", "").replace("-", "")
        if phone.startswith("+"):
            phone = phone[1:]
        if phone.startswith("0") and len(phone) == 10:
            phone = "254" + phone[1:]
        if phone.startswith("7") or phone.startswith("1"):
            phone = "254" + phone
        return phone

    # ── STK Push ────────────────────────────────────────────────────────
    def stk_push(
        self,
        phone_number: str,
        amount: int,
        account_reference: str,
        transaction_desc: str = "Payment",
    ) -> dict:
        """Trigger an STK Push (Lipa Na M-Pesa Online) prompt on the customer's phone."""
        token = self.get_access_token()
        timestamp = self._timestamp()
        password = self._password(timestamp)
        phone = self.normalize_phone(phone_number)

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": self.transaction_type,
            "Amount": int(amount),
            "PartyA": phone,
            "PartyB": self.shortcode,
            "PhoneNumber": phone,
            "CallBackURL": self.callback_url,
            "AccountReference": account_reference[:12],
            "TransactionDesc": transaction_desc[:13],
        }

        resp = requests.post(
            f"{self.base_url}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        data = resp.json()
        if resp.status_code != 200 or data.get("ResponseCode") not in ("0", 0):
            logger.error("STK push failed: %s", data)
            raise MpesaAPIError(data.get("errorMessage", "STK push request failed"))
        return data

    # ── STK Query (poll transaction status) ────────────────────────────
    def stk_query(self, checkout_request_id: str) -> dict:
        token = self.get_access_token()
        timestamp = self._timestamp()
        password = self._password(timestamp)

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        resp = requests.post(
            f"{self.base_url}/mpesa/stkpushquery/v1/query",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        data = resp.json()
        if resp.status_code != 200:
            logger.error("STK query failed: %s", data)
            raise MpesaAPIError(data.get("errorMessage", "STK query failed"))
        return data
