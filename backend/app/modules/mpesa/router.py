# app/modules/mpesa/router.py
# Auto-D Kenya - M-Pesa Routes
# ================================================================
# TYPE: MODULE - M-Pesa API routes

from fastapi import APIRouter, Depends, Request

from app.core.dependencies import get_current_user
from app.modules.mpesa.service import MpesaService
from app.modules.mpesa.callback import MpesaCallbackHandler
from app.modules.mpesa.schemas import MpesaPaymentRequest, MpesaPaymentResponse

router = APIRouter()
mpesa_service = MpesaService()
callback_handler = MpesaCallbackHandler()


@router.post("/mpesa/stkpush", response_model=MpesaPaymentResponse)
async def stk_push(
    request: MpesaPaymentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Initiate an M-Pesa STK push payment."""
    result = await mpesa_service.initiate_payment(
        phone=request.phone,
        service_id=request.service_id,
        description=request.description,
        user_id=current_user["id"],
        request_id=request.request_id,
        amount=request.amount
    )
    return result


@router.get("/mpesa/status/{checkout_request_id}")
async def payment_status(checkout_request_id: str):
    """Query the status of a payment."""
    return await mpesa_service.get_payment_status(checkout_request_id)


@router.post("/mpesa/confirm/{checkout_request_id}")
async def confirm_payment(checkout_request_id: str):
    """Confirm a payment and unlock the service."""
    return await mpesa_service.confirm_payment(checkout_request_id)


@router.post("/mpesa/callback")
async def mpesa_callback(request: Request):
    """M-Pesa callback endpoint."""
    body = await request.json()
    result = await callback_handler.process_callback(body)
    return result


@router.get("/mpesa/payments")
async def get_payments(current_user: dict = Depends(get_current_user)):
    """Get payment history for the current user."""
    return await mpesa_service.get_user_payments(current_user["id"])


@router.get("/mpesa/user/services")
async def get_user_services(current_user: dict = Depends(get_current_user)):
    """Get services purchased by the user."""
    return await mpesa_service.get_user_services(current_user["id"])


@router.get("/mpesa/services")
async def get_services():
    """Get all available services."""
    supabase = get_supabase()
    response = supabase.table("services").select("*").eq("active", True).order("display_order").execute()
    
    if not response.data:
        # Fallback services
        return {
            "services": [
                {"id": "1", "code": "mileage", "name": "Mileage Calculator", "price": 100, "currency": "KES", "icon": "📈", "active": True},
                {"id": "2", "code": "valuation", "name": "Instant Vehicle Value", "price": 150, "currency": "KES", "icon": "💰", "active": True},
                {"id": "3", "code": "ownership", "name": "Ownership Cost Report", "price": 200, "currency": "KES", "icon": "📊", "active": True}
            ],
            "count": 3
        }
    
    return {"services": response.data, "count": len(response.data)}
