"""
M-Pesa API
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.database import supabase
from app.core.security import (
    get_current_user,
    verify_admin,
    verify_api_key,
)
from app.services.mpesa_service import MpesaService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["M-Pesa"])

mpesa_service = MpesaService()


# ==========================================================
# HEALTH
# ==========================================================

@router.get("/mpesa/test")
async def test():
    return {
        "success": True,
        "message": "M-Pesa router loaded",
        "environment": mpesa_service.environment,
        "shortcode": mpesa_service.shortcode,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/mpesa/health")
async def health():
    return {
        "success": True,
        "configured": mpesa_service.is_configured(),
        "environment": mpesa_service.environment,
        "shortcode": mpesa_service.shortcode,
        "callback_url": mpesa_service.callback_url,
    }


@router.get("/mpesa/shortcode")
async def shortcode():
    return {
        "success": True,
        "shortcode": mpesa_service.shortcode,
        "environment": mpesa_service.environment,
    }


# ==========================================================
# STK PUSH
# ==========================================================

@router.post("/mpesa/stkpush")
async def stkpush(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    Initiate an M-Pesa STK Push.
    """

    try:
        body = await request.json()

        phone = body.get("phone")
        amount = body.get("amount")
        account_reference = body.get("account_reference", "AUTO-D")
        description = body.get("description", "Auto-D Payment")

        if not phone:
            raise HTTPException(
                status_code=400,
                detail="Phone number is required."
            )

        if amount is None:
            raise HTTPException(
                status_code=400,
                detail="Amount is required."
            )

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail="Amount must be numeric."
            )

        if amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="Amount must be greater than zero."
            )

        logger.info(
            f"Initiating STK Push | user={current_user['id']} | phone={phone} | amount={amount}"
        )

        result = await mpesa_service.initiate_stk_push(
            phone=phone,
            amount=amount,
            account_reference=account_reference,
            description=description,
            user_id=current_user["id"],
        )

        # --------------------------------------------------
        # Defensive checks
        # --------------------------------------------------

        if result is None:
            logger.error("MpesaService returned None")

            raise HTTPException(
                status_code=500,
                detail="M-Pesa service returned no response."
            )

        if not isinstance(result, dict):
            logger.error(
                f"Unexpected response type: {type(result)}"
            )

            raise HTTPException(
                status_code=500,
                detail="Invalid response from M-Pesa service."
            )

        if not result.get("success", False):

            error = (
                result.get("error")
                or result.get("message")
                or "Failed to initiate STK Push."
            )

            logger.error(f"STK Push failed: {error}")

            raise HTTPException(
                status_code=400,
                detail=error
            )

        logger.info("STK Push initiated successfully.")

        return result

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error during STK Push")

        raise HTTPException(
            status_code=500,
            detail="Internal server error while initiating STK Push."
        )


# ==========================================================
# CALLBACK
# ==========================================================

@router.post("/mpesa/callback")
async def callback(request: Request):

    try:
        data = await request.json()

        logger.info("Received M-Pesa callback")

        success = mpesa_service.process_callback(data)

        return {
            "ResultCode": 0 if success else 1,
            "ResultDesc": "Success" if success else "Failed"
        }

    except Exception:
        logger.exception("Callback processing failed")

        return {
            "ResultCode": 1,
            "ResultDesc": "Processing Failed"
        }


# ==========================================================
# PAYMENT STATUS
# ==========================================================

@router.get("/mpesa/status/{checkout_request_id}")
async def payment_status(checkout_request_id: str):

    logger.info(f"Checking payment {checkout_request_id}")

    result = mpesa_service.get_payment_status(checkout_request_id)

    if result is None:
        result = {
            "success": False,
            "error": "Payment not found."
        }

    return JSONResponse(
        status_code=200 if result.get("success") else 404,
        content=result
    )


# ==========================================================
# MANUAL CONFIRM
# ==========================================================

@router.post("/mpesa/confirm/{checkout_request_id}")
async def confirm(
    checkout_request_id: str,
    current_user: dict = Depends(get_current_user),
):

    result = mpesa_service.confirm_payment_manually(
        checkout_request_id,
        current_user["id"],
    )

    if result is None:
        raise HTTPException(
            status_code=500,
            detail="No response from M-Pesa service."
        )

    if not result.get("success", False):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Confirmation failed.")
        )

    return result


# ==========================================================
# SERVICES
# ==========================================================

@router.get("/mpesa/services")
async def services():
    return {
        "success": True,
        "services": mpesa_service.get_all_services(),
    }


@router.get("/mpesa/user/services")
async def user_services(
    current_user: dict = Depends(get_current_user),
):
    return {
        "success": True,
        "services": mpesa_service.get_user_services(current_user["id"]),
    }


@router.get("/mpesa/user/services/{service_id}/status")
async def service_status(
    service_id: str,
    current_user: dict = Depends(get_current_user),
):

    services = mpesa_service.get_user_services(current_user["id"])

    unlocked = any(
        s["service_id"] == service_id
        for s in services
    )

    return {
        "success": True,
        "service_id": service_id,
        "unlocked": unlocked,
    }


# ==========================================================
# PAYMENT HISTORY
# ==========================================================

@router.get("/mpesa/payments")
async def payment_history(
    current_user: dict = Depends(get_current_user),
):

    payments = mpesa_service.get_payment_history(current_user["id"])

    return {
        "success": True,
        "payments": payments,
        "count": len(payments),
    }


# ==========================================================
# ADMIN
# ==========================================================

@router.post("/mpesa/admin/service-prices")
async def service_prices(
    request: Request,
    current_user: dict = Depends(verify_admin),
    api_key: str = Depends(verify_api_key),
):

    body = await request.json()

    response = (
        supabase.table("service_prices")
        .insert(body)
        .execute()
    )

    return {
        "success": True,
        "data": response.data,
    }


@router.get("/mpesa/admin/stats")
async def stats(
    current_user: dict = Depends(verify_admin),
    api_key: str = Depends(verify_api_key),
):

    payments = (
        supabase.table("payments")
        .select("*")
        .execute()
    )

    data = payments.data or []

    return {
        "success": True,
        "total_payments": len(data),
        "completed": len([p for p in data if p["status"] == "completed"]),
        "pending": len([p for p in data if p["status"] == "pending"]),
        "failed": len([p for p in data if p["status"] == "failed"]),
        "total_amount": sum(float(p["amount"]) for p in data),
    }
