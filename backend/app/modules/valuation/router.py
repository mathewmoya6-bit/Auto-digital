"""
routers/valuation_router.py

Exposes POST /api/v1/valuation/calculate — the endpoint the
"Instant Value Check" frontend calls via
CONFIG.API_BASE + CONFIG.ENDPOINTS.VALUATION.

Mount this router in your app with the same prefix your other
routers use, e.g.:

    from fastapi import FastAPI
    from routers.valuation_router import router as valuation_router

    app = FastAPI()
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

from fastapi import APIRouter, Depends, HTTPException

# TODO: point these at your actual project modules.
from app.db import get_supabase  # noqa: F401  (placeholder import)
from app.auth import get_current_user  # noqa: F401  (placeholder import)

from services.valuation_service import (
    ValuationError,
    ValuationRequest,
    ValuationService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/valuation", tags=["valuation"])


@router.post("/calculate")
async def calculate_valuation(
    payload: ValuationRequest,
    supabase=Depends(get_supabase),
    current_user=Depends(get_current_user),
):
    """Calculate an AI-assisted vehicle valuation.

    Delegates to `calculate_vehicle_valuation`, the SQL function
    already validated against real CRSP data, and returns the result
    reshaped for the frontend's showValuationResult().
    """
    service = ValuationService(supabase)
    try:
        return await service.calculate(payload)
    except ValuationError as exc:
        logger.warning("Valuation request failed: %s", exc.message)
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during valuation")
        raise HTTPException(status_code=500, detail="Internal valuation error") from exc
