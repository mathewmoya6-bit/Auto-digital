# app/modules/mpesa/router.py
from fastapi import APIRouter, Depends, Request
from app.core.database import get_supabase
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
    return await mpesa_service.initiate_payment(
        phone=request.phone,
        service_id=request.service_id,
        description=request.description,
        user_id=current_user["id"],
        request_id=request.request_id,
        amount=request.amount
    )


@router.get("/mpesa/status/{checkout_request_id}")
async def payment_status(
    checkout_request_id: str,
    current_user: dict = Depends(get_current_user)
):
    return await mpesa_service.get_payment_status(checkout_request_id, current_user["id"])


@router.post("/mpesa/confirm/{checkout_request_id}")
async def confirm_payment(
    checkout_request_id: str,
    current_user: dict = Depends(get_current_user)
):
    return await mpesa_service.confirm_payment(checkout_request_id, current_user["id"])


@router.post("/mpesa/callback")
async def mpesa_callback(request: Request):
    body = await request.json()
    return await callback_handler.process_callback(body)


@router.get("/mpesa/payments")
async def get_payments(current_user: dict = Depends(get_current_user)):
    return await mpesa_service.get_user_payments(current_user["id"])


@router.get("/mpesa/user/services")
async def get_user_services(current_user: dict = Depends(get_current_user)):
    return await mpesa_service.get_user_services(current_user["id"])


@router.get("/mpesa/services")
async def get_services():
    supabase = get_supabase()
    response = supabase.table("services").select("*").eq("active", True).order("display_order").execute()

    if not response.data:
        return {
            "services": [
                {"id": "1", "code": "mileage", "name": "Mileage Calculator", "price": 100, "currency": "KES", "icon": "📈", "active": True},
                {"id": "2", "code": "valuation", "name": "Instant Vehicle Value", "price": 150, "currency": "KES", "icon": "💰", "active": True},
                {"id": "3", "code": "ownership", "name": "Ownership Cost Report", "price": 200, "currency": "KES", "icon": "📊", "active": True}
            ],
            "count": 3
        }

    return {"services": response.data, "count": len(response.data)}
