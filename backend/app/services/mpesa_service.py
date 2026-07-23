# app/api/v1/mpesa.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
import logging

from app.core.database import supabase
from app.services.mpesa_service import MpesaService
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize service
mpesa_service = MpesaService()

@router.get("/mpesa/status/{checkout_request_id}")
async def get_payment_status(
    checkout_request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get payment status by checkout_request_id.
    
    Returns:
        - 200: Payment found with status
        - 404: Payment not found
        - 500: Server error
    """
    try:
        logger.info(f"🔍 Checking payment status for: {checkout_request_id}")
        
        # Get payment status from service
        result = mpesa_service.get_payment_status(checkout_request_id)
        
        logger.info(f"📊 Status result: {result}")

        # Check if payment was found
        if result.get("success"):
            return {
                "success": True,
                "status": result.get("status", "pending"),
                "checkout_request_id": result.get("checkout_request_id"),
                "amount": result.get("amount"),
                "service_id": result.get("service_id"),
                "created_at": result.get("created_at"),
                "updated_at": result.get("updated_at")
            }
        else:
            # Payment not found - return 404
            logger.warning(f"⚠️ Payment not found: {checkout_request_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("error", "Payment not found")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Status check failed for {checkout_request_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/mpesa/confirm/{checkout_request_id}")
async def confirm_payment_manually(
    checkout_request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Manually confirm a payment and unlock the service.
    """
    try:
        user_id = current_user.get("id")
        
        result = mpesa_service.confirm_payment_manually(checkout_request_id, user_id)
        
        if result.get("success"):
            return {
                "success": True,
                "message": result.get("message", "Payment confirmed and service unlocked")
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to confirm payment")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Manual confirm failed for {checkout_request_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/mpesa/stkpush")
async def initiate_stk_push(
    request: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Initiate an M-Pesa STK Push payment.
    """
    try:
        phone = request.get("phone")
        amount = request.get("amount")
        account_reference = request.get("account_reference")
        description = request.get("description")
        user_id = current_user.get("id")
        
        if not phone or not amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number and amount are required"
            )
        
        result = await mpesa_service.initiate_stk_push(
            phone=phone,
            amount=amount,
            account_reference=account_reference,
            description=description,
            user_id=user_id
        )
        
        if result.get("success"):
            return {
                "success": True,
                "checkout_request_id": result.get("checkout_request_id"),
                "message": result.get("message", "STK Push sent successfully")
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "STK Push failed")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("❌ STK Push initiation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/mpesa/callback")
async def mpesa_callback(request: Dict[str, Any]):
    """
    M-Pesa callback endpoint.
    """
    try:
        logger.info("📞 Received M-Pesa callback")
        
        success = mpesa_service.process_callback(request)
        
        if success:
            return {"ResultCode": 0, "ResultDesc": "Success"}
        else:
            return {"ResultCode": 1, "ResultDesc": "Failed to process callback"}
            
    except Exception as e:
        logger.exception("❌ Callback processing failed")
        return {"ResultCode": 1, "ResultDesc": "Internal error"}
