# backend/app/api/v1/endpoints/mpesa.py
"""
M-Pesa API Endpoints - Version 1
Handles STK Push, payment status, service access, and webhooks
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from fastapi.responses import JSONResponse
from datetime import datetime

from app.services.mpesa_service import MpesaService
from app.core.database import db
from app.core.security import get_current_user, verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter()
mpesa_service = MpesaService()


# ─── Health & Configuration ──────────────────────────────────────────

@router.get("/mpesa/health")
async def mpesa_health():
    """
    Check M-Pesa service health and configuration.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "environment": mpesa_service.environment,
        "shortcode": mpesa_service.shortcode,
        "callback_url": mpesa_service.callback_url
    }


@router.get("/mpesa/shortcode")
async def get_shortcode():
    """
    Get the configured M-Pesa shortcode.
    """
    return {
        "success": True,
        "shortcode": mpesa_service.shortcode,
        "environment": mpesa_service.environment
    }


# ─── STK Push Payment ────────────────────────────────────────────────

@router.post("/mpesa/stkpush")
async def initiate_stk_push(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Initiate an M-Pesa STK Push payment.
    
    Request Body:
    {
        "phone": "0712345678",
        "amount": 100,
        "account_reference": "mileage",
        "description": "Auto-D: Mileage Calculator"
    }
    """
    try:
        data = await request.json()
        
        phone = data.get('phone', '').strip()
        amount = data.get('amount')
        account_reference = data.get('account_reference', 'AUTO-D')
        description = data.get('description', 'Auto-D Payment')
        
        # Validate inputs
        if not phone:
            raise HTTPException(status_code=400, detail="Phone number is required")
        
        if not amount or amount <= 0:
            raise HTTPException(status_code=400, detail="Valid amount is required")
        
        # Get user ID from authenticated user
        user_id = current_user.get('id') if current_user else None
        
        # Initiate STK Push
        result = mpesa_service.initiate_stk_push(
            phone=phone,
            amount=amount,
            account_reference=account_reference,
            description=description,
            user_id=user_id
        )
        
        if result.get('success'):
            return {
                "success": True,
                "checkout_request_id": result.get('checkout_request_id'),
                "message": "STK Push sent successfully",
                "response_description": result.get('response_description')
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get('error', 'STK Push failed')
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ STK Push error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── M-Pesa Callback ─────────────────────────────────────────────────

@router.post("/mpesa/callback")
async def mpesa_callback(request: Request):
    """
    M-Pesa callback endpoint for STK Push results.
    This endpoint is called by Safaricom when payment is completed.
    """
    try:
        data = await request.json()
        logger.info(f"📩 M-Pesa callback received")
        
        # Process the callback
        success = mpesa_service.process_callback(data)
        
        if success:
            return {"success": True, "message": "Callback processed successfully"}
        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Failed to process callback"}
            )
            
    except Exception as e:
        logger.error(f"❌ Callback error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )


# ─── Payment Status ──────────────────────────────────────────────────

@router.get("/mpesa/status/{checkout_request_id}")
async def get_payment_status(
    checkout_request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Check the status of a payment.
    """
    try:
        result = mpesa_service.get_payment_status(checkout_request_id)
        
        if result.get('success'):
            return result
        else:
            raise HTTPException(status_code=404, detail=result.get('error', 'Payment not found'))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Status check error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Manual Payment Confirmation ─────────────────────────────────────

@router.post("/mpesa/confirm/{checkout_request_id}")
async def confirm_payment_manually(
    checkout_request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Manually confirm a payment (for cases where callback fails).
    """
    try:
        user_id = current_user.get('id') if current_user else None
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")
        
        result = mpesa_service.confirm_payment_manually(checkout_request_id, user_id)
        
        if result.get('success'):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Confirmation failed'))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Confirm payment error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Services ─────────────────────────────────────────────────────────

@router.get("/mpesa/services")
async def get_services(
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of all available services with prices.
    """
    try:
        services = mpesa_service.get_all_services()
        return {
            "success": True,
            "services": services
        }
    except Exception as e:
        logger.error(f"❌ Get services error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mpesa/user/services")
async def get_user_services(
    current_user: dict = Depends(get_current_user)
):
    """
    Get unlocked services for the authenticated user.
    """
    try:
        user_id = current_user.get('id') if current_user else None
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")
        
        services = mpesa_service.get_user_services(user_id)
        return {
            "success": True,
            "services": services
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get user services error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mpesa/user/services/{service_id}/status")
async def check_service_access(
    service_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Check if a specific service is unlocked for the user.
    """
    try:
        user_id = current_user.get('id') if current_user else None
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")
        
        services = mpesa_service.get_user_services(user_id)
        is_unlocked = any(s.get('service_id') == service_id for s in services)
        
        return {
            "success": True,
            "service_id": service_id,
            "unlocked": is_unlocked,
            "service_name": mpesa_service.get_service_name(service_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Check service access error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Payment History ──────────────────────────────────────────────────

@router.get("/mpesa/payments")
async def get_payment_history(
    current_user: dict = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """
    Get payment history for the authenticated user.
    """
    try:
        user_id = current_user.get('id') if current_user else None
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")
        
        # Query payments from database
        response = db.table('payments') \
            .select('*') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .limit(limit) \
            .offset(offset) \
            .execute()
        
        payments = response.data if response.data else []
        
        return {
            "success": True,
            "payments": payments,
            "total": len(payments)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get payment history error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Webhook (Testing) ───────────────────────────────────────────────

@router.post("/mpesa/webhook")
async def webhook_receiver(request: Request):
    """
    Generic webhook endpoint for testing.
    """
    try:
        data = await request.json()
        logger.info(f"📩 Webhook received: {str(data)[:500]}")
        return {"success": True, "message": "Webhook received"}
    except Exception as e:
        logger.error(f"❌ Webhook error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )


# ─── Admin Endpoints ──────────────────────────────────────────────────

@router.post("/mpesa/admin/service-prices")
async def set_service_price(
    request: Request,
    current_user: dict = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """
    Admin endpoint to set service prices.
    """
    try:
        # Verify admin role
        if current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")
        
        data = await request.json()
        service_type = data.get('service_type')
        price = data.get('price')
        
        if not service_type or price is None:
            raise HTTPException(status_code=400, detail="service_type and price are required")
        
        # Insert into database
        response = db.table('service_prices').insert({
            'service_type': service_type,
            'price': price,
            'created_at': datetime.now().isoformat()
        }).execute()
        
        if response.data:
            return {
                "success": True,
                "message": f"Price for {service_type} set to {price}",
                "data": response.data[0]
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to set price")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Set service price error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mpesa/admin/stats")
async def get_mpesa_stats(
    current_user: dict = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """
    Admin endpoint to get M-Pesa payment statistics.
    """
    try:
        # Verify admin role
        if current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get total payments
        total_response = db.table('payments') \
            .select('*') \
            .execute()
        
        # Get successful payments
        success_response = db.table('payments') \
            .select('*') \
            .eq('status', 'completed') \
            .execute()
        
        # Get failed payments
        failed_response = db.table('payments') \
            .select('*') \
            .eq('status', 'failed') \
            .execute()
        
        # Calculate total amount
        total_amount = sum(p.get('amount', 0) for p in total_response.data) if total_response.data else 0
        
        return {
            "success": True,
            "stats": {
                "total_payments": len(total_response.data) if total_response.data else 0,
                "successful_payments": len(success_response.data) if success_response.data else 0,
                "failed_payments": len(failed_response.data) if failed_response.data else 0,
                "total_amount": total_amount,
                "currency": "KES"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get M-Pesa stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
