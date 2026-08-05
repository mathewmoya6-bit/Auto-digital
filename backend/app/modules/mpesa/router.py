# app/modules/mpesa/router.py
# ================================================================
# Auto-D Kenya - M-Pesa API Router
# ================================================================

import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.dependencies import (
    get_current_user,
    get_current_user_optional,
)
from app.core.exceptions import (
    AppException,
    NotFoundException,
    ValidationException,
)
from app.core.security import mask_sensitive

from app.modules.mpesa.schemas import (
    AvailableServicesResponse,
    MpesaPaymentRequest,
    MpesaPaymentResponse,
    PaymentHistoryResponse,
    PaymentStatusResponse,
    ServiceAccessResponse,
    UserServicesResponse,
    create_payment_response,
    create_service_access_response,
)

from app.modules.mpesa.service import MpesaService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["M-Pesa"])


# ================================================================
# Singleton Service
# ================================================================

_mpesa_service = MpesaService()


def get_mpesa_service() -> MpesaService:
    return _mpesa_service


# ================================================================
# Simple Rate Limiter
# ================================================================

_rate_buckets: dict[str, deque] = defaultdict(deque)


def rate_limit(
    key: str,
    max_requests: int = 5,
    window: int = 60,
):
    now = time.monotonic()
    bucket = _rate_buckets[key]

    while bucket and now - bucket[0] > window:
        bucket.popleft()

    if len(bucket) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests.",
        )

    bucket.append(now)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ================================================================
# Response Models
# ================================================================

class ServiceDetailResponse(BaseModel):
    id: int
    code: Optional[str] = None
    name: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = "KES"
    description: Optional[str] = None
    icon: Optional[str] = None
    has_access: Optional[bool] = False


# ================================================================
# Exception Converter
# ================================================================

def api_error(exc: Exception):
    """Convert domain exceptions to HTTP exceptions."""

    if isinstance(exc, ValidationException):
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    if isinstance(exc, NotFoundException):
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    if isinstance(exc, AppException):
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        )

    logger.exception(exc)

    raise HTTPException(
        status_code=500,
        detail="Internal server error",
    )


# ================================================================
# STK PUSH
# ================================================================

@router.post(
    "/mpesa/stkpush",
    response_model=MpesaPaymentResponse,
)
async def stk_push(
    request: MpesaPaymentRequest,
    current_user: dict = Depends(get_current_user),
    mpesa_service: MpesaService = Depends(get_mpesa_service),
):
    """
    Initiate an STK Push payment.

    Requires authentication.
    """
    rate_limit(f"stk:{current_user['id']}")

    try:
        logger.info(
            f"STK Push | "
            f"user={current_user['id']} "
            f"service={request.service_id} "
            f"phone=***{request.phone[-4:]}"
        )

        result = await mpesa_service.initiate_payment(
            phone=request.phone,
            service_id=request.service_id,
            description=request.description,
            user_id=current_user["id"],
            amount=request.amount,
        )

        return create_payment_response(
            checkout_request_id=result["checkout_request_id"],
            message=result.get(
                "customer_message",
                "STK Push sent successfully.",
            ),
            status=result.get(
                "status",
                "pending",
            ),
        )

    except Exception as exc:
        api_error(exc)


# ================================================================
# Public STK Push
# ================================================================

@router.post(
    "/mpesa/stkpush-public",
    response_model=MpesaPaymentResponse,
)
async def stk_push_public(
    request: MpesaPaymentRequest,
    http_request: Request,
    x_api_key: Optional[str] = Header(default=None),
    mpesa_service: MpesaService = Depends(get_mpesa_service),
):
    """
    Initiate an STK Push payment without authentication.

    Requires valid API key.
    """
    if (
        settings.PUBLIC_API_KEY
        and x_api_key != settings.PUBLIC_API_KEY
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )

    rate_limit(f"public:{client_ip(http_request)}")

    try:
        result = await mpesa_service.initiate_payment(
            phone=request.phone,
            service_id=request.service_id,
            description=request.description,
            user_id=request.user_id,
            amount=request.amount,
        )

        return create_payment_response(
            checkout_request_id=result["checkout_request_id"],
            message=result.get(
                "customer_message",
                "STK Push sent successfully.",
            ),
            status=result.get(
                "status",
                "pending",
            ),
        )

    except Exception as exc:
        api_error(exc)


# ================================================================
# Payment Status
# ================================================================

@router.get(
    "/mpesa/status/{checkout_request_id}",
    response_model=PaymentStatusResponse,
)
async def payment_status(
    checkout_request_id: str,
    current_user: dict = Depends(get_current_user),
    mpesa_service: MpesaService = Depends(get_mpesa_service),
):
    """
    Check the status of a payment.
    """
    try:
        return await mpesa_service.get_payment_status(
            checkout_request_id,
            current_user["id"],
        )

    except Exception as exc:
        api_error(exc)


# ================================================================
# CALLBACK (FIXED - removed secret verification)
# ================================================================

@router.post("/mpesa/callback")
async def mpesa_callback(
    request: Request,
    mpesa_service: MpesaService = Depends(get_mpesa_service),
):
    """
    Safaricom callback endpoint.

    Receives payment confirmation from M-Pesa.
    """
    try:
        body = await request.json()
    except Exception:
        logger.exception("Invalid callback payload")
        return JSONResponse(
            status_code=200,
            content={
                "ResultCode": 0,
                "ResultDesc": "Accepted",
            },
        )

    callback = body.get("Body", {}).get("stkCallback")

    if callback is None:
        logger.warning("Missing stkCallback")
        return JSONResponse(
            status_code=200,
            content={
                "ResultCode": 0,
                "ResultDesc": "Accepted",
            },
        )

    metadata = {}
    for item in callback.get("CallbackMetadata", {}).get("Item", []):
        metadata[item["Name"]] = item.get("Value")

    try:
        logger.info(
            "Processing callback %s",
            mask_sensitive(callback["CheckoutRequestID"]),
        )

        await mpesa_service.handle_callback(
            checkout_request_id=callback["CheckoutRequestID"],
            result_code=str(callback["ResultCode"]),
            result_desc=callback.get("ResultDesc", ""),
            receipt=metadata.get("MpesaReceiptNumber"),
            amount=metadata.get("Amount"),
            phone=str(metadata.get("PhoneNumber"))
            if metadata.get("PhoneNumber")
            else None,
            transaction_date=str(metadata.get("TransactionDate"))
            if metadata.get("TransactionDate")
            else None,
            callback_payload=body,
        )

    except Exception:
        logger.exception("Callback processing failed")

    return JSONResponse(
        status_code=200,
        content={
            "ResultCode": 0,
            "ResultDesc": "Accepted",
        },
    )


# ================================================================
# SERVICE ACCESS
# ================================================================

@router.get(
    "/mpesa/check-access/{service_id}",
    response_model=ServiceAccessResponse,
)
async def check_service_access(
    service_id: int,
    current_user: dict = Depends(get_current_user),
    mpesa_service: MpesaService = Depends(get_mpesa_service),
):
    """
    Check if the current user has access to a service.
    """
    try:
        result = await mpesa_service.check_service_access_by_id(
            user_id=current_user["id"],
            service_id=service_id,
        )

        return create_service_access_response(
            has_access=result["has_access"],
            status=result["status"],
            expires_at=result.get("expires_at"),
            message=result.get("message"),
        )

    except Exception as exc:
        api_error(exc)


# ================================================================
# USER SERVICES
# ================================================================

@router.get(
    "/mpesa/user/services",
    response_model=UserServicesResponse,
)
async def get_user_services(
    current_user: dict = Depends(get_current_user),
    mpesa_service: MpesaService = Depends(get_mpesa_service),
):
    """
    Get all services the user has access to.
    """
    try:
        services = await mpesa_service.get_user_services(
            current_user["id"]
        )

        return {
            "services": services,
        }

    except Exception as exc:
        api_error(exc)


@router.get("/mpesa/user/services-list")
async def get_user_services_list(
    current_user: dict = Depends(get_current_user),
    mpesa_service: MpesaService = Depends(get_mpesa_service),
):
    """
    Get all available services with access status for the current user.
    """
    try:
        user_services = await mpesa_service.get_user_services(
            current_user["id"]
        )

        services = await mpesa_service.get_available_services()

        results = []

        for service in services:
            code = service.get("code")

            results.append(
                {
                    "id": service.get("id"),
                    "code": code,
                    "name": service.get("name"),
                    "price": service.get("price"),
                    "currency": service.get(
                        "currency",
                        "KES",
                    ),
                    "description": service.get("description"),
                    "icon": service.get("icon"),
                    "has_access": user_services.get(
                        code,
                        False,
                    ),
                }
            )

        return {
            "services": results,
        }

    except Exception as exc:
        api_error(exc)


# ================================================================
# PAYMENT HISTORY
# ================================================================

@router.get(
    "/mpesa/payments",
    response_model=PaymentHistoryResponse,
)
async def get_payments(
    current_user: dict = Depends(get_current_user),
    mpesa_service: MpesaService = Depends(get_mpesa_service),
):
    """
    Get the current user's payment history.
    """
    try:
        payments = await mpesa_service.get_user_payments(
            current_user["id"]
        )

        return {
            "payments": payments,
        }

    except Exception as exc:
        api_error(exc)


# ================================================================
# AVAILABLE SERVICES
# ================================================================

@router.get(
    "/mpesa/services",
    response_model=AvailableServicesResponse,
)
async def get_services(
    current_user: Optional[dict] = Depends(get_current_user_optional),
    mpesa_service: MpesaService = Depends(get_mpesa_service),
):
    """
    Get all available services.

    If authenticated, includes access status for the current user.
    """
    try:
        services = await mpesa_service.get_available_services()

        if current_user:
            user_services = await mpesa_service.get_user_services(
                current_user["id"]
            )

            for service in services:
                code = service.get("code")
                service["has_access"] = user_services.get(
                    code,
                    False,
                )

        return {
            "services": services,
        }

    except Exception as exc:
        api_error(exc)


# ================================================================
# SERVICE DETAILS
# ================================================================

@router.get(
    "/mpesa/services/{service_id}",
    response_model=ServiceDetailResponse,
)
async def get_service(
    service_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    mpesa_service: MpesaService = Depends(get_mpesa_service),
):
    """
    Get details for a specific service.

    If authenticated, includes access status for the current user.
    """
    try:
        services = await mpesa_service.get_available_services()

        service = next(
            (
                s
                for s in services
                if s.get("id") == service_id
            ),
            None,
        )

        if service is None:
            raise NotFoundException(
                f"Service {service_id} not found."
            )

        if current_user:
            user_services = await mpesa_service.get_user_services(
                current_user["id"]
            )

            service["has_access"] = user_services.get(
                service.get("code"),
                False,
            )

        return service

    except Exception as exc:
        api_error(exc)


# ================================================================
# HEALTH CHECK
# ================================================================

@router.get("/mpesa/health")
async def health(
    mpesa_service: MpesaService = Depends(get_mpesa_service),
):
    """
    Health check for the M-Pesa module.

    Checks database connectivity and STK Push service availability.
    """
    status_data = {
        "status": "healthy",
        "service": "mpesa",
        "version": "2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": False,
            "stk_push": False,
        },
    }

    # Database check
    try:
        mpesa_service.supabase.table("services") \
            .select("id") \
            .limit(1) \
            .execute()

        status_data["checks"]["database"] = True

    except Exception as exc:
        logger.exception(exc)
        status_data["status"] = "degraded"

    # STK Push check
    try:
        if mpesa_service.stk_push:
            status_data["checks"]["stk_push"] = True

    except Exception:
        status_data["status"] = "degraded"

    if (
        not status_data["checks"]["database"]
        and
        not status_data["checks"]["stk_push"]
    ):
        status_data["status"] = "unhealthy"

    return status_data


# ================================================================
# WEBHOOK TEST
# ================================================================

@router.post("/mpesa/webhook-test")
async def webhook_test(request: Request):
    """
    Debug endpoint for testing webhooks.

    Enabled only in DEBUG mode.
    """
    if not settings.DEBUG:
        raise HTTPException(
            status_code=404,
            detail="Not Found",
        )

    try:
        payload = await request.json()

        logger.info("Webhook test payload received.")

        return {
            "success": True,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "payload": payload,
        }

    except Exception as exc:
        logger.exception(exc)

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": str(exc),
            },
        )


# ================================================================
# ROOT
# ================================================================

@router.get("/mpesa")
async def mpesa_root():
    """
    Root endpoint for the M-Pesa module.
    """
    return {
        "service": "Auto-D Kenya M-Pesa API",
        "status": "running",
        "version": "2.0",
    }
