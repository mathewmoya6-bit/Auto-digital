"""
M-Pesa Routes - Production Ready
All services and prices are pulled from the database dynamically
Endpoints match OpenAPI spec: /api/v1/mpesa/*
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.core.dependencies import get_current_user
from app.core.config import settings

logger = logging.getLogger(__name__)

# Router - main.py adds /api/v1 prefix
router = APIRouter(tags=["M-Pesa"])

# ─── Service Imports ──────────────────────────────────────────────
try:
    from app.services.mpesa_service import mpesa_service
    MPESA_SERVICE_LOADED = True
    logger.info("✅ M-Pesa service loaded")
except ImportError as e:
    logger.error(f"❌ M-Pesa service not available: {e}")
    mpesa_service = None
    MPESA_SERVICE_LOADED = False

try:
    from app.repositories.payment_repository import PaymentRepository
    payment_repo = PaymentRepository()
    logger.info("✅ Payment repository loaded")
except ImportError as e:
    logger.warning(f"⚠️ Payment repository not available: {e}")
    payment_repo = None


# ─── Models ──────────────────────────────────────────────────────
class STKPushRequest(BaseModel):
    phone: str
    service_id: str
    description: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    amount: Optional[float] = None


# ─── Helpers ──────────────────────────────────────────────────────
def require_mpesa_service():
    if not MPESA_SERVICE_LOADED or mpesa_service is None:
        raise HTTPException(
            status_code=503,
            detail="M-Pesa service is currently unavailable. Please try again later."
        )
    return True


def require_payment_repo():
    if payment_repo is None:
        raise HTTPException(
            status_code=503,
            detail="Payment repository is currently unavailable. Please try again later."
        )
    return True


# ════════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS
# ════════════════════════════════════════════════════════════════

@router.get("/mpesa/health")
async def mpesa_health():
    """GET /api/v1/mpesa/health - Health check"""
    return {
        "status": "ok" if MPESA_SERVICE_LOADED else "degraded",
        "service": "mpesa",
        "loaded": MPESA_SERVICE_LOADED,
        "shortcode": getattr(settings, "MPESA_SHORTCODE", "4095377")
    }


@router.get("/mpesa/shortcode")
async def get_shortcode():
    """GET /api/v1/mpesa/shortcode - Get M-Pesa shortcode"""
    return {"shortcode": getattr(settings, "MPESA_SHORTCODE", "4095377")}


@router.get("/mpesa/services")
async def get_services():
    """GET /api/v1/mpesa/services - Get all available services"""
    require_mpesa_service()
    try:
        services = await mpesa_service.get_services()
        return {"services": services}
    except Exception as e:
        logger.error(f"Error fetching services: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch services")


@router.get("/mpesa/user/services")
async def get_user_services(current_user: Dict = Depends(get_current_user)):
    """GET /api/v1/mpesa/user/services - Get user's unlocked services"""
    require_mpesa_service()
    try:
        services = await mpesa_service.get_user_services(current_user.get("id"))
        return {"services": services}
    except Exception as e:
        logger.error(f"Error fetching user services: {e}")
        return {"services": []}


@router.get("/mpesa/user/services/{service_code}/status")
async def check_service_status(
    service_code: str, 
    current_user: Dict = Depends(get_current_user)
):
    """GET /api/v1/mpesa/user/services/{service_code}/status - Check service access"""
    require_mpesa_service()
    try:
        return await mpesa_service.check_service_access(current_user.get("id"), service_code)
    except Exception as e:
        logger.error(f"Error checking service status: {e}")
        return {"has_access": False, "error": str(e)}


@router.post("/mpesa/stkpush")
async def initiate_stk_push(
    request: STKPushRequest, 
    current_user: Dict = Depends(get_current_user)
):
    """POST /api/v1/mpesa/stkpush - Initiate STK Push payment"""
    require_mpesa_service()
    
    try:
        amount = request.amount
        if amount is None:
            services = await mpesa_service.get_services()
            service = next((s for s in services if s.get("code") == request.service_id), None)
            amount = service.get("price", 0) if service else 0
        
        result = await mpesa_service.initiate_payment(
            phone=request.phone,
            service_code=request.service_id,
            description=request.description,
            user_id=current_user.get("id"),
            request_id=request.request_id,
            amount=amount,
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Payment initiation failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STK Push error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mpesa/callback")
async def mpesa_callback(request: Request):
    """POST /api/v1/mpesa/callback - M-Pesa callback endpoint"""
    require_mpesa_service()
    try:
        data = await request.json()
        logger.info(f"Callback received: {data}")
        success = await mpesa_service.process_callback(data)
        return {"ResultCode": 0, "ResultDesc": "Success" if success else "Failed"}
    except Exception as e:
        logger.exception("Callback error")
        return {"ResultCode": 1, "ResultDesc": str(e)}


@router.get("/mpesa/status/{checkout_request_id}")
async def get_payment_status(checkout_request_id: str):
    """GET /api/v1/mpesa/status/{checkout_request_id} - Get payment status"""
    require_mpesa_service()
    try:
        return await mpesa_service.get_payment_status(checkout_request_id)
    except Exception as e:
        logger.error(f"Error getting payment status: {e}")
        return {"status": "unknown", "error": str(e)}


@router.post("/mpesa/confirm/{checkout_request_id}")
async def confirm_payment(
    checkout_request_id: str, 
    current_user: Dict = Depends(get_current_user)
):
    """POST /api/v1/mpesa/confirm/{checkout_request_id} - Confirm payment"""
    require_mpesa_service()
    require_payment_repo()
    
    try:
        payment = await payment_repo.get_by_checkout_id(checkout_request_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        if payment.get("user_id") != current_user.get("id"):
            raise HTTPException(status_code=403, detail="Not authorized")
        
        if payment.get("status") == "completed":
            return {"success": True, "status": "already_completed", "message": "Payment already confirmed"}
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Confirm payment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mpesa/payments")
async def get_payment_history(current_user: Dict = Depends(get_current_user)):
    """GET /api/v1/mpesa/payments - Get user's payment history"""
    require_mpesa_service()
    try:
        payments = await mpesa_service.get_payment_history(current_user.get("id"))
        return {"payments": payments}
    except Exception as e:
        logger.error(f"Error getting payment history: {e}")
        return {"payments": []}


# ════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ════════════════════════════════════════════════════════════════

@router.get("/mpesa/admin/services")
async def admin_get_services(current_user: Dict = Depends(get_current_user)):
    """GET /api/v1/mpesa/admin/services - Admin: Get all services"""
    require_mpesa_service()
    try:
        services = await mpesa_service.admin_get_all_services(include_inactive=True)
        return {"services": services}
    except Exception as e:
        logger.error(f"Admin get services error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch services")


@router.get("/mpesa/admin/services/{service_id}")
async def admin_get_service(service_id: int, current_user: Dict = Depends(get_current_user)):
    """GET /api/v1/mpesa/admin/services/{service_id} - Admin: Get service by ID"""
    require_mpesa_service()
    try:
        service = await mpesa_service.admin_get_service(service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        return {"service": service}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin get service error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch service")


@router.post("/mpesa/admin/services")
async def admin_create_service(data: Dict, current_user: Dict = Depends(get_current_user)):
    """POST /api/v1/mpesa/admin/services - Admin: Create a new service"""
    require_mpesa_service()
    try:
        result = await mpesa_service.admin_create_service(
            data=data,
            created_by=current_user.get("id")
        )
        return {"service": result}
    except Exception as e:
        logger.error(f"Admin create service error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/mpesa/admin/services/{service_id}")
async def admin_update_service(
    service_id: int, 
    data: Dict, 
    current_user: Dict = Depends(get_current_user)
):
    """PUT /api/v1/mpesa/admin/services/{service_id} - Admin: Update a service"""
    require_mpesa_service()
    try:
        result = await mpesa_service.admin_update_service(
            service_id=service_id,
            data=data,
            changed_by=current_user.get("id")
        )
        if not result:
            raise HTTPException(status_code=404, detail="Service not found or update failed")
        return {"service": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin update service error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/mpesa/admin/services/{service_id}")
async def admin_delete_service(
    service_id: int, 
    current_user: Dict = Depends(get_current_user)
):
    """DELETE /api/v1/mpesa/admin/services/{service_id} - Admin: Delete a service"""
    require_mpesa_service()
    try:
        success = await mpesa_service.admin_delete_service(
            service_id=service_id,
            deleted_by=current_user.get("id")
        )
        if not success:
            raise HTTPException(status_code=404, detail="Service not found or delete failed")
        return {"success": True, "message": "Service deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin delete service error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mpesa/admin/services/{service_id}/restore")
async def admin_restore_service(
    service_id: int, 
    current_user: Dict = Depends(get_current_user)
):
    """POST /api/v1/mpesa/admin/services/{service_id}/restore - Admin: Restore a service"""
    require_mpesa_service()
    try:
        success = await mpesa_service.admin_restore_service(service_id)
        if not success:
            raise HTTPException(status_code=404, detail="Service not found or restore failed")
        return {"success": True, "message": "Service restored"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin restore service error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mpesa/admin/services/{service_id}/price-history")
async def admin_get_price_history(
    service_id: int, 
    current_user: Dict = Depends(get_current_user)
):
    """GET /api/v1/mpesa/admin/services/{service_id}/price-history - Admin: Get price history"""
    require_mpesa_service()
    try:
        history = await mpesa_service.admin_get_price_history(service_id)
        return {"price_history": history}
    except Exception as e:
        logger.error(f"Admin get price history error: {e}")
        return {"price_history": []}


@router.post("/mpesa/admin/expire-stale")
async def admin_expire_stale(
    minutes: int = 30, 
    current_user: Dict = Depends(get_current_user)
):
    """POST /api/v1/mpesa/admin/expire-stale - Admin: Expire stale payments"""
    require_mpesa_service()
    require_payment_repo()
    try:
        count = await mpesa_service.expire_stale_payments(minutes)
        return {"expired_count": count}
    except Exception as e:
        logger.error(f"Admin expire stale error: {e}")
        return {"expired_count": 0, "error": str(e)}


@router.get("/mpesa/admin/stats")
async def admin_get_stats(current_user: Dict = Depends(get_current_user)):
    """GET /api/v1/mpesa/admin/stats - Admin: Get stats"""
    require_mpesa_service()
    
    try:
        services = await mpesa_service.get_services() if mpesa_service else []
        
        if payment_repo:
            payments = await payment_repo.get_all_payments()
            total_payments = len(payments)
            total_revenue = sum(p.get("amount", 0) for p in payments if p.get("status") == "completed")
        else:
            total_payments = 0
            total_revenue = 0
        
        return {
            "total_services": len(services),
            "active_services": len([s for s in services if s.get("active")]) if services else 0,
            "total_payments": total_payments,
            "total_revenue": total_revenue,
            "mpesa_service_loaded": MPESA_SERVICE_LOADED
        }
    except Exception as e:
        logger.error(f"Admin get stats error: {e}")
        return {
            "total_services": 0,
            "active_services": 0,
            "total_payments": 0,
            "total_revenue": 0,
            "mpesa_service_loaded": MPESA_SERVICE_LOADED,
            "error": str(e)
        }
