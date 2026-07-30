# routes/mpesa_routes.py
# Auto-D Kenya - M-Pesa Payment Routes
# ================================================================
# TYPE: ROUTES - M-Pesa payment endpoints

from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import Optional

from schemas import MpesaPaymentRequest, MpesaPaymentResponse
from auth import get_current_user
from mpesa import MpesaService, handle_stk_push, handle_payment_status, handle_payment_confirm

router = APIRouter()
mpesa_service = MpesaService()


@router.post("/mpesa/stkpush", response_model=MpesaPaymentResponse)
async def stk_push(
    request: MpesaPaymentRequest,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """
    Initiate an M-Pesa STK push payment.
    """
    try:
        # Use authenticated user ID if not provided
        user_id = request.user_id or current_user.get("id") if current_user else None
        
        result = await handle_stk_push(
            phone=request.phone,
            service_id=request.service_id,
            description=request.description or "Auto-D Kenya Service",
            user_id=user_id,
            request_id=request.request_id,
            amount=request.amount
        )
        
        return MpesaPaymentResponse(
            checkout_request_id=result["checkout_request_id"],
            message=result["message"],
            status=result["status"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment initiation failed: {str(e)}"
        )


@router.get("/mpesa/status/{checkout_request_id}")
async def payment_status(checkout_request_id: str):
    """
    Query the status of a payment.
    """
    try:
        result = await handle_payment_status(checkout_request_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status query failed: {str(e)}"
        )


@router.post("/mpesa/confirm/{checkout_request_id}")
async def confirm_payment(checkout_request_id: str):
    """
    Confirm a payment and unlock the service.
    """
    try:
        result = await handle_payment_confirm(checkout_request_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment confirmation failed: {str(e)}"
        )


@router.post("/mpesa/callback")
async def mpesa_callback(request: Request):
    """
    M-Pesa callback endpoint for STK push results.
    """
    try:
        body = await request.json()
        
        # Process callback
        stk_callback = body.get("Body", {}).get("stkCallback", {})
        result_code = stk_callback.get("ResultCode")
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        
        if result_code == "0":
            # Payment successful
            await mpesa_service._unlock_service(checkout_request_id)
            return {"ResultCode": 0, "ResultDesc": "Success"}
        else:
            # Payment failed
            return {"ResultCode": result_code, "ResultDesc": stk_callback.get("ResultDesc", "Failed")}
            
    except Exception as e:
        return {"ResultCode": 1, "ResultDesc": str(e)}


@router.get("/mpesa/payments")
async def get_payments(current_user: dict = Depends(get_current_user)):
    """
    Get payment history for the current user.
    """
    try:
        supabase = get_supabase()
        response = supabase.table("mpesa_payments").select("*").eq("user_id", current_user["id"]).order("created_at", desc=True).execute()
        return {"payments": response.data, "count": len(response.data)}
    except Exception as e:
        return {"payments": [], "count": 0}


@router.get("/mpesa/health")
async def mpesa_health():
    """
    Check M-Pesa service health.
    """
    try:
        # Try to get access token
        await mpesa_service._get_access_token()
        return {"status": "healthy", "message": "M-Pesa service is operational"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}
