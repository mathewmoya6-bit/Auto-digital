"""
Auto-D Kenya Flask Backend

Endpoints:

POST /api/mpesa/stkpush
    Start M-Pesa STK Push payment

POST /api/mpesa/callback
    Receive Safaricom payment callback

GET /api/mpesa/status/<checkout_id>
    Check payment status

GET /api/health
    Health check
"""

from __future__ import annotations

import logging
import os
import threading

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

from mpesa import (
    MpesaAPIError,
    MpesaClient,
    MpesaConfigError
)


# Load local .env during development
load_dotenv()


# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auto-d-backend")


# Flask app
app = Flask(__name__)


app.config["SECRET_KEY"] = os.getenv(
    "FLASK_SECRET_KEY",
    "development-secret"
)


# Allow frontend access
CORS(
    app,
    origins=[
        "https://auto-d.meipressgroup.com"
    ]
)


# Temporary payment storage
# Replace with database later if you need payment history
transactions = {}

transactions_lock = threading.Lock()



def get_client():

    try:
        return MpesaClient()

    except MpesaConfigError as e:
        logger.error(e)
        raise



@app.get("/api/health")
def health():

    return jsonify({
        "status": "ok",
        "service": "auto-d-backend"
    })



@app.post("/api/mpesa/stkpush")
def stkpush():

    data = request.get_json() or {}


    phone = data.get("phone")
    amount = data.get("amount")

    account_reference = data.get(
        "account_reference",
        "AUTO-D"
    )

    description = data.get(
        "description",
        "Vehicle valuation"
    )


    if not phone or not amount:

        return jsonify({
            "error":
            "phone and amount are required"
        }), 400



    try:

        amount = int(float(amount))

        if amount <= 0:
            raise ValueError


    except ValueError:

        return jsonify({
            "error":
            "Invalid amount"
        }), 400



    try:

        client = get_client()


        result = client.stk_push(

            phone_number=phone,

            amount=amount,

            account_reference=
            account_reference,

            transaction_desc=
            description
        )


    except MpesaConfigError as e:

        return jsonify({
            "error": str(e)
        }), 500


    except MpesaAPIError as e:

        return jsonify({
            "error": str(e)
        }), 502



    checkout_id = result.get(
        "CheckoutRequestID"
    )


    with transactions_lock:

        transactions[checkout_id] = {

            "status":
            "pending",

            "phone":
            client.normalize_phone(phone),

            "amount":
            amount

        }



    return jsonify({

        "message":
        "STK Push sent",

        "checkout_request_id":
        checkout_id

    })




@app.post("/api/mpesa/callback")
def mpesa_callback():

    payload = request.get_json() or {}


    logger.info(
        "M-Pesa callback: %s",
        payload
    )


    callback = (
        payload
        .get("Body", {})
        .get("stkCallback", {})
    )


    checkout_id = callback.get(
        "CheckoutRequestID"
    )


    result_code = callback.get(
        "ResultCode"
    )


    result_desc = callback.get(
        "ResultDesc"
    )


    receipt = None
    amount = None



    if result_code == 0:

        items = (
            callback
            .get("CallbackMetadata", {})
            .get("Item", [])
        )


        metadata = {

            item.get("Name"):
            item.get("Value")

            for item in items

        }


        receipt = metadata.get(
            "MpesaReceiptNumber"
        )


        amount = metadata.get(
            "Amount"
        )



    with transactions_lock:

        transactions[checkout_id] = {

            "status":
            "success"
            if result_code == 0
            else "failed",

            "result_code":
            result_code,

            "description":
            result_desc,

            "receipt":
            receipt,

            "amount":
            amount

        }



    return jsonify({

        "ResultCode": 0,

        "ResultDesc":
        "Accepted"

    })




@app.get("/api/mpesa/status/<checkout_id>")
def payment_status(checkout_id):

    with transactions_lock:

        payment = transactions.get(
            checkout_id
        )


    if not payment:

        return jsonify({

            "status":
            "unknown"

        }), 404



    return jsonify(payment)




if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            5000
        )
    )


    app.run(

        host="0.0.0.0",

        port=port,

        debug=False

    )
