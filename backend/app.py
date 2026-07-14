"""
app.py
──────
Flask backend for Auto-D Kenya's M-Pesa payment flow.

Endpoints
    POST /api/mpesa/stkpush      -> trigger an STK push prompt on the customer's phone
    POST /api/mpesa/callback     -> Safaricom posts the payment result here
    GET  /api/mpesa/status/<id>  -> frontend polls this to check payment status
    GET  /api/health             -> simple health check

Run locally:
    cp .env.example .env      # then fill in real values
    pip install -r requirements.txt
    python app.py

In production, put this behind gunicorn + a reverse proxy (nginx) over HTTPS,
and make sure MPESA_CALLBACK_URL points at this server's public /api/mpesa/callback.
"""

from __future__ import annotations

import logging
import os
import threading

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()  # reads .env in local/dev; in prod set real env vars on the host instead

from mpesa import MpesaAPIError, MpesaClient, MpesaConfigError  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-only-change-me")
CORS(app)  # tighten origins in production, e.g. CORS(app, origins=["https://yourdomain.com"])

# In-memory store for demo purposes only.
# Swap this for a real database (Postgres/SQLite/etc.) before going to production —
# an in-memory dict does not survive a restart and won't work across multiple workers.
_transactions_lock = threading.Lock()
transactions: dict[str, dict] = {}


def get_mpesa_client() -> MpesaClient:
    try:
        return MpesaClient()
    except MpesaConfigError as exc:
        logger.error(str(exc))
        raise


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/mpesa/stkpush")
def stk_push():
    """
    Body JSON:
    {
        "phone": "0712345678",
        "amount": 100,
        "account_reference": "AUTO-D-1234",
        "description": "Vehicle valuation report"
    }
    """
    body = request.get_json(silent=True) or {}
    phone = body.get("phone")
    amount = body.get("amount")
    account_reference = body.get("account_reference", "Auto-D Kenya")
    description = body.get("description", "Payment")

    if not phone or not amount:
        return jsonify({"error": "phone and amount are required"}), 400

    try:
        amount = int(round(float(amount)))
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "amount must be a positive number"}), 400

    try:
        client = get_mpesa_client()
        result = client.stk_push(
            phone_number=phone,
            amount=amount,
            account_reference=account_reference,
            transaction_desc=description,
        )
    except MpesaConfigError as exc:
        return jsonify({"error": str(exc)}), 500
    except MpesaAPIError as exc:
        return jsonify({"error": str(exc)}), 502

    checkout_id = result.get("CheckoutRequestID")
    with _transactions_lock:
        transactions[checkout_id] = {
            "status": "pending",
            "phone": client.normalize_phone(phone),
            "amount": amount,
            "account_reference": account_reference,
            "raw_request": result,
        }

    return jsonify(
        {
            "message": "STK push sent. Ask the customer to check their phone and enter their M-Pesa PIN.",
            "checkout_request_id": checkout_id,
            "merchant_request_id": result.get("MerchantRequestID"),
        }
    )


@app.post("/api/mpesa/callback")
def mpesa_callback():
    """Safaricom POSTs the final payment result here. Must be a public HTTPS URL."""
    payload = request.get_json(silent=True) or {}
    logger.info("M-Pesa callback received: %s", payload)

    stk_callback = (payload.get("Body") or {}).get("stkCallback") or {}
    checkout_id = stk_callback.get("CheckoutRequestID")
    result_code = stk_callback.get("ResultCode")
    result_desc = stk_callback.get("ResultDesc")

    receipt_number = None
    paid_amount = None
    if result_code == 0:
        items = (stk_callback.get("CallbackMetadata") or {}).get("Item", [])
        meta = {item.get("Name"): item.get("Value") for item in items}
        receipt_number = meta.get("MpesaReceiptNumber")
        paid_amount = meta.get("Amount")

    with _transactions_lock:
        if checkout_id in transactions:
            transactions[checkout_id].update(
                {
                    "status": "success" if result_code == 0 else "failed",
                    "result_code": result_code,
                    "result_desc": result_desc,
                    "receipt_number": receipt_number,
                    "paid_amount": paid_amount,
                }
            )
        else:
            transactions[checkout_id] = {
                "status": "success" if result_code == 0 else "failed",
                "result_code": result_code,
                "result_desc": result_desc,
                "receipt_number": receipt_number,
                "paid_amount": paid_amount,
            }

    # Always acknowledge receipt so Safaricom doesn't retry the callback.
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})


@app.get("/api/mpesa/status/<checkout_request_id>")
def mpesa_status(checkout_request_id: str):
    """Frontend polls this after triggering an STK push to see if payment completed."""
    with _transactions_lock:
        record = transactions.get(checkout_request_id)

    if not record:
        return jsonify({"status": "unknown"}), 404

    return jsonify(record)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    # debug=False in anything resembling production
    app.run(host="0.0.0.0", port=port, debug=os.getenv("MPESA_ENV") != "production")
