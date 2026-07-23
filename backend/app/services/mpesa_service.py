"""
Auto-D Kenya
M-Pesa Business Logic
"""

import base64
import logging
import requests

from datetime import datetime
from app.core.config import settings
from app.core.database import supabase

logger = logging.getLogger(__name__)


class MpesaService:

    def __init__(self):

        self.environment = settings.MPESA_ENV
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.callback_url = settings.MPESA_CALLBACK_URL

        if self.environment == "production":
            self.base_url = "https://api.safaricom.co.ke"
        else:
            self.base_url = "https://sandbox.safaricom.co.ke"

    ###########################################################
    # Configuration
    ###########################################################

    def is_configured(self):

        return all([
            self.consumer_key,
            self.consumer_secret,
            self.shortcode,
            self.passkey,
            self.callback_url
        ])

    ###########################################################
    # Access Token
    ###########################################################

    def get_access_token(self):

        auth = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {auth}"
        }

        url = (
            f"{self.base_url}"
            "/oauth/v1/generate?grant_type=client_credentials"
        )

        response = requests.get(url, headers=headers, timeout=30)

        response.raise_for_status()

        return response.json()["access_token"]

    ###########################################################
    # STK Push
    ###########################################################

    async def initiate_stk_push(
        self,
        phone,
        amount,
        account_reference,
        description,
        user_id=None
    ):
        """
        Sends STK Push
        Saves pending payment
        """

        pass

    ###########################################################
    # Callback
    ###########################################################

    def process_callback(self, callback):

        """
        Update payment

        pending
            ↓

        completed

        OR

        failed
        """

        pass

    ###########################################################
    # Payment Status
    ###########################################################

    def get_payment_status(self, checkout_request_id):

        response = (
            supabase
            .table("payments")
            .select("*")
            .eq("checkout_request_id", checkout_request_id)
            .limit(1)
            .execute()
        )

        if not response.data:

            return {
                "success": False,
                "error": "Payment not found"
            }

        payment = response.data[0]

        return {
            "success": True,
            "checkout_request_id": payment["checkout_request_id"],
            "status": payment["status"],
            "amount": payment["amount"],
            "service_id": payment.get("service_id"),
            "created_at": payment["created_at"]
        }

    ###########################################################
    # Manual Confirmation
    ###########################################################

    def confirm_payment_manually(
        self,
        checkout_request_id,
        user_id
    ):

        pass

    ###########################################################
    # Services
    ###########################################################

    def get_all_services(self):

        return [
            {
                "service_id": "mileage",
                "name": "Mileage Calculator",
                "price": 1
            },
            {
                "service_id": "valuation",
                "name": "Vehicle Valuation",
                "price": 1000
            },
            {
                "service_id": "inspection",
                "name": "Vehicle Inspection",
                "price": 2500
            },
            {
                "service_id": "running_cost",
                "name": "Running Cost",
                "price": 500
            }
        ]

    def get_service_name(self, service_id):

        for service in self.get_all_services():

            if service["service_id"] == service_id:
                return service["name"]

        return service_id

    ###########################################################
    # User Services
    ###########################################################

    def get_user_services(self, user_id):

        response = (
            supabase
            .table("user_services")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )

        return response.data or []
