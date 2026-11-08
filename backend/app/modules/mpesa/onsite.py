
# app/modules/mpesa/onsite.py
# ================================================================
# Auto-D Kenya - M-Pesa for Onsite Valuations
#
# POST /mpesa/onsite/stkpush
#   Initiates an STK push for a cash-client valuation.
#
# POST /mpesa/onsite/callback
#   Processes Safaricom payment confirmation.
#
# Ownership:
#   - An officer can pay for their own valuation.
#   - A senior valuer with can_sign=true can pay for another
#     officer's valuation.
#   - Inactive or unregistered officers are rejected.
#
# Payment completion is handled by the database RPC:
#   onsite_stk_complete
# ================================================================

import asyncio
import logging
import time
from collections import defaultdict, deque
from typing import Any, Dict, Optional

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

_buckets: Dict[str, deque] = defaultdict(deque)

_stk: Optional[StkPushService] = None


# ================================================================
# Helpers
# ================================================================

def _rate_limit(key: str, max_requests: int = 5, window: int = 60) -> None:
    now = time.monotonic()
    bucket = _buckets[key]

    while bucket and now - bucket[0] > window:
        bucket.popleft()

    if len(bucket) >= max_requests:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Wait a minute and try again.",
        )

    bucket.append(now)


def _one(query) -> Optional[Dict[str, Any]]:
    """Return the first matching database row or None."""
    result = query.limit(1).execute()
    rows = (result.data if result else None) or []
    return rows[0] if rows else None


def _onsite_callback_url() -> str:
    """Resolve the dedicated onsite callback URL."""
    explicit = getattr(settings, "MPESA_ONSITE_CALLBACK_URL", "") or ""

    if explicit:
        return explicit

    base = (settings.MPESA_CALLBACK_URL or "").rstrip("/")

    if base.endswith("/mpesa/callback"):
        return (
            base[: -len("/mpesa/callback")]
            + "/mpesa/onsite/callback"
        )

    return (
        f"{settings.API_BASE_URL.rstrip('/')}"
        f"{settings.API_V1_PREFIX}/mpesa/onsite/callback"
    )


def _get_stk() -> StkPushService:
    """Return an STK service configured for onsite callbacks."""
    global _stk

    if _stk is None:
        if not settings.mpesa_configured:
            raise HTTPException(
                status_code=503,
                detail="M-Pesa is not configured on the server.",
            )

        _stk = StkPushService()
        _stk.callback_url = _onsite_callback_url()

        logger.info(
            "Onsite STK callback URL configured: %s",
            _stk.callback_url,
        )

    return _stk


def _resolve_officer(sb, current_user: dict) -> Dict[str, Any]:
    """
    Resolve the authenticated user to their valuation_officers row.

    get_current_user() returns a profiles row. Its user_id is the
    Supabase Auth UID. The profile's own id must not be assumed to
    be the valuation officer ID.

    The valuation_officers.id is the canonical officer identifier.
    """
    auth_uid = current_user.get("user_id")

    if not auth_uid:
        raise HTTPException(
            status_code=403,
            detail="Your login could not be linked to a valuation officer account.",
        )

    officer = _one(
        sb.table("valuation_officers")
        .select("id,active,role,can_sign")
        .eq("id", str(auth_uid))
    )

    if not officer:
        logger.warning(
            "No valuation officer found for authenticated UID=%s",
            auth_uid,
        )
        raise HTTPException(
            status_code=403,
            detail="No valuation officer profile was found for this login.",
        )

    if not officer.get("active"):
        raise HTTPException(
            status_code=403,
            detail="Your officer account is not active.",
        )

    return officer


def _can_pay_for_another_officer(officer: Dict[str, Any]) -> bool:
    return (
        officer.get("role") == "senior_valuer"
        and officer.get("can_sign") is True
    )


# ================================================================
# Request model
# ================================================================

class OnsiteStkRequest(BaseModel):
    valuation_id: str
    phone: str


# ================================================================
# STK Push
# ================================================================

@router.post("/mpesa/onsite/stkpush")
async def onsite_stk_push(
    body: OnsiteStkRequest,
    current_user: dict = Depends(get_current_user),
):
    sb = get_supabase()

    # Resolve the authenticated user to the actual officer record.
    officer = _resolve_officer(sb, current_user)

    # Always use the officer table ID as the canonical identity.
    officer_id = str(officer["id"])

    _rate_limit(f"onsite-stk:{officer_id}")

    # Validate phone number.
    try:
        phone = normalize_phone(body.phone)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    # Retrieve the requested valuation.
    valuation = _one(
        sb.table("onsite_valuations")
        .select(
            "id,ref,officer_id,purpose,client_id,fee,payment_status"
        )
        .eq("id", body.valuation_id)
    )

    if not valuation:
        raise HTTPException(
            status_code=404,
            detail="Valuation not found.",
        )

    # ------------------------------------------------------------
    # Ownership verification
    # ------------------------------------------------------------

    valuation_owner = str(valuation.get("officer_id") or "")

    is_owner = valuation_owner == officer_id
    is_authorized_senior = _can_pay_for_another_officer(officer)

    if not is_owner and not is_authorized_senior:
        logger.warning(
            "Onsite payment ownership denied | valuation=%s owner=%s caller=%s role=%s",
            valuation.get("id"),
            valuation_owner,
            officer_id,
            officer.get("role"),
        )

        raise HTTPException(
            status_code=403,
            detail="This valuation belongs to another officer.",
        )

    # ------------------------------------------------------------
    # Client verification
    # ------------------------------------------------------------

    client_id = valuation.get("client_id")

    if not client_id:
        raise HTTPException(
            status_code=400,
            detail="This valuation has no linked client.",
        )

    client = _one(
        sb.table("onsite_clients")
        .select("client_type")
        .eq("id", client_id)
    )

    if not client or client.get("client_type") != "cash":
        raise HTTPException(
            status_code=400,
            detail="Only cash clients pay per valuation.",
        )

    # ------------------------------------------------------------
    # Payment status verification
    # ------------------------------------------------------------

    if valuation.get("payment_status") == "paid":
        raise HTTPException(
            status_code=409,
            detail="This valuation is already paid.",
        )

    # ------------------------------------------------------------
    # Determine valuation fee
    # ------------------------------------------------------------

    fee = valuation.get("fee")

    if fee is None:
        pricing = _one(
            sb.table("onsite_pricing")
            .select("price")
            .eq("purpose", valuation.get("purpose"))
        )

        fee = pricing.get("price") if pricing else None

    try:
        amount = float(fee)
    except (TypeError, ValueError):
        amount = 0

    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="No valid fee is set for this service.",
        )

    account_ref = str(valuation.get("ref") or "AUTOD")[:12]

    # ------------------------------------------------------------
    # Initiate Safaricom STK push
    # ------------------------------------------------------------

    try:
        push = await _get_stk().initiate_push(
            phone=phone,
            amount=amount,
            description="Auto-D Valuation",
            user_id=officer_id,
            service_id=account_ref,
        )

    except AppException as exc:
        logger.exception(
            "Onsite STK initiation failed | valuation=%s",
            valuation.get("id"),
        )
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    checkout_id = push.get("checkout_request_id")

    if not checkout_id:
        raise HTTPException(
            status_code=502,
            detail="Safaricom did not return a checkout request ID.",
        )

    # ------------------------------------------------------------
    # Record STK request
    # ------------------------------------------------------------

    try:
        sb.table("onsite_stk_requests").insert(
            {
                "checkout_request_id": checkout_id,
                "merchant_request_id": push.get("merchant_request_id"),
                "valuation_id": valuation["id"],
                "user_id": officer_id,
                "phone": phone,
                "amount": amount,
            }
        ).execute()

    except Exception:
        logger.exception(
            "STK sent but request could not be recorded | checkout=%s",
            mask_sensitive(checkout_id),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "The payment prompt was sent but could not be recorded. "
                "Verify the payment before attempting another prompt."
            ),
        )

    logger.info(
        "Onsite STK initiated | valuation=%s officer=%s checkout=%s",
        valuation.get("ref"),
        officer_id,
        mask_sensitive(checkout_id),
    )

    return {
        "checkout_request_id": checkout_id,
        "status": "pending",
        "message": (
            push.get("customer_message")
            or "STK Push sent successfully."
        ),
    }


# ================================================================
# Safaricom Callback
# ================================================================

@router.post("/mpesa/onsite/callback")
async def onsite_callback(request: Request):
    accepted = JSONResponse(
        status_code=200,
        content={
            "ResultCode": 0,
            "ResultDesc": "Accepted",
        },
    )

    try:
        payload = await request.json()
    except Exception:
        logger.warning("Onsite callback received invalid JSON.")
        return accepted

    callback = (
        (payload.get("Body") or {}).get("stkCallback")
    )

    if not callback:
        logger.warning("Onsite callback missing stkCallback.")
        return accepted

    checkout_id = callback.get("CheckoutRequestID")

    if not checkout_id:
        return accepted

    result_code = str(callback.get("ResultCode"))

    metadata_items = (
        (callback.get("CallbackMetadata") or {}).get("Item", [])
    )

    metadata = {
        item.get("Name"): item.get("Value")
        for item in metadata_items
        if item.get("Name")
    }

    try:
        # Safaricom success callback must be independently verified.
        if result_code == "0":
            confirmed = False

            for attempt in range(3):
                try:
                    query_result = await _get_stk().query_payment(
                        checkout_id
                    )

                    confirmed = (
                        query_result.get("status") == "completed"
                    )

                    break

                except Exception:
                    if attempt == 2:
                        raise

                    await asyncio.sleep(2)

            if not confirmed:
                logger.error(
                    "Onsite callback not confirmed by Safaricom | checkout=%s",
                    mask_sensitive(checkout_id),
                )
                return accepted

        amount = metadata.get("Amount")
        phone_number = metadata.get("PhoneNumber")

        # Database function validates the checkout request and performs
        # the payment update atomically.
        result = (
            get_supabase()
            .rpc(
                "onsite_stk_complete",
                {
                    "p_checkout": checkout_id,
                    "p_code": result_code,
                    "p_desc": callback.get("ResultDesc", ""),
                    "p_receipt": metadata.get("MpesaReceiptNumber"),
                    "p_amount": (
                        float(amount)
                        if amount is not None
                        else None
                    ),
                    "p_phone": (
                        str(phone_number)
                        if phone_number
                        else None
                    ),
                },
            )
            .execute()
        )

        logger.info(
            "Onsite M-Pesa callback processed | checkout=%s result=%s",
            mask_sensitive(checkout_id),
            result.data,
        )

    except Exception:
        logger.exception(
            "Onsite callback processing failed | checkout=%s",
            mask_sensitive(checkout_id),
        )

    # Safaricom callbacks should receive an acknowledgement.
    return accepted
