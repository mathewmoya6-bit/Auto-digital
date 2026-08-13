"""
router.py

Exposes POST /api/v1/valuation/calculate — the endpoint the
"Instant Value Check" frontend calls via
CONFIG.API_BASE + CONFIG.ENDPOINTS.VALUATION.

Mount this router in your app the same way your other module routers
are mounted, e.g. in app/main.py:

    from app.modules.valuation.router import router as valuation_router

    app.include_router(valuation_router, prefix="/api/v1")

ASSUMPTIONS:
  - `get_supabase()` returns your configured Supabase client
    (swap the import for your actual dependency).
  - `get_current_user()` is your existing auth dependency that
    validates the `Authorization: Bearer <token>` header sent by
    the frontend's APIService and returns the authenticated user
    (or raises 401). If you don't have one yet, replace the
    Depends(get_current_user) call below with your own, or drop it
    to make the endpoint public.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import get_supabase
from app.core.security import decode_token

from .engine import ValuationEngine, ValuationEngineError
from .repository import ValuationRepository
from .schemas import ValuationRequest, ValuationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/valuation", tags=["valuation"])

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> Dict[str, Any]:
    """Resolve the authenticated user from the `Authorization: Bearer`
    header using app.core.security.decode_token(), which already
    supports both internal Auto-D HS256 tokens and Supabase
    ES256/RS256 tokens.

    NOTE: per decode_token()'s own docstring, Supabase tokens are
    decoded as *unverified* claims — fine for reading `sub`/`email`,
    but if this endpoint needs hard signature verification, swap this
    for a Supabase JWKS check or supabase.auth.get_user(token)
    instead. If your project already has a shared get_current_user
    dependency (e.g. wired through app/core/middleware.py), prefer
    that one over this local copy so auth behavior stays consistent
    across routers.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    try:
        return decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc


def get_engine(supabase=Depends(get_supabase)) -> ValuationEngine:
    return ValuationEngine(ValuationRepository(supabase))


@router.post("/calculate", response_model=ValuationResponse)
async def calculate_valuation(
    payload: ValuationRequest,
    engine: ValuationEngine = Depends(get_engine),
    current_user=Depends(get_current_user),
):
    """Calculate an AI-assisted vehicle valuation.

    Delegates to `calculate_vehicle_valuation`, the SQL function
    already validated against real CRSP data, and returns the result
    reshaped for the frontend's showValuationResult().
    """
    try:
        return engine.calculate(payload)
    except ValuationEngineError as exc:
        logger.warning("Valuation request failed: %s", exc.message)
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during valuation")
        raise HTTPException(status_code=500, detail="Internal valuation error") from exc
