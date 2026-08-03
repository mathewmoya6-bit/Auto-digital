# app/modules/mpesa/router.py
# Auto-D Kenya - M-Pesa Routes
# ================================================================
# TYPE: MODULE - M-Pesa API routes

import logging
import time
from collections import defaultdict, deque
from datetime import timezone, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.dependencies import get_current_user, get_current_user_optional
from app.core.exceptions import ValidationException, NotFoundException, AppException
from app.core.security import mask_sensitive
from app.modules.mpesa.service import MpesaService
from app.modules.mpesa.schemas import (
    MpesaPaymentRequest,
    MpesaPaymentResponse,
    PaymentStatusResponse,
    ServiceAccessResponse,
    UserServicesResponse,
    AvailableServicesResponse,
    PaymentHistoryResponse,
    create_payment_response,
    create_service_access_response,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── SERVICE DEPENDENCY ──────────────────────────────────────────
# One instance reused for the life of the process to preserve OAuth token cache

_mpesa_service_singleton = MpesaService()


def get_mpesa_service() -> MpesaService:
    return _mpesa_service_singleton


# ─── MINIMAL IN-MEMORY RATE LIMITER ─────────────────────────────

_rate_buckets: dict[str, deque] = defaultdict(deque)


def _rate_limit(key: str, max_requests: int = 5, window_seconds: int = 60):
    now = time.monotonic()
    bucket = _rate_buckets[key]
    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()
    if len(bucket) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests, slow down."
        )
    bucket.append(now)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


class ServiceDetailResponse(BaseModel):
    """Response model for GET /mpesa/services/{service_id}"""
    id: int
    code: Optional[str] = None
    name: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = "KES"
    description: Optional[str] = None
    icon: Optional[str] = None
    has_access: Optional[bool] = None


# ─── EXCEPTION HANDLERS ─────────────────────────────────────────

def handle_api_error(e: Exception) -> HTTPException:
    """Convert domain exceptions to HTTP exceptions."""
    if isinstance(e, ValidationException):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    elif isinstance(e, NotFoundException):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    elif isinstance(e, AppException):
        return HTTPException(status_code=e.status_code, detail=str(e))
    else:
        logger.exception(f"Unexpected error: {str(e)}")
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# ─── STK PUSH ──────────────────────────────────────────────────────

@router.post("/mpesa/stkpush", response_model=MpesaPaymentResponse)
async def stk_push(
    request: MpesaPaymentRequest,
    current_user: dict = Depends(get_current_user),
    mpesa_service: MpesaService = Depends(get_mpesa_service)
):
    """
    Initiate M-Pesa STK Push payment.

    POST /api/v1/mpesa/stkpush

    Requires authentication.
    """
    _rate_limit(f"stkpush:{current_user.get('id')}", max_requests=5, window_seconds=60)

    try:
        # Fix: plain f-string log instead of extra= dict
        logger.info(
            f"STK Push initiated | user={current_user.get('id')} "
            f"service={request.service_id} "
            f"phone=***{request.phone[-4:] if request.phone else 'N/A'}"
        )

        # Fix: Removed request_id parameter (not used)
        result = await mpesa_service.initiate_payment(
            phone=request.phone,
            service_id=request.service_id,
            description=request.description,
            user_id=current_user.get("id"),
            amount=request.amount
        )

        return create_payment_response(
            checkout_request_id=result["checkout_request_id"],
            message=result.get("message", "STK push sent successfully"),
            status=result.get("status", "pending")
        )

    except Exception as e:
        raise handle_api_error(e)


@router.post("/mpesa/stkpush-public", response_model=MpesaPaymentResponse)
async def stk_push_public(
    request: MpesaPaymentRequest,
    req: Request,
    x_api_key: Optional[str] = Header(None),
    mpesa_service: MpesaService = Depends(get_mpesa_service)
):
    """
    Initiate M-Pesa STK Push payment (public endpoint).

    POST /api/v1/mpesa/stkpush-public

    Protected by a shared API key.
    """
    if settings.PUBLIC_API_KEY and x_api_key != settings.PUBLIC_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    _rate_limit(f"stkpush-public:{_client_ip(req)}", max_requests=5, window_seconds=60)

    try:
        # Fix: Removed request_id parameter (not used)
        result = await mpesa_service.initiate_payment(
            phone=request.phone,
            service_id=request.service_id,
            description=request.description,
            user_id=request.user_id,
            amount=request.amount
        )

        return create_payment_response(
            checkout_request_id=result["checkout_request_id"],
            message=result.get("message", "STK push sent successfully"),
            status=result.get("status", "pending")
        )

    except Exception as e:
        raise handle_api_error(e)


# ─── PAYMENT STATUS ───────────────────────────────────────────────

@router.get("/mpesa/status/{checkout_request_id}", response_model=PaymentStatusResponse)
async def payment_status(
    checkout_request_id: str,
    current_user: dict = Depends(get_current_user),
    mpesa_service: MpesaService = Depends(get_mpesa_service)
):
    """
    Get payment status.

    GET /api/v1/mpesa/status/{checkout_request_id}

    Requires authentication.
    """
    try:
        result = await mpesa_service.get_payment_status(checkout_request_id, current_user.get("id"))
        return result

    except Exception as e:
        raise handle_api_error(e)


# ─── CONFIRM PAYMENT ──────────────────────────────────────────────
# DELETED: confirm_payment endpoint removed as callback is now the only source of truth


# ─── CALLBACK ──────────────────────────────────────────────────────

@router.post("/mpesa/callback")
async def mpesa_callback(
    request: Request,
    mpesa_service: MpesaService = Depends(get_mpesa_service)
):
    """
    M-Pesa callback webhook.

    POST /api/v1/mpesa/callback

    This is called by Safaricom when the payment is completed.
    This is the ONLY place where services are unlocked.

    Requires MPESA_CALLBACK_SECRET as query param or header.
    """
    if settings.MPESA_CALLBACK_SECRET:
        provided_secret = request.headers.get("X-Callback-Secret") or request.query_params.get("secret")
        if provided_secret != settings.MPESA_CALLBACK_SECRET:
            logger.warning(f"Rejected callback with invalid/missing secret from {_client_ip(request)}")
            return JSONResponse(status_code=200, content={"ResultCode": 0, "ResultDesc": "Accepted"})

    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" not in content_type:
            logger.warning(f"Callback invalid content type: {content_type}")
            return JSONResponse(status_code=200, content={"ResultCode": 0, "ResultDesc": "Accepted"})

        body = await request.json()
    except Exception:
        logger.warning("Invalid/unparseable callback JSON")
        return JSONResponse(status_code=200, content={"ResultCode": 0, "ResultDesc": "Accepted"})

    if not body.get("Body", {}).get("stkCallback"):
        logger.warning("Callback missing Body.stkCallback")
        return JSONResponse(status_code=200, content={"ResultCode": 0, "ResultDesc": "Accepted"})

    try:
        checkout_id = body.get("Body", {}).get("stkCallback", {}).get("CheckoutRequestID")
        result_code = body.get("Body", {}).get("stkCallback", {}).get("ResultCode")

        logger.info(
            f"Callback received | checkout_id={mask_sensitive(checkout_id)} "
            f"result_code={result_code}"
        )

        result = await mpesa_service.stk_push.process_callback(body)

        if result and result.get("status") == "error":
            logger.error(f"Callback processed with error | checkout_id={mask_sensitive(checkout_id)} result={result}")
        else:
            logger.info(f"Callback processed | checkout_id={mask_sensitive(checkout_id)} result={result}")

        return JSONResponse(status_code=200, content={"ResultCode": 0, "ResultDesc": "Accepted"})

    except Exception:
        logger.exception("Callback processing failed")
        return JSONResponse(status_code=200, content={"ResultCode": 0, "ResultDesc": "Accepted"})


# ─── SERVICE ACCESS ──────────────────────────────────────────────

@router.get("/mpesa/check-access/{service_id}", response_model=ServiceAccessResponse)
async def check_service_access(
    service_id: int,
    current_user: dict = Depends(get_current_user),
    mpesa_service: MpesaService = Depends(get_mpesa_service)
):
    """
    Check if user has access to a service.

    GET /api/v1/mpesa/check-access/{service_id}

    Requires authentication.
    """
    try:
        result = await mpesa_service.check_service_access(
            user_id=current_user.get("id"),
            service_id=service_id
        )

        return create_service_access_response(
            has_access=result["has_access"],
            status=result["status"],
            expires_at=result.get("expires_at"),
            message=result.get("message", "")
        )

    except Exception as e:
        raise handle_api_error(e)


@router.get("/mpesa/user/services", response_model=UserServicesResponse)
async def get_user_services(
    current_user: dict = Depends(get_current_user),
    mpesa_service: MpesaService = Depends(get_mpesa_service)
):
    """
    Get all services a user has access to.

    GET /api/v1/mpesa/user/services

    Returns: { "services": { service_id: true/false } }

    Requires authentication.
    """
    try:
        services = await mpesa_service.get_user_services(current_user.get("id"))
        return {"services": services}

    except Exception as e:
        raise handle_api_error(e)


@router.get("/mpesa/user/services-list")
async def get_user_services_list(
    current_user: dict = Depends(get_current_user),
    mpesa_service: MpesaService = Depends(get_mpesa_service)
):
    """
    Get detailed list of user services with metadata.

    GET /api/v1/mpesa/user/services-list

    Requires authentication.
    """
    try:
        user_service_map = await mpesa_service.get_user_services(current_user.get("id"))
        all_services = await mpesa_service.get_available_services()

        result = []
        for service in all_services:
            service_id = service.get("id")
            result.append({
                "id": service_id,
                "code": service.get("code"),
                "name": service.get("name"),
                "price": service.get("price"),
                "currency": service.get("currency", "KES"),
                "description": service.get("description"),
                "icon": service.get("icon"),
                "has_access": user_service_map.get(service_id, False)
            })

        return {"services": result}

    except Exception as e:
        raise handle_api_error(e)


# ─── PAYMENT HISTORY ──────────────────────────────────────────────

@router.get("/mpesa/payments", response_model=PaymentHistoryResponse)
async def get_payments(
    current_user: dict = Depends(get_current_user),
    mpesa_service: MpesaService = Depends(get_mpesa_service)
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
        raise handle_api_error(e)


# ─── AVAILABLE SERVICES ──────────────────────────────────────────

@router.get("/mpesa/services", response_model=AvailableServicesResponse)
async def get_services(
    current_user: dict = Depends(get_current_user_optional),
    mpesa_service: MpesaService = Depends(get_mpesa_service)
):
    """
    Get all available services.

    GET /api/v1/mpesa/services

    Optional authentication. If authenticated, includes access status.
    """
    try:
        services = await mpesa_service.get_available_services()

        if current_user:
            user_id = current_user.get("id")
            user_service_map = await mpesa_service.get_user_services(user_id)

            for service in services:
                service_id = service.get("id")
                service["has_access"] = user_service_map.get(service_id, False)

        return {"services": services}

    except Exception as e:
        raise handle_api_error(e)


@router.get("/mpesa/services/{service_id}", response_model=ServiceDetailResponse)
async def get_service(
    service_id: int,
    current_user: dict = Depends(get_current_user_optional),
    mpesa_service: MpesaService = Depends(get_mpesa_service)
):
    """
    Get a specific service by ID.

    GET /api/v1/mpesa/services/{service_id}
    """
    try:
        services = await mpesa_service.get_available_services()
        service = None
        for s in services:
            if s.get("id") == service_id:
                service = s
                break

        if not service:
            raise NotFoundException(f"Service with ID {service_id} not found")

        if current_user:
            user_id = current_user.get("id")
            user_service_map = await mpesa_service.get_user_services(user_id)
            service["has_access"] = user_service_map.get(service_id, False)

        return service

    except Exception as e:
        raise handle_api_error(e)


# ─── HEALTH CHECK ──────────────────────────────────────────────────

@router.get("/mpesa/health")
async def health(
    mpesa_service: MpesaService = Depends(get_mpesa_service)
):
    """
    Health check for M-Pesa service.

    GET /api/v1/mpesa/health
    """
    health_status = {
        "status": "healthy",
        "service": "mpesa",
        "version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.MPESA_ENVIRONMENT,
        "checks": {
            "oauth": False,
            "database": False
        }
    }

    try:
        health_status["checks"]["oauth"] = await mpesa_service.stk_push.health_check()
        if not health_status["checks"]["oauth"]:
            health_status["status"] = "degraded"
    except Exception as e:
        logger.warning(f"OAuth health check failed: {e}")
        health_status["checks"]["oauth"] = False
        health_status["status"] = "degraded"

    try:
        supabase = mpesa_service.stk_push.supabase
        supabase.table("services").select("id").limit(1).execute()
        health_status["checks"]["database"] = True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        health_status["checks"]["database"] = False
        health_status["status"] = "degraded"

    if not health_status["checks"]["oauth"] and not health_status["checks"]["database"]:
        health_status["status"] = "unhealthy"

    return health_status


# ─── WEBHOOK TEST ──────────────────────────────────────────────────

@router.post("/mpesa/webhook-test")
async def webhook_test(request: Request):
    """
    Test webhook endpoint for debugging.

    POST /api/v1/mpesa/webhook-test

    Only available when DEBUG=True.
    """
    if not getattr(settings, "DEBUG", False):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    try:
        body = await request.json()
        return {
            "status": "received",
            "payload": body,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.exception("Webhook test failed")
        return {
            "status": "error",
            "message": str(e)
        }
