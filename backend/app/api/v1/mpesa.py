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
from app.services.mpesa_service import mpesa_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["M-Pesa"])


# ==========================================================
# HEALTH
# ==========================================================

@router.get("/mpesa/test")
async def test():
    return {
        "success": True,
        "message": "M-Pesa router loaded",
        "environment": mpesa_service.auth_service.environment,
        "shortcode": mpesa_service.stk_service.shortcode,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/mpesa/health")
async def health():
    return {
        "success": True,
        "configured": mpesa_service.is_configured(),
        "environment": mpesa_service.auth_service.environment,
        "shortcode": mpesa_service.stk_service.shortcode,
        "callback_url": mpesa_service.stk_service.callback_url,
    }


@router.get("/mpesa/shortcode")
async def shortcode():
    return {
        "success": True,
        "shortcode": mpesa_service.stk_service.shortcode,
        "environment": mpesa_service.auth_service.environment,
    }


# ==========================================================
# STK PUSH - FIXED: Uses service_id, NOT amount
# ==========================================================

@router.post("/mpesa/stkpush")
async def stkpush(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    Initiate an M-Pesa STK Push.
    Amount is calculated by the backend from the service_id.
    """
    try:
        body = await request.json()

        phone = body.get("phone")
        service_id = body.get("service_id")
        description = body.get("description")
        corporate_id = body.get("corporate_id")

        # ─── Validate phone ───
        if not phone:
            raise HTTPException(
                status_code=400,
                detail="Phone number is required."
            )

        # ─── Validate service_id ───
        if not service_id:
            raise HTTPException(
                status_code=400,
                detail="service_id is required."
            )

        logger.info(
            f"Initiating STK Push | user={current_user['id']} | "
            f"phone={phone} | service_id={service_id}"
        )

        # ─── FIX: Call with service_id, NOT amount ───
        result = await mpesa_service.initiate_stk_push(
            phone=phone,
            service_id=service_id,
            description=description,
            user_id=current_user["id"],
            corporate_id=corporate_id,
        )

        # ─── Defensive checks ───
        if result is None:
            logger.error("MpesaService returned None")
            raise HTTPException(
                status_code=500,
                detail="M-Pesa service returned no response."
            )

        if not isinstance(result, dict):
            logger.error(f"Unexpected response type: {type(result)}")
            raise HTTPException(
                status_code=500,
                detail="Invalid response from M-Pesa service."
            )

        if not result.get("success", False):
            error = result.get("error") or result.get("message") or "Failed to initiate STK Push."
            logger.error(f"STK Push failed: {error}")
            raise HTTPException(
                status_code=400,
                detail=error
            )

        logger.info("STK Push initiated successfully.")

        return result

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Unexpected error during STK Push")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ==========================================================
# CALLBACK
# ==========================================================

@router.post("/mpesa/callback")
async def callback(request: Request):
    """
    M-Pesa callback endpoint.
    """
    try:
        data = await request.json()

        logger.info("Received M-Pesa callback")
        logger.debug(f"Callback data: {data}")

        # ─── FIX: Use async/await ───
        success = await mpesa_service.process_callback(data)

        return {
            "ResultCode": 0 if success else 1,
            "ResultDesc": "Success" if success else "Failed"
        }

    except Exception as e:
        logger.exception("Callback processing failed")
        return {
            "ResultCode": 1,
            "ResultDesc": f"Processing Failed: {str(e)}"
        }


# ==========================================================
# PAYMENT STATUS - FIXED: Uses async
# ==========================================================

@router.get("/mpesa/status/{checkout_request_id}")
async def payment_status(checkout_request_id: str):
    """
    Get payment status by checkout request ID.
    """
    try:
        logger.info(f"Checking payment {checkout_request_id}")

        # ─── FIX: Use async/await ───
        result = await mpesa_service.get_payment_status(checkout_request_id)

        if result is None or not result.get("success"):
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Payment not found."
                }
            )

        return JSONResponse(
            status_code=200,
            content=result
        )

    except Exception as e:
        logger.exception(f"Payment status error: {checkout_request_id}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }
        )


# ==========================================================
# MANUAL CONFIRM - FIXED: Uses async
# ==========================================================

@router.post("/mpesa/confirm/{checkout_request_id}")
async def confirm(
    checkout_request_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Manually confirm a payment and unlock the service.
    """
    try:
        logger.info(
            f"Manual confirm | user={current_user['id']} | "
            f"checkout={checkout_request_id}"
        )

        # ─── FIX: Use async/await ───
        result = await mpesa_service.confirm_payment_manually(
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

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(f"Manual confirm error: {checkout_request_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ==========================================================
# SERVICES - FIXED: Uses async
# ==========================================================

@router.get("/mpesa/services")
async def services():
    """
    Get all available services.
    """
    try:
        # ─── FIX: Use async/await ───
        services_list = await mpesa_service.get_all_services()

        return {
            "success": True,
            "services": services_list,
            "count": len(services_list),
        }

    except Exception as e:
        logger.exception("Get services error")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }
        )


@router.get("/mpesa/user/services")
async def user_services(
    current_user: dict = Depends(get_current_user),
):
    """
    Get all unlocked services for the current user.
    """
    try:
        # ─── FIX: Use async/await ───
        services_list = await mpesa_service.get_user_services(current_user["id"])

        return {
            "success": True,
            "services": services_list,
            "count": len(services_list),
        }

    except Exception as e:
        logger.exception("Get user services error")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }
        )


@router.get("/mpesa/user/services/{service_id}/status")
async def service_status(
    service_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Check if a user has access to a specific service.
    """
    try:
        # ─── FIX: Use async/await ───
        result = await mpesa_service.check_service_access(
            current_user["id"],
            service_id
        )

        return {
            "success": True,
            **result
        }

    except Exception as e:
        logger.exception(f"Service status error: {service_id}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }
        )


# ==========================================================
# PAYMENT HISTORY - FIXED: Uses async
# ==========================================================

@router.get("/mpesa/payments")
async def payment_history(
    current_user: dict = Depends(get_current_user),
):
    """
    Get payment history for the current user.
    """
    try:
        # ─── FIX: Use async/await ───
        payments = await mpesa_service.get_payment_history(current_user["id"])

        return {
            "success": True,
            "payments": payments,
            "count": len(payments),
        }

    except Exception as e:
        logger.exception("Get payment history error")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }
        )


# ==========================================================
# ADMIN - FIXED: Uses async
# ==========================================================

@router.post("/mpesa/admin/service-prices")
async def service_prices(
    request: Request,
    current_user: dict = Depends(verify_admin),
    api_key: str = Depends(verify_api_key),
):
    """
    Admin: Create or update service prices.
    """
    try:
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

    except Exception as e:
        logger.exception("Admin service prices error")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }
        )


@router.get("/mpesa/admin/stats")
async def stats(
    current_user: dict = Depends(verify_admin),
    api_key: str = Depends(verify_api_key),
):
    """
    Admin: Get payment statistics.
    """
    try:
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

    except Exception as e:
        logger.exception("Admin stats error")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }
        )


# ==========================================================
# ADMIN SERVICES - FIXED: Uses async
# ==========================================================

@router.get("/mpesa/admin/services")
async def admin_services(
    current_user: dict = Depends(verify_admin),
    api_key: str = Depends(verify_api_key),
):
    """
    Admin: Get all services including inactive.
    """
    try:
        # ─── FIX: Use async/await ───
        services_list = await mpesa_service.admin_get_all_services()

        return {
            "success": True,
            "services": services_list,
            "count": len(services_list),
        }

    except Exception as e:
        logger.exception("Admin get services error")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }
        )


@router.post("/mpesa/admin/services")
async def admin_create_service(
    request: Request,
    current_user: dict = Depends(verify_admin),
    api_key: str = Depends(verify_api_key),
):
    """
    Admin: Create a new service.
    """
    try:
        body = await request.json()

        # ─── FIX: Use async/await ───
        result = await mpesa_service.admin_create_service(body)

        if result is None:
            raise HTTPException(
                status_code=400,
                detail="Failed to create service."
            )

        return {
            "success": True,
            "data": result,
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Admin create service error")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.put("/mpesa/admin/services/{service_id}")
async def admin_update_service(
    service_id: str,
    request: Request,
    current_user: dict = Depends(verify_admin),
    api_key: str = Depends(verify_api_key),
):
    """
    Admin: Update a service.
    """
    try:
        body = await request.json()

        changed_by = current_user.get("email") or current_user.get("id")
        reason = body.get("reason")

        # ─── FIX: Use async/await ───
        result = await mpesa_service.admin_update_service(
            service_id=service_id,
            data=body,
            changed_by=changed_by,
            reason=reason,
        )

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Service not found or update failed."
            )

        return {
            "success": True,
            "data": result,
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Admin update service error")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete("/mpesa/admin/services/{service_id}")
async def admin_delete_service(
    service_id: str,
    current_user: dict = Depends(verify_admin),
    api_key: str = Depends(verify_api_key),
):
    """
    Admin: Soft delete a service.
    """
    try:
        deleted_by = current_user.get("email") or current_user.get("id")

        # ─── FIX: Use async/await ───
        result = await mpesa_service.admin_delete_service(
            service_id=service_id,
            deleted_by=deleted_by,
        )

        if not result:
            raise HTTPException(
                status_code=404,
                detail="Service not found or deletion failed."
            )

        return {
            "success": True,
            "message": "Service deleted successfully.",
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Admin delete service error")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/mpesa/admin/services/{service_id}/restore")
async def admin_restore_service(
    service_id: str,
    current_user: dict = Depends(verify_admin),
    api_key: str = Depends(verify_api_key),
):
    """
    Admin: Restore a soft-deleted service.
    """
    try:
        # ─── FIX: Use async/await ───
        result = await mpesa_service.admin_restore_service(service_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail="Service not found or restoration failed."
            )

        return {
            "success": True,
            "message": "Service restored successfully.",
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Admin restore service error")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/mpesa/admin/services/{service_id}/price-history")
async def admin_price_history(
    service_id: str,
    current_user: dict = Depends(verify_admin),
    api_key: str = Depends(verify_api_key),
):
    """
    Admin: Get price history for a service.
    """
    try:
        # ─── FIX: Use async/await ───
        history = await mpesa_service.admin_get_price_history(service_id)

        return {
            "success": True,
            "service_id": service_id,
            "history": history,
            "count": len(history),
        }

    except Exception as e:
        logger.exception("Admin price history error")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }
        )


@router.post("/mpesa/admin/expire-stale")
async def admin_expire_stale(
    current_user: dict = Depends(verify_admin),
    api_key: str = Depends(verify_api_key),
):
    """
    Admin: Expire stale pending payments.
    """
    try:
        # ─── FIX: Use async/await ───
        count = await mpesa_service.expire_stale_payments(minutes=30)

        return {
            "success": True,
            "expired_count": count,
            "message": f"Expired {count} stale payments.",
        }

    except Exception as e:
        logger.exception("Admin expire stale error")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }
        )
