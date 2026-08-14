"""
app/modules/valuation/router.py

Valuation API routes.

POST /api/v1/valuation/calculate

Flow:

    Frontend
        ↓
    FastAPI router
        ↓
    ValuationEngine
        ↓
    ValuationRepository
        ↓
    calculate_vehicle_valuation()
        ↓
    PostgreSQL
        ↓
    ValuationResponse
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import get_supabase
from app.core.security import decode_token

from .engine import ValuationEngine, ValuationEngineError
from .repository import ValuationRepository
from .schemas import ValuationRequest, ValuationResponse


logger = logging.getLogger(__name__)


# =====================================================================
# ROUTER
# =====================================================================

router = APIRouter(
    prefix="/valuation",
    tags=["valuation"],
)


# =====================================================================
# AUTHENTICATION
# =====================================================================

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        _bearer_scheme
    ),
) -> dict[str, Any]:
    """
    Validate the Authorization Bearer token.

    Returns decoded user claims.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        user = decode_token(credentials.credentials)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )

        return user

    except HTTPException:
        raise

    except ValueError as exc:
        logger.warning(
            "Authentication failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    except Exception:
        logger.exception(
            "Unexpected authentication error"
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )


# =====================================================================
# ENGINE DEPENDENCY
# =====================================================================

def get_engine(
    supabase=Depends(get_supabase),
) -> ValuationEngine:
    """
    Build the valuation engine using the application's
    configured Supabase client.
    """

    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Valuation database is unavailable",
        )

    repository = ValuationRepository(supabase)

    return ValuationEngine(repository)


# =====================================================================
# VALIDATE REQUEST
# =====================================================================

def _validate_payload(payload: ValuationRequest) -> None:
    """
    Final defensive validation before the request reaches the
    CRSP repository.

    This protects against the frontend accidentally sending:

        make: ""
        model: ""

    which was one of the errors appearing in the logs.
    """

    make = (payload.make or "").strip()
    model = (payload.model or "").strip()

    if not make or not model:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "INVALID_VEHICLE",
                "message": "Make and model are required for valuation",
                "make": make,
                "model": model,
            },
        )


# =====================================================================
# CALCULATE VALUATION
# =====================================================================

@router.post(
    "/calculate",
    response_model=ValuationResponse,
    status_code=status.HTTP_200_OK,
)
async def calculate_valuation(
    payload: ValuationRequest,
    engine: ValuationEngine = Depends(get_engine),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> ValuationResponse:
    """
    Calculate a vehicle valuation.

    The PostgreSQL function:

        calculate_vehicle_valuation()

    remains the authoritative valuation calculation.

    Python is responsible for:

    - request validation
    - CRSP selection
    - enum normalization
    - calling the SQL function
    - shaping the API response
    """

    # ---------------------------------------------------------------
    # Validate request
    # ---------------------------------------------------------------

    _validate_payload(payload)

    logger.info(
        "Valuation request: make=%r model=%r trim=%r "
        "year=%s mileage=%s",
        payload.make,
        payload.model,
        payload.trim,
        payload.year,
        payload.mileage,
    )

    # ---------------------------------------------------------------
    # Calculate
    # ---------------------------------------------------------------

    try:

        result = engine.calculate(payload)

        if result is None:
            logger.error(
                "Valuation engine returned None"
            )

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "error": "NO_VALUATION_RESULT",
                    "message": "No valuation data received",
                },
            )

        logger.info(
            "Valuation successful: crsp_id=%s "
            "reference=%s final_value=%s",
            result.data.crsp.crsp_id,
            result.data.report.report_number,
            result.data.valuation.estimated_vehicle_value,
        )

        return result

    # ---------------------------------------------------------------
    # Known valuation errors
    # ---------------------------------------------------------------

    except ValuationEngineError as exc:

        logger.warning(
            "Valuation request failed: %s",
            exc.message,
        )

        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "error": "VALUATION_ERROR",
                "message": exc.message,
            },
        ) from exc

    # ---------------------------------------------------------------
    # FastAPI HTTP errors
    # ---------------------------------------------------------------

    except HTTPException:
        raise

    # ---------------------------------------------------------------
    # Unexpected errors
    # ---------------------------------------------------------------

    except Exception as exc:

        logger.exception(
            "Unexpected error during valuation"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_VALUATION_ERROR",
                "message": "An unexpected error occurred during valuation",
            },
        ) from exc
