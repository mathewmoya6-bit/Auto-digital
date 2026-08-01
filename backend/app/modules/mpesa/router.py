# app/modules/mpesa/router.py
# Auto-D Kenya - M-Pesa Routes
# ================================================================
# TYPE: MODULE - M-Pesa API routes

from fastapi import APIRouter, Depends, Request, HTTPException, status
from typing import Dict, Any

from app.core.database import get_supabase
from app.core.dependencies import get_current_user, get_current_user_optional
from app.modules.mpesa.service import MpesaService
from app.modules.mpesa.callback import MpesaCallbackHandler
from app.modules.mpesa.schemas import (
    MpesaPaymentRequest,
    MpesaPaymentResponse,
    PaymentStatusResponse,
    ServiceAccessResponse,
    UserServicesResponse,
    AvailableServicesResponse,
    PaymentHistoryResponse,
    WebhookResponse,
    MpesaHealthResponse,
    create_payment_response,
    create_service_access_response,
    create_webhook_response
)

router = APIRouter()
mpesa_service = MpesaService()
callback_handler = MpesaCallbackHandler()


# ─── STK PUSH ──────────────────────────────────────────────────────

@router.post("/mpesa/stkpush", response_model=MpesaPaymentResponse)
async def stk_push(
    request: MpesaPaymentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Initiate M-Pesa STK Push payment.
    
    POST /api/v1/mpesa/stkpush
    
    Requires authentication.
    """
    try:
        result = await mpesa_service.initiate_payment(
            phone=request.phone,
            service_id=request.service_id,
            description=request.description,
            user_id=current_user.get("id"),
            request_id=request.request_id,
            amount=request.amount
        )
        
        return create_payment_response(
            checkout_request_id=result["checkout_request_id"],
            message=result.get("message", "STK push sent successfully"),
            status=result.get("status", "pending")
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment initiation failed: {str(e)}"
        )


@router.post("/mpesa/stkpush-public", response_model=MpesaPaymentResponse)
async def stk_push_public(
    request: MpesaPaymentRequest
):
    """
    Initiate M-Pesa STK Push payment (public endpoint).
    
    POST /api/v1/mpesa/stkpush-public
    
    No authentication required. Use this for testing or public-facing flows.
    """
    try:
        result = await mpesa_service.initiate_payment(
            phone=request.phone,
            service_id=request.service_id,
            description=request.description,
            user_id=request.user_id,
            request_id=request.request_id,
            amount=request.amount
        )
        
        return create_payment_response(
            checkout_request_id=result["checkout_request_id"],
            message=result.get("message", "STK push sent successfully"),
            status=result.get("status", "pending")
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment initiation failed: {str(e)}"
        )


# ─── PAYMENT STATUS ───────────────────────────────────────────────

@router.get("/mpesa/status/{checkout_request_id}", response_model=PaymentStatusResponse)
async def payment_status(
    checkout_request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get payment status.
    
    GET /api/v1/mpesa/status/{checkout_request_id}
    
    Requires authentication.
    """
    try:
        result = await mpesa_service.get_payment_status(checkout_request_id, current_user.get("id"))
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment status: {str(e)}"
        )


@router.get("/mpesa/status-public/{checkout_request_id}")
async def payment_status_public(
    checkout_request_id: str
):
    """
    Get payment status (public endpoint).
    
    GET /api/v1/mpesa/status-public/{checkout_request_id}
    
    No authentication required.
    """
    try:
        result = await mpesa_service.stk_push.verify_payment_status(checkout_request_id)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment status: {str(e)}"
        )


# ─── CONFIRM PAYMENT ──────────────────────────────────────────────

@router.post("/mpesa/confirm/{checkout_request_id}")
async def confirm_payment(
    checkout_request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Confirm payment and unlock service.
    
    POST /api/v1/mpesa/confirm/{checkout_request_id}
    
    Requires authentication.
    """
    try:
        result = await mpesa_service.confirm_payment(checkout_request_id, current_user.get("id"))
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment confirmation failed: {str(e)}"
        )


# ─── CALLBACK ──────────────────────────────────────────────────────

@router.post("/mpesa/callback", response_model=WebhookResponse)
async def mpesa_callback(request: Request):
    """
    M-Pesa callback webhook.
    
    POST /api/v1/mpesa/callback
    
    This is called by Safaricom when the payment is completed.
    This is the ONLY place where services are unlocked.
    """
    try:
        body = await request.json()
        result = await callback_handler.process_callback(body)
        
        return create_webhook_response(
            status=result.get("status", "processed"),
            message=result.get("message", "Callback processed"),
            checkout_request_id=result.get("checkout_request_id"),
            mpesa_receipt=result.get("mpesa_receipt"),
            transaction_id=result.get("transaction_id")
        )
        
    except Exception as e:
        logger.error(f"Callback processing error: {str(e)}")
        return create_webhook_response(
            status="error",
            message=f"Callback processing failed: {str(e)}"
        )


# ─── SERVICE ACCESS ──────────────────────────────────────────────

@router.get("/mpesa/check-access/{service_code}", response_model=ServiceAccessResponse)
async def check_service_access(
    service_code: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Check if user has access to a service.
    
    GET /api/v1/mpesa/check-access/{service_code}
    
    Requires authentication.
    """
    try:
        result = await mpesa_service.check_service_access(
            user_id=current_user.get("id"),
            service_code=service_code
        )
        
        return create_service_access_response(
            has_access=result["has_access"],
            status=result["status"],
            expires_at=result.get("expires_at"),
            message=result.get("message", "")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check access: {str(e)}"
        )


@router.get("/mpesa/user/services", response_model=UserServicesResponse)
async def get_user_services(
    current_user: dict = Depends(get_current_user)
):
    """
    Get all services a user has access to.
    
    GET /api/v1/mpesa/user/services
    
    Requires authentication.
    """
    try:
        services = await mpesa_service.get_user_services(current_user.get("id"))
        return {"services": services}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user services: {str(e)}"
        )


@router.get("/mpesa/user/services-list")
async def get_user_services_list(
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed list of user services with metadata.
    
    GET /api/v1/mpesa/user/services-list
    
    Requires authentication.
    """
    try:
        services = await mpesa_service.get_user_services(current_user.get("id"))
        
        # Get service details
        all_services = await mpesa_service.get_available_services()
        
        result = []
        for service in all_services:
            code = service.get("code")
            result.append({
                "code": code,
                "name": service.get("name"),
                "price": service.get("price"),
                "description": service.get("description"),
                "icon": service.get("icon"),
                "has_access": services.get(code, False)
            })
        
        return {"services": result}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user services: {str(e)}"
        )


# ─── PAYMENT HISTORY ──────────────────────────────────────────────

@router.get("/mpesa/payments", response_model=PaymentHistoryResponse)
async def get_payments(
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's payment history.
    
    GET /api/v1/mpesa/payments
    
    Requires authentication.
    """
    try:
        payments = await mpesa_service.get_user_payments(current_user.get("id"))
        return {"payments": payments}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payments: {str(e)}"
        )


# ─── AVAILABLE SERVICES ──────────────────────────────────────────

@router.get("/mpesa/services", response_model=AvailableServicesResponse)
async def get_services(
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get all available services.
    
    GET /api/v1/mpesa/services
    
    Optional authentication. If authenticated, includes access status.
    """
    try:
        services = await mpesa_service.get_available_services()
        
        # If user is authenticated, add access status
        if current_user:
            user_id = current_user.get("id")
            user_services = await mpesa_service.get_user_services(user_id)
            
            for service in services:
                code = service.get("code")
                service["has_access"] = user_services.get(code, False)
        
        return {"services": services}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get services: {str(e)}"
        )


@router.get("/mpesa/services/{service_code}")
async def get_service(
    service_code: str,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get a specific service by code.
    
    GET /api/v1/mpesa/services/{service_code}
    """
    try:
        service = await mpesa_service.get_service_by_code(service_code)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service '{service_code}' not found"
            )
        
        # If user is authenticated, add access status
        if current_user:
            user_id = current_user.get("id")
            user_services = await mpesa_service.get_user_services(user_id)
            service["has_access"] = user_services.get(service_code, False)
        
        return service
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service: {str(e)}"
        )


# ─── HEALTH CHECK ──────────────────────────────────────────────────

@router.get("/mpesa/health", response_model=MpesaHealthResponse)
async def health():
    """
    Health check for M-Pesa service.
    
    GET /api/v1/mpesa/health
    """
    from app.core.config import settings
    
    return {
        "status": "healthy",
        "service": "mpesa",
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.MPESA_ENVIRONMENT,
        "shortcode": settings.MPESA_SHORTCODE
    }


# ─── WEBHOOK TEST ──────────────────────────────────────────────────

@router.post("/mpesa/webhook-test")
async def webhook_test(request: Request):
    """
    Test webhook endpoint for debugging.
    
    POST /api/v1/mpesa/webhook-test
    """
    try:
        body = await request.json()
        return {
            "status": "received",
            "payload": body,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
