"""
app/modules/valuation/service.py

Orchestration layer sitting between the router and (repository + engine).
Follows the same conventions established in the M-Pesa hardening work:
singleton service instantiation, bounded TTL caching for read-heavy
lookups, and a request/response shape that maps 1:1 onto what
instant-value.html already parses.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.modules.valuation.engine import ValuationEngine, ValuationInput
from app.modules.valuation.repository import ValuationRepository
from app.modules.valuation.schemas import (
    AdjustmentsBlock,
    AnalysisBlock,
    CRSPMatchBlock,
    ReportBlock,
    ValuationBlock,
    ValuationData,
    ValuationRequest,
    VehicleBlock,
)

logger = logging.getLogger("valuation.service")

# ── bounded TTL cache for CRSP lookups ──────────────────────────────────
# Keyed on (make, model, trim, year, engine_capacity_id). Small footprint,
# short TTL — CRSP data changes rarely intraday but we don't want a stale
# cache surviving a mid-day data correction either.
_CRSP_CACHE_TTL_SECONDS = 300
_CRSP_CACHE_MAX_ENTRIES = 2_000
_crsp_cache: dict[tuple, tuple[float, Optional[dict[str, Any]]]] = {}


def _cache_get(key: tuple) -> Optional[dict[str, Any]] | None:
    entry = _crsp_cache.get(key)
    if not entry:
        return None
    expires_at, value = entry
    if time.monotonic() > expires_at:
        _crsp_cache.pop(key, None)
        return None
    return value


def _cache_set(key: tuple, value: Optional[dict[str, Any]]) -> None:
    if len(_crsp_cache) >= _CRSP_CACHE_MAX_ENTRIES:
        # Cheap eviction: drop an arbitrary (oldest-ish, dict-ordered) entry
        # rather than maintaining a full LRU for a cache this small.
        _crsp_cache.pop(next(iter(_crsp_cache)), None)
    _crsp_cache[key] = (time.monotonic() + _CRSP_CACHE_TTL_SECONDS, value)


def _new_report_number() -> str:
    return f"AUTO-{datetime.now(timezone.utc).strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


class ValuationService:
    def __init__(
        self,
        repository: Optional[ValuationRepository] = None,
        engine: Optional[ValuationEngine] = None,
    ):
        self._repo = repository or ValuationRepository()
        self._engine = engine or ValuationEngine()

    # ── core flow shared by calculate / calculate-public / quick ──────

    async def _lookup_crsp(self, req: ValuationRequest) -> tuple[Optional[dict[str, Any]], str]:
        cache_key = (req.make, req.model, req.trim, req.year, req.engine_capacity_id)
        cached = _cache_get(cache_key)
        if cached is not None or cache_key in _crsp_cache:
            return cached, "engine_capacity_id" if req.engine_capacity_id else "fuzzy_match"

        row: Optional[dict[str, Any]] = None
        source = "none"

        if req.engine_capacity_id:
            row = await self._repo.get_crsp_by_engine_capacity_id(req.engine_capacity_id)
            source = "engine_capacity_id"

        if row is None:
            row = await self._repo.get_crsp_by_fuzzy_match(
                req.make, req.model, req.trim, req.year
            )
            source = "fuzzy_match" if row else source

        _cache_set(cache_key, row)
        return row, source

    async def calculate(
        self, req: ValuationRequest, *, user_id: Optional[str], persist: bool = True
    ) -> ValuationData:
        crsp_row, crsp_source = await self._lookup_crsp(req)

        crsp_base_price = None
        if crsp_row:
            crsp_base_price = crsp_row.get("crsp_kes")
        elif req.crsp_kes:
            # Untrusted client hint used only when the server-side lookup
            # missed entirely — better than falling straight to the
            # generic market anchor.
            crsp_base_price = req.crsp_kes
            crsp_source = "client_hint"

        engine_cc = self._parse_cc(req.engine_capacity)

        result = self._engine.calculate(
            ValuationInput(
                make=req.make,
                model=req.model,
                trim=req.trim,
                year=req.year,
                mileage=req.mileage,
                condition=req.condition.value,
                accident_history=req.accident_history.value,
                previous_owners=req.previous_owners,
                location=req.location,
                fuel_type=req.fuel_type.value,
                transmission=req.transmission.value,
                vehicle_type=req.vehicle_type.value,
                profit_margin_pct=req.profit_margin,
                engine_capacity_cc=engine_cc,
                crsp_base_price_kes=crsp_base_price,
            )
        )

        report_number = _new_report_number()

        data = ValuationData(
            vehicle=VehicleBlock(
                make=req.make,
                model=req.model,
                trim=req.trim,
                year=req.year,
                mileage=req.mileage,
                location=req.location,
                condition=req.condition,
                fuel_type=req.fuel_type,
                transmission=req.transmission,
                engine_capacity=req.engine_capacity,
                vehicle_type=req.vehicle_type,
            ),
            valuation=ValuationBlock(
                estimated_vehicle_value=result.estimated_vehicle_value,
                confidence_score=result.confidence_score,
                recommended_selling_price=result.recommended_selling_price,
            ),
            analysis=AnalysisBlock(
                vehicle_age=result.vehicle_age,
                depreciation_rate=result.depreciation_rate,
                depreciation_amount=result.depreciation_amount,
                mileage_adjustment=result.mileage_adjustment,
                adjustments=AdjustmentsBlock(**result.adjustments),
            ),
            report=ReportBlock(
                report_number=report_number,
                generated_at=datetime.now(timezone.utc),
            ),
            crsp=CRSPMatchBlock(
                matched=result.crsp_used,
                matched_line=(
                    f"{crsp_row.get('trim_level', req.trim)}" if crsp_row else None
                ),
                base_price_kes=crsp_base_price,
                reference_value_kes=(
                    round(crsp_base_price * 0.85, 2) if crsp_base_price else None
                ),
                variance_pct=result.crsp_variance_pct,
                source=crsp_source,
            ),
        )

        if persist:
            saved = await self._repo.save_report(
                report_number=report_number,
                user_id=user_id,
                request_payload=req.model_dump(mode="json"),
                result_payload={
                    "estimated_vehicle_value": result.estimated_vehicle_value,
                    "confidence_score": result.confidence_score,
                    "recommended_selling_price": result.recommended_selling_price,
                },
            )
            if saved and saved.get("id"):
                data.report.report_id = saved["id"]

        return data

    async def calculate_quick(self, req: ValuationRequest) -> ValuationBlock:
        """Lightweight path for /valuation/quick — no CRSP lookup, no
        persistence, pure engine estimate. Used for instant "ballpark"
        widgets where latency matters more than precision.
        """
        engine_cc = self._parse_cc(req.engine_capacity)
        result = self._engine.calculate(
            ValuationInput(
                make=req.make,
                model=req.model,
                trim=req.trim,
                year=req.year,
                mileage=req.mileage,
                condition=req.condition.value,
                accident_history=req.accident_history.value,
                previous_owners=req.previous_owners,
                location=req.location,
                fuel_type=req.fuel_type.value,
                transmission=req.transmission.value,
                vehicle_type=req.vehicle_type.value,
                profit_margin_pct=req.profit_margin,
                engine_capacity_cc=engine_cc,
                crsp_base_price_kes=req.crsp_kes,  # client hint only, no lookup
            )
        )
        return ValuationBlock(
            estimated_vehicle_value=result.estimated_vehicle_value,
            confidence_score=result.confidence_score,
            recommended_selling_price=result.recommended_selling_price,
        )

    async def calculate_bulk(
        self, items: list[ValuationRequest], *, user_id: Optional[str]
    ) -> tuple[list[ValuationData], list[dict]]:
        results: list[ValuationData] = []
        failed: list[dict] = []
        for idx, item in enumerate(items):
            try:
                results.append(await self.calculate(item, user_id=user_id, persist=True))
            except Exception as exc:  # noqa: BLE001
                logger.exception("Bulk valuation item %s failed", idx)
                failed.append({"index": idx, "error": str(exc)})
        return results, failed

    async def compare(
        self, items: list[ValuationRequest], *, user_id: Optional[str]
    ) -> tuple[list[ValuationData], Optional[int]]:
        results = [
            await self.calculate(item, user_id=user_id, persist=False) for item in items
        ]
        best_idx = None
        if results:
            best_idx = max(
                range(len(results)),
                key=lambda i: results[i].valuation.estimated_vehicle_value,
            )
        return results, best_idx

    # ── history / stats passthroughs ───────────────────────────────────

    async def get_report_by_id(self, report_id):
        return await self._repo.get_report_by_id(report_id)

    async def get_report_by_number(self, report_number: str):
        return await self._repo.get_report_by_number(report_number)

    async def get_history(self, user_id: str, page: int, page_size: int):
        return await self._repo.list_reports_for_user(user_id, page, page_size)

    async def get_stats(self):
        return await self._repo.get_stats()

    # ── helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _parse_cc(engine_capacity: Optional[str]) -> Optional[float]:
        """`engine_capacity` arrives as a display string like "1998cc" or
        "2.0L" from the trim dropdown — best-effort numeric extraction."""
        if not engine_capacity:
            return None
        digits = "".join(c for c in engine_capacity if c.isdigit() or c == ".")
        if not digits:
            return None
        try:
            value = float(digits)
        except ValueError:
            return None
        # Normalise "2.0" (litres) up to cc; anything >= 100 is assumed
        # already in cc.
        return value * 1000 if value < 100 else value


# ── singleton accessor (matches mpesa service's singleton pattern) ──────
_service_instance: Optional[ValuationService] = None


def get_valuation_service() -> ValuationService:
    global _service_instance
    if _service_instance is None:
        _service_instance = ValuationService()
    return _service_instance
