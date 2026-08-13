
app/modules/valuation/router.py

Routes registered under prefix /api/v1/valuation (see main app include:
`app.include_router(valuation_router, prefix="/api/v1/valuation",
tags=["Valuation"])`).

Endpoint set matches openapi.json exactly:
  POST /calculate                       (auth required)
  POST /calculate-public                (no auth — used by public widgets)
  POST /quick                           (no auth, no persistence)
  POST /calculate-legacy                (back-compat shape, deprecated)
  GET  /health
  POST /bulk                            (auth required)
  POST /compare                         (auth required)
  GET  /history                         (auth required)
  GET  /history/{report_id}
  GET  /history/report/{report_number}
  GET  /stats

NOTE: instant-value.html currently calls plain "/valuation/calculate"
(not "-public") and always attaches a Bearer token because the make/
model/trim dropdowns themselves are gated behind Supabase auth
(`makeSelect.disabled = !authenticated`) — so `get_current_user` is a
hard dependency here, matching that flow. `/calculate-public` exists for
other embeds (e.g. a marketing landing page widget) that never gate on
sign-in.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import get_current_user, get_optional_user  # existing auth deps
from app.modules.valuation.schemas import (
    BulkValuationRequest,
    BulkValuationResponse,
    CompareValuationRequest,
    CompareValuationResponse,
    HealthResponse,
    ValuationBlock,
    ValuationHistoryItem,
    ValuationHistoryResponse,
    ValuationRequest,
    ValuationResponse,
    ValuationStatsResponse,
)
from app.modules.valuation.service import ValuationService, get_valuation_service

logger = logging.getLogger("valuation.router")

router = APIRouter()

ENGINE_VERSION = "2026.08"


def _service_dep() -> ValuationService:
    return get_valuation_service()


# ─────────────────────────────────────────────────────────────────────────
# Calculation endpoints
# ─────────────────────────────────────────────────────────────────────────

@router.post("/calculate", response_model=ValuationResponse, status_code=status.HTTP_200_OK)
async def calculate_valuation(
    payload: ValuationRequest,
    user=Depends(get_current_user),
    svc: ValuationService = Depends(_service_dep),
):
    """Authenticated valuation — the path instant-value.html actually calls."""
    try:
        data = await svc.calculate(payload, user_id=str(user.id), persist=True)
        return ValuationResponse(data=data)
    except Exception as exc:  # noqa: BLE001
        logger.exception("calculate_valuation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation calculation failed: {exc}",
        ) from exc


@router.post(
    "/calculate-public", response_model=ValuationResponse, status_code=status.HTTP_200_OK
)
async def calculate_valuation_public(
    payload: ValuationRequest,
    user=Depends(get_optional_user),
    svc: ValuationService = Depends(_service_dep),
):
    """Same engine, no auth gate — for public/embed widgets. Still
    persists (with user_id=None) so it shows up in aggregate stats.
    """
    try:
        data = await svc.calculate(
            payload, user_id=str(user.id) if user else None, persist=True
        )
        return ValuationResponse(data=data)
    except Exception as exc:  # noqa: BLE001
        logger.exception("calculate_valuation_public failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation calculation failed: {exc}",
        ) from exc


@router.post("/quick", response_model=ValuationBlock, status_code=status.HTTP_200_OK)
async def quick_valuation(
    payload: ValuationRequest,
    svc: ValuationService = Depends(_service_dep),
):
    """Fast ballpark estimate — no CRSP round-trip, no DB write."""
    try:
        return await svc.calculate_quick(payload)
    except Exception as exc:  # noqa: BLE001
        logger.exception("quick_valuation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quick valuation failed: {exc}",
        ) from exc


@router.post(
    "/calculate-legacy", response_model=ValuationResponse, status_code=status.HTTP_200_OK
)
async def calculate_valuation_legacy(
    payload: ValuationRequest,
    user=Depends(get_optional_user),
    svc: ValuationService = Depends(_service_dep),
):
    """Deprecated shape kept only so older cached frontend bundles (pre
    v6.0, before the flat `data.valuation.*` contract) don't 404 outright.
    Internally identical to /calculate-public; do not build new features
    against this path.
    """
    data = await svc.calculate(
        payload, user_id=str(user.id) if user else None, persist=True
    )
    return ValuationResponse(data=data)


# ─────────────────────────────────────────────────────────────────────────
# Bulk / compare
# ─────────────────────────────────────────────────────────────────────────

@router.post("/bulk", response_model=BulkValuationResponse)
async def bulk_valuation(
    payload: BulkValuationRequest,
    user=Depends(get_current_user),
    svc: ValuationService = Depends(_service_dep),
):
    results, failed = await svc.calculate_bulk(payload.items, user_id=str(user.id))
    return BulkValuationResponse(results=results, failed=failed)


@router.post("/compare", response_model=CompareValuationResponse)
async def compare_valuations(
    payload: CompareValuationRequest,
    user=Depends(get_current_user),
    svc: ValuationService = Depends(_service_dep),
):
    results, best_idx = await svc.compare(payload.items, user_id=str(user.id))
    return CompareValuationResponse(results=results, best_value=best_idx)


# ─────────────────────────────────────────────────────────────────────────
# History / stats
# ─────────────────────────────────────────────────────────────────────────

@router.get("/history", response_model=ValuationHistoryResponse)
async def get_valuation_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    svc: ValuationService = Depends(_service_dep),
):
    rows, total = await svc.get_history(str(user.id), page, page_size)
    items = [
        ValuationHistoryItem(
            report_id=row["id"],
            report_number=row["report_number"],
            make=row["make"],
            model=row["model"],
            year=row["year"],
            estimated_vehicle_value=row["estimated_vehicle_value"],
            created_at=row["created_at"],
        )
        for row in rows
    ]
    return ValuationHistoryResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/history/{report_id}")
async def get_valuation_report(
    report_id: UUID,
    user=Depends(get_current_user),
    svc: ValuationService = Depends(_service_dep),
):
    report = await svc.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.get("user_id") and report["user_id"] != str(user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this report")
    return report


@router.get("/history/report/{report_number}")
async def get_valuation_by_report_number(
    report_number: str,
    user=Depends(get_optional_user),
    svc: ValuationService = Depends(_service_dep),
):
    """No hard auth requirement — report numbers are unguessable UUID-
    suffixed tokens, used for e.g. sharing a printed report link. Owner-
    only fields are not exposed beyond what's already in the payload.
    """
    report = await svc.get_report_by_number(report_number)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/stats", response_model=ValuationStatsResponse)
async def get_valuation_stats(
    user=Depends(get_current_user),  # admin-ish aggregate — require auth
    svc: ValuationService = Depends(_service_dep),
):
    stats = await svc.get_stats()
    return ValuationStatsResponse(**stats)


# ─────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def valuation_health(svc: ValuationService = Depends(_service_dep)):
    crsp_available = True
    try:
        # Cheap liveness probe against the CRSP view — don't fail health
        # over a single flaky lookup.
        await svc._repo.get_crsp_by_fuzzy_match("Toyota", "Corolla", None, 2020)
    except Exception:  # noqa: BLE001
        crsp_available = False

    return HealthResponse(
        status="ok",
        engine_version=ENGINE_VERSION,
        crsp_lookup_available=crsp_available,
    )
