"""
M-Pesa Routes - Clean Version
3 Services: mileage (100), valuation (150), ownership (200)
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.services.mpesa_service import mpesa_service
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mpesa", tags=["M-Pesa"])


class STKPushRequest(BaseModel):
    phone: str
    service_id: str  # CODE from frontend (e.g., "mileage")
    description: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None


@router.get("/health")
async def health():
    return {"status": "ok", "service": "mpesa"}


@router.get("/shortcode")
async def get_shortcode():
    from app.core.config import settings
    return {"shortcode": settings.MPESA_SHORTCODE}


@router.get("/services")
async def get_services():
    """Get all available services"""
    services = await mpesa_service.get_services()
    return {"services": services}


@router.get("/user/services")
async def get_user_services(current_user: Dict = Depends(get_current_user)):
    """Get user's unlocked services"""
    services = await mpesa_service.get_user_services(current_user.get("id"))
    return {"services": services}


@router.get("/user/services/{service_code}/status")
async def check_service_status(service_code: str, current_user: Dict = Depends(get_current_user)):
    """Check if user has access to a service"""
    return await mpesa_service.check_service_access(current_user.get("id"), service_code)


@router.post("/stkpush")
async def initiate_stk_push(request: STKPushRequest, current_user: Dict = Depends(get_current_user)):
    """
    Initiate STK Push payment
    FIX: Uses initiate_payment method (not initiate_stk_push)
    """
    result = await mpesa_service.initiate_payment(
        phone=request.phone,
        service_code=request.service_id,
        description=request.description,
        user_id=current_user.get("id"),
        request_id=request.request_id,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/callback")
async def mpesa_callback(request: Request):
    """M-Pesa callback endpoint"""
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
    return await mpesa_service.get_payment_status(checkout_request_id)


@router.post("/confirm/{checkout_request_id}")
async def confirm_payment(checkout_request_id: str, current_user: Dict = Depends(get_current_user)):
    """Manually confirm a payment"""
    payment = await mpesa_service.payment_repo.get_by_checkout_id(checkout_request_id)
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
    payments = await mpesa_service.get_payment_history(current_user.get("id"))
    return {"payments": payments}


# ─── Admin Routes ───

@router.get("/admin/services")
async def admin_get_services(current_user: Dict = Depends(get_current_user)):
    """Admin: Get all services including inactive"""
    services = await mpesa_service.admin_get_all_services(include_inactive=True)
    return {"services": services}


@router.get("/admin/services/{service_id}")
async def admin_get_service(service_id: int, current_user: Dict = Depends(get_current_user)):
    """Admin: Get service by ID"""
    service = await mpesa_service.admin_get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return {"service": service}


@router.post("/admin/services")
async def admin_create_service(data: Dict, current_user: Dict = Depends(get_current_user)):
    """Admin: Create a new service"""
    # This would need to be implemented in the service
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.put("/admin/services/{service_id}")
async def admin_update_service(
    service_id: int, 
    data: Dict, 
    current_user: Dict = Depends(get_current_user)
):
    """Admin: Update a service"""
    result = await mpesa_service.admin_update_service(
        service_id=service_id,
        data=data,
        changed_by=current_user.get("id")
    )
    if not result:
        raise HTTPException(status_code=404, detail="Service not found or update failed")
    return {"service": result}


@router.delete("/admin/services/{service_id}")
async def admin_delete_service(service_id: int, current_user: Dict = Depends(get_current_user)):
    """Admin: Delete a service"""
    success = await mpesa_service.admin_delete_service(
        service_id=service_id,
        deleted_by=current_user.get("id")
    )
    if not success:
        raise HTTPException(status_code=404, detail="Service not found or delete failed")
    return {"success": True, "message": "Service deleted"}


@router.post("/admin/services/{service_id}/restore")
async def admin_restore_service(service_id: int, current_user: Dict = Depends(get_current_user)):
    """Admin: Restore a service"""
    success = await mpesa_service.admin_restore_service(service_id)
    if not success:
        raise HTTPException(status_code=404, detail="Service not found or restore failed")
    return {"success": True, "message": "Service restored"}


@router.get("/admin/services/{service_id}/price-history")
async def admin_get_price_history(service_id: int, current_user: Dict = Depends(get_current_user)):
    """Admin: Get price history for a service"""
    history = await mpesa_service.admin_get_price_history(service_id)
    return {"price_history": history}


@router.post("/admin/expire-stale")
async def admin_expire_stale(minutes: int = 30, current_user: Dict = Depends(get_current_user)):
    """Admin: Expire stale pending payments"""
    count = await mpesa_service.expire_stale_payments(minutes)
    return {"expired_count": count}


@router.get("/admin/stats")
async def admin_get_stats(current_user: Dict = Depends(get_current_user)):
    """Admin: Get stats"""
    # Get counts
    services = await mpesa_service.get_services()
    payments = await mpesa_service.payment_repo.get_user_payments(current_user.get("id"))
    
    return {
        "total_services": len(services),
        "total_payments": len(payments),
        "active_services": len([s for s in services if s.get("active")]),
    }
