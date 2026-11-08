# app/modules/mpesa/onsite.py
# ================================================================
# Auto-D Kenya - M-Pesa for the Onsite Valuation app
#   POST /mpesa/onsite/stkpush   (officer app: cash client pays a valuation fee)
#   POST /mpesa/onsite/callback  (Safaricom confirms the payment)
# Marks onsite_valuations as paid through the SQL function
# onsite_stk_complete (see onsite_stk.sql), so the database stays the
# single source of truth for the payment lock and the certificate.
# ================================================================

import asyncio
import logging
import time
from collections import defaultdict, deque
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_supabase
from app.core.dependencies import get_current_user
from app.core.exceptions import AppException
from app.core.security import mask_sensitive
from app.modules.mpesa.stk_push import StkPushService, normalize_phone

logger = logging.getLogger(__name__)

router = APIRouter(tags=["M-Pesa Onsite"])


# ================================================================
# Helpers
# ================================================================

_buckets: Dict[str, deque] = defaultdict(deque)


def _rate_limit(key: str, max_requests: int = 5, window: int = 60) -> None:
    now = time.monotonic()
    bucket = _buckets[key]
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    if len(bucket) >= max_requests:
        raise HTTPException(status_code=429, detail="Too many requests. Wait a minute and try again.")
    bucket.append(now)


def _onsite_callback_url() -> str:
    """Callback for onsite pushes. Derived from MPESA_CALLBACK_URL unless MPESA_ONSITE_CALLBACK_URL is set."""
    explicit = getattr(settings, "MPESA_ONSITE_CALLBACK_URL", "") or ""
    if explicit:
        return explicit
    base = (settings.MPESA_CALLBACK_URL or "").rstrip("/")
    if base.endswith("/mpesa/callback"):
        return base[: -len("/mpesa/callback")] + "/mpesa/onsite/callback"
    return f"{settings.API_BASE_URL.rstrip('/')}{settings.API_V1_PREFIX}/mpesa/onsite/callback"


_stk: StkPushService | None = None


def _get_stk() -> StkPushService:
    """Separate STK client so onsite pushes use the onsite callback URL."""
    global _stk
    if _stk is None:
        if not settings.mpesa_configured:
            raise HTTPException(status_code=503, detail="M-Pesa is not configured on the server.")
        _stk = StkPushService()
        _stk.callback_url = _onsite_callback_url()
        logger.info("Onsite STK callback URL: %s", _stk.callback_url)
    return _stk


def _one(query) -> Dict[str, Any] | None:
    res = query.maybe_single().execute()
    return res.data if res else None


def _rows(query) -> list:
    """Plain select that never raises on 'no rows' (unlike maybe_single on some client versions)."""
    res = query.execute()
    return (res.data if res else None) or []


# ================================================================
# STK Push
# ================================================================

class OnsiteStkRequest(BaseModel):
    valuation_id: str
    phone: str


@router.post("/mpesa/onsite/stkpush")
async def onsite_stk_push(
    body: OnsiteStkRequest,
    current_user: dict = Depends(get_current_user),
):
    uid = str(current_user["id"])
    _rate_limit(f"onsite-stk:{uid}")

    try:
        phone = normalize_phone(body.phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    sb = get_supabase()

    # Separate "no profile found" from "profile inactive" so the cause is visible.
    found = _rows(
        sb.table("valuation_officers").select("id,active,role,can_sign").eq("id", uid).limit(1)
    )
    officer = found[0] if found else None
    if not officer:
        logger.warning(
            "Onsite STK: no valuation_officers row for id=%s | current_user keys=%s | "
            "check that get_supabase() uses the service-role key and that this id is the Supabase auth uid",
            uid, sorted(current_user.keys()),
        )
        raise HTTPException(status_code=403, detail="No officer profile was found for this login.")
    if not officer.get("active"):
        raise HTTPException(status_code=403, detail="Your officer account is not active.")

    val = _one(
        sb.table("onsite_valuations")
        .select("id,ref,officer_id,purpose,client_id,fee,payment_status")
        .eq("id", body.valuation_id)
    )
    is_billing = officer.get("role") == "senior_valuer" and bool(officer.get("can_sign"))
    if not val or (str(val.get("officer_id")) != uid and not is_billing):
        raise HTTPException(status_code=404, detail="Valuation not found.")

    client = _one(sb.table("onsite_clients").select("client_type").eq("id", val.get("client_id"))) if val.get("client_id") else None
    if not client or client.get("client_type") != "cash":
        raise HTTPException(status_code=400, detail="Only cash clients pay per valuation.")
    if val.get("payment_status") == "paid":
        raise HTTPException(status_code=409, detail="This valuation is already paid.")

    fee = val.get("fee")
    if fee is None:
        price = _one(sb.table("onsite_pricing").select("price").eq("purpose", val.get("purpose")))
        fee = price.get("price") if price else None
    if not fee or float(fee) <= 0:
        raise HTTPException(status_code=400, detail="No fee is set for this service.")

    account_ref = str(val.get("ref") or "AUTOD")[:12]

    try:
        push = await _get_stk().initiate_push(
            phone=phone,
            amount=float(fee),
            description="Auto-D Valuation",
            user_id=uid,
            service_id=account_ref,  # becomes the M-Pesa AccountReference
        )
    except AppException as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    checkout_id = push.get("checkout_request_id")
    try:
        sb.table("onsite_stk_requests").insert({
            "checkout_request_id": checkout_id,
            "merchant_request_id": push.get("merchant_request_id"),
            "valuation_id": val["id"],
            "user_id": uid,
            "phone": phone,
            "amount": float(fee),
        }).execute()
    except Exception:
        logger.exception("Onsite STK sent but could not be recorded | checkout=%s", checkout_id)
        raise HTTPException(
            status_code=500,
            detail="The prompt was sent but could not be recorded. If the client pays, enter the M-Pesa code manually.",
        )

    logger.info("Onsite STK | valuation=%s checkout=%s", val.get("ref"), mask_sensitive(checkout_id))
    return {
        "checkout_request_id": checkout_id,
        "status": "pending",
        "message": push.get("customer_message") or "STK Push sent successfully.",
    }


# ================================================================
# Callback
# ================================================================

@router.post("/mpesa/onsite/callback")
async def onsite_callback(request: Request):
    accepted = JSONResponse(status_code=200, content={"ResultCode": 0, "ResultDesc": "Accepted"})

    try:
        payload = await request.json()
    except Exception:
        logger.warning("Onsite callback: invalid JSON")
        return accepted

    cb = (payload.get("Body") or {}).get("stkCallback")
    if not cb or not cb.get("CheckoutRequestID"):
        return accepted

    checkout_id = cb["CheckoutRequestID"]
    code = str(cb.get("ResultCode"))
    meta = {
        i.get("Name"): i.get("Value")
        for i in (cb.get("CallbackMetadata") or {}).get("Item", [])
        if i.get("Name")
    }

    try:
        if code == "0":
            # The callback URL is public, so never trust it alone: confirm with Safaricom first.
            confirmed = False
            for attempt in range(3):
                try:
                    q = await _get_stk().query_payment(checkout_id)
                    confirmed = q.get("status") == "completed"
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2)
            if not confirmed:
                logger.error("Onsite callback not confirmed by Safaricom | checkout=%s", mask_sensitive(checkout_id))
                return accepted

        amount = meta.get("Amount")
        res = get_supabase().rpc("onsite_stk_complete", {
            "p_checkout": checkout_id,
            "p_code": code,
            "p_desc": cb.get("ResultDesc", ""),
            "p_receipt": meta.get("MpesaReceiptNumber"),
            "p_amount": float(amount) if amount is not None else None,
            "p_phone": str(meta["PhoneNumber"]) if meta.get("PhoneNumber") else None,
        }).execute()
        logger.info("Onsite callback | checkout=%s result=%s", mask_sensitive(checkout_id), res.data)
    except Exception:
        logger.exception("Onsite callback processing failed | checkout=%s", mask_sensitive(checkout_id))

    return accepted
