import base64
import datetime
import os
import requests


class MpesaConfigError(Exception):
    pass


class MpesaAPIError(Exception):
    pass


class MpesaClient:

    def __init__(self):
        self.environment = os.getenv("MPESA_ENV", "sandbox")

        self.consumer_key = os.getenv("MPESA_CONSUMER_KEY")
        self.consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")
        self.shortcode = os.getenv("MPESA_SHORTCODE")
        self.passkey = os.getenv("MPESA_PASSKEY")
        self.callback_url = os.getenv("MPESA_CALLBACK_URL")

        if not all([
            self.consumer_key,
            self.consumer_secret,
            self.shortcode,
            self.passkey,
            self.callback_url
        ]):
            raise MpesaConfigError(
                "Missing M-Pesa environment variables"
            )


    def normalize_phone(self, phone):

        phone = str(phone).replace("+", "").replace(" ", "")

        if phone.startswith("0"):
            phone = "254" + phone[1:]

        if phone.startswith("7"):
            phone = "254" + phone

        return phone


    def get_access_token(self):

        url = (
            "https://api.safaricom.co.ke/oauth/v1/generate"
            "?grant_type=client_credentials"
        )

        response = requests.get(
            url,
            auth=(
                self.consumer_key,
                self.consumer_secret
            ),
            timeout=30
        )

        if response.status_code != 200:
            raise MpesaAPIError(
                response.text
            )

        return response.json()["access_token"]


    def stk_push(
        self,
        phone_number,
        amount,
        account_reference,
        transaction_desc
    ):

        token = self.get_access_token()

        timestamp = datetime.datetime.now().strftime(
            "%Y%m%d%H%M%S"
        )

        password_string = (
            self.shortcode +
            self.passkey +
            timestamp
        )

        password = base64.b64encode(
            password_string.encode()
        ).decode()


        url = (
            "https://api.safaricom.co.ke/"
            "mpesa/stkpush/v1/processrequest"
        )


        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType":
                "CustomerPayBillOnline",

            "Amount": amount,

            "PartyA":
                self.normalize_phone(phone_number),

            "PartyB":
                self.shortcode,

            "PhoneNumber":
                self.normalize_phone(phone_number),

            "CallBackURL":
                self.callback_url,

            "AccountReference":
                account_reference,

            "TransactionDesc":
                transaction_desc
        }


        headers = {
            "Authorization":
                f"Bearer {token}",

            "Content-Type":
                "application/json"
        }


        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )


        if response.status_code != 200:
            raise MpesaAPIError(
                response.text
            )


        data = response.json()


        if data.get("ResponseCode") != "0":
            raise MpesaAPIError(
                data.get(
                    "errorMessage",
                    "STK push failed"
                )
            )


        return data
