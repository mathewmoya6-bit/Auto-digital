"""
M-Pesa Routes - Clean Version
3 Services: mileage (100), valuation (150), ownership (200)
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

# ─── FIX: Use correct import path ──────────────────────────────────────
from app.core.dependencies import get_current_user
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mpesa", tags=["M-Pesa"])


# ─── FIX: Handle service import gracefully ────────────────────────────
try:
    from app.services.mpesa_service import mpesa_service
    MPESA_SERVICE_LOADED = True
    logger.info("✅ M-Pesa service loaded")
except ImportError as e:
    logger.error(f"❌ M-Pesa service not available: {e}")
    mpesa_service = None
    MPESA_SERVICE_LOADED = False


# ─── FIX: Handle payment repo gracefully ─────────────────────────────
try:
    from app.repositories.payment_repository import PaymentRepository
    payment_repo = PaymentRepository()
    logger.info("✅ Payment repository loaded")
except ImportError as e:
    logger.warning(f"⚠️ Payment repository not available: {e}")
    payment_repo = None


class STKPushRequest(BaseModel):
    phone: str
    service_id: str  # CODE from frontend (e.g., "mileage")
    description: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None


# ─── FIX: Check service availability on every endpoint ──────────────
def require_mpesa_service():
    if not MPESA_SERVICE_LOADED or mpesa_service is None:
        raise HTTPException(
            status_code=503,
            detail="M-Pesa service is currently unavailable. Please try again later."
        )
    return True


@router.get("/health")
async def health():
    return {
        "status": "ok" if MPESA_SERVICE_LOADED else "degraded",
        "service": "mpesa",
        "loaded": MPESA_SERVICE_LOADED
    }


@router.get("/shortcode")
async def get_shortcode():
    return {"shortcode": settings.MPESA_SHORTCODE}


@router.get("/services")
async def get_services():
    """Get all available services"""
    require_mpesa_service()
    services = await mpesa_service.get_services()
    return {"services": services}


@router.get("/user/services")
async def get_user_services(current_user: Dict = Depends(get_current_user)):
    """Get user's unlocked services"""
    require_mpesa_service()
    services = await mpesa_service.get_user_services(current_user.get("id"))
    return {"services": services}


@router.get("/user/services/{service_code}/status")
async def check_service_status(
    service_code: str, 
    current_user: Dict = Depends(get_current_user)
):
    """Check if user has access to a service"""
    require_mpesa_service()
    return await mpesa_service.check_service_access(current_user.get("id"), service_code)


@router.post("/stkpush")
async def initiate_stk_push(
    request: STKPushRequest, 
    current_user: Dict = Depends(get_current_user)
):
    """
    Initiate STK Push payment
    """
    require_mpesa_service()
    
    try:
        result = await mpesa_service.initiate_payment(
            phone=request.phone,
            service_code=request.service_id,
            description=request.description,
            user_id=current_user.get("id"),
            request_id=request.request_id,
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Payment initiation failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STK Push error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/callback")
async def mpesa_callback(request: Request):
    """M-Pesa callback endpoint"""
    require_mpesa_service()
    try:
        data = await request.json()
        success = await mpesa_service.process_callback(data)
        return {"ResultCode": 0, "ResultDesc": "Success" if success else "Failed"}
    except Exception as e:
        logger.exception("Callback error")
        return {"ResultCode": 1, "ResultDesc": str(e)}


@router.get("/status/{checkout_request_id}")
async def get_payment_status(checkout_request_id: str):
    """Get payment status"""
    require_mpesa_service()
    return await mpesa_service.get_payment_status(checkout_request_id)


@router.post("/confirm/{checkout_request_id}")
async def confirm_payment(
    checkout_request_id: str, 
    current_user: Dict = Depends(get_current_user)
):
    """Manually confirm a payment"""
    require_mpesa_service()
    
    if payment_repo is None:
        raise HTTPException(status_code=503, detail="Payment repository unavailable")
    
    payment = await payment_repo.get_by_checkout_id(checkout_request_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment.get("user_id") != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if payment.get("status") == "completed":
        return {"success": True, "status": "already_completed"}
    
    # Create synthetic callback
    callback_data = {
        "Body": {
            "stkCallback": {
                "CheckoutRequestID": checkout_request_id,
                "ResultCode": "0",
                "ResultDesc": "Confirmed manually",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": payment.get("amount", 0)},
                        {"Name": "MpesaReceiptNumber", "Value": f"MANUAL-{checkout_request_id[:8]}"},
                    ]
                }
            }
        }
    }
    
    success = await mpesa_service.process_callback(callback_data)
    if success:
        return {"success": True, "message": "Payment confirmed"}
    raise HTTPException(status_code=500, detail="Failed to confirm payment")


@router.get("/payments")
async def get_payment_history(current_user: Dict = Depends(get_current_user)):
    """Get user's payment history"""
    require_mpesa_service()
    payments = await mpesa_service.get_payment_history(current_user.get("id"))
    return {"payments": payments}


# ─── FIX: Handle payment repo gracefully ─────────────────────────────
def require_payment_repo():
    if payment_repo is None:
        raise HTTPException(
            status_code=503,
            detail="Payment repository is currently unavailable. Please try again later."
        )
    return True


# ─── Admin Routes ────────────────────────────────────────────────────

@router.get("/admin/services")
async def admin_get_services(current_user: Dict = Depends(get_current_user)):
    """Admin: Get all services including inactive"""
    require_mpesa_service()
    services = await mpesa_service.admin_get_all_services(include_inactive=True)
    return {"services": services}


@router.get("/admin/services/{service_id}")
async def admin_get_service(service_id: int, current_user: Dict = Depends(get_current_user)):
    """Admin: Get service by ID"""
    require_mpesa_service()
    service = await mpesa_service.admin_get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return {"service": service}


@router.post("/admin/services")
async def admin_create_service(data: Dict, current_user: Dict = Depends(get_current_user)):
    """Admin: Create a new service"""
    require_mpesa_service()
    # This would need to be implemented in the service
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.put("/admin/services/{service_id}")
async def admin_update_service(
    service_id: int, 
    data: Dict, 
    current_user: Dict = Depends(get_current_user)
):
    """Admin: Update a service"""
    require_mpesa_service()
    result = await mpesa_service.admin_update_service(
        service_id=service_id,
        data=data,
        changed_by=current_user.get("id")
    )
    if not result:
        raise HTTPException(status_code=404, detail="Service not found or update failed")
    return {"service": result}


@router.delete("/admin/services/{service_id}")
async def admin_delete_service(
    service_id: int, 
    current_user: Dict = Depends(get_current_user)
):
    """Admin: Delete a service"""
    require_mpesa_service()
    success = await mpesa_service.admin_delete_service(
        service_id=service_id,
        deleted_by=current_user.get("id")
    )
    if not success:
        raise HTTPException(status_code=404, detail="Service not found or delete failed")
    return {"success": True, "message": "Service deleted"}


@router.post("/admin/services/{service_id}/restore")
async def admin_restore_service(
    service_id: int, 
    current_user: Dict = Depends(get_current_user)
):
    """Admin: Restore a service"""
    require_mpesa_service()
    success = await mpesa_service.admin_restore_service(service_id)
    if not success:
        raise HTTPException(status_code=404, detail="Service not found or restore failed")
    return {"success": True, "message": "Service restored"}


@router.get("/admin/services/{service_id}/price-history")
async def admin_get_price_history(
    service_id: int, 
    current_user: Dict = Depends(get_current_user)
):
    """Admin: Get price history for a service"""
    require_mpesa_service()
    history = await mpesa_service.admin_get_price_history(service_id)
    return {"price_history": history}


@router.post("/admin/expire-stale")
async def admin_expire_stale(
    minutes: int = 30, 
    current_user: Dict = Depends(get_current_user)
):
    """Admin: Expire stale pending payments"""
    require_mpesa_service()
    require_payment_repo()
    count = await mpesa_service.expire_stale_payments(minutes)
    return {"expired_count": count}


@router.get("/admin/stats")
async def admin_get_stats(current_user: Dict = Depends(get_current_user)):
    """Admin: Get stats"""
    require_mpesa_service()
    
    services = await mpesa_service.get_services() if mpesa_service else []
    
    if payment_repo:
        payments = await payment_repo.get_user_payments(current_user.get("id"))
        total_payments = len(payments)
    else:
        total_payments = 0
    
    return {
        "total_services": len(services),
        "total_payments": total_payments,
        "active_services": len([s for s in services if s.get("active")]) if services else 0,
        "mpesa_service_loaded": MPESA_SERVICE_LOADED
    }
