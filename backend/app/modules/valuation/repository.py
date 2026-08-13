"""
app/modules/valuation/repository.py

Data access layer. All writes and CRSP reads go through the Supabase
service-role client (never the anon/browser client used in the frontend),
consistent with the rest of the backend.

ASSUMPTIONS FLAGGED BELOW -- confirm/adjust against the live schema:

1. `vehicle_crsp_prices` -- the FK-normalized CRSP pricing table referenced
   in the Aug alignment work. Assumed columns:
     id, engine_capacity_id (FK), make, model, trim_level, crsp_kes,
     body_type, fuel, transmission, crsp_year
   Lookup pattern follows total-cost-ownership.html / mileage-running-
   cost.html: `.eq('engine_capacity_id', variant_id)` first, with an
   `.in_()` fallback across sibling variant_ids when a dropdown option
   represents multiple grouped trims.

2. `crsp_makes` / `crsp_models` / `crsp_price_list` -- the normalized KRA
   CRSP pipeline tables from the DB audit. Used here only as a secondary
   fuzzy-match path when `engine_capacity_id` isn't supplied by the
   caller (current instant-value.html v6.0 doesn't send it yet).

3. `vehicle_master_specs` -- confirmed view, PK `variant_id`, has
   `engine_size_cc`, `make_id`, `model_id`, `generation_id`,
   `fuel_consumption_combined`. Used to resolve a display engine size
   when only a text `engine_capacity` string comes in.

4. `valuation_reports` -- assumed table for persisted reports (not yet
   confirmed to exist). Columns assumed:
     id (uuid pk), report_number (text unique), user_id (uuid, nullable
     for public/quick valuations), make, model, trim, year, mileage,
     location, condition, estimated_vehicle_value, confidence_score,
     recommended_selling_price, payload (jsonb), created_at.
   If this table doesn't exist yet, `save_report()` degrades gracefully
   (logs + returns an in-memory-only report) rather than raising, so
   valuation keeps working while the migration is pending.

Swap in real column/table names as soon as you confirm the CRSP audit
results -- the public method signatures below are what `service.py`
depends on, so internals can change freely.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from app.core.supabase import get_service_client  # existing service-role client factory

logger = logging.getLogger("valuation.repository")

CRSP_VIEW = "vehicle_crsp_prices"
CRSP_MAKES_TABLE = "crsp_makes"
CRSP_MODELS_TABLE = "crsp_models"
CRSP_PRICE_LIST_TABLE = "crsp_price_list"
MASTER_SPECS_VIEW = "vehicle_master_specs"
REPORTS_TABLE = "valuation_reports"


class ValuationRepository:
    """Thin, testable wrapper around Supabase calls used by the valuation
    domain. Instantiated once (see service.py singleton) and reused across
    requests -- supabase-py's client is safe to share.
    """

    def __init__(self, client=None):
        self._client = client or get_service_client()

    # -- CRSP LOOKUP ----------------------------------------------------

    async def get_crsp_by_engine_capacity_id(
        self,
        engine_capacity_id: int,
        sibling_ids: Optional[list[int]] = None,
    ) -> Optional[dict[str, Any]]:
        """Primary CRSP lookup path -- mirrors the pattern already proven
        out in total-cost-ownership.html / mileage-running-cost.html.

        `sibling_ids` covers the case where a cc-grouped dropdown option
        represents several underlying variant_ids; if the primary id
        misses, we widen to `.in_()` across the group before giving up.
        """
        try:
            resp = (
                self._client.table(CRSP_VIEW)
                .select("*")
                .eq("engine_capacity_id", engine_capacity_id)
                .limit(1)
                .execute()
            )
            if resp.data:
                return resp.data[0]

            if sibling_ids:
                resp = (
                    self._client.table(CRSP_VIEW)
                    .select("*")
                    .in_("engine_capacity_id", sibling_ids)
                    .limit(1)
                    .execute()
                )
                if resp.data:
                    return resp.data[0]

            return None
        except Exception as exc:  # noqa: BLE001 -- degrade, don't 500 the valuation
            logger.warning("CRSP lookup by engine_capacity_id failed: %s", exc)
            return None

    async def get_crsp_by_fuzzy_match(
        self,
        make: str,
        model: str,
        trim: Optional[str],
        year: int,
    ) -> Optional[dict[str, Any]]:
        """Fallback path used when the caller hasn't supplied
        engine_capacity_id (current frontend build). Filters make/model/
        year server-side, then does a light in-process trim match --
        the heavier rapidfuzz scoring lives in baseprice_engine.py and
        can be swapped in here once this module needs the same accuracy.
        """
        try:
            resp = (
                self._client.table(CRSP_VIEW)
                .select("*")
                .ilike("make", make)
                .ilike("model", model)
                .eq("crsp_year", year)
                .execute()
            )
            rows = resp.data or []
            if not rows:
                return None
            if not trim:
                return rows[0]

            trim_norm = trim.strip().lower()
            for row in rows:
                if str(row.get("trim_level", "")).strip().lower() == trim_norm:
                    return row
            # No exact trim match -- best-effort: shortest Levenshtein-free
            # substring match, else just the first row for the year.
            for row in rows:
                row_trim = str(row.get("trim_level", "")).strip().lower()
                if row_trim and (row_trim in trim_norm or trim_norm in row_trim):
                    return row
            return rows[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("CRSP fuzzy match failed: %s", exc)
            return None

    async def get_vehicle_master_spec(self, variant_id: int) -> Optional[dict[str, Any]]:
        try:
            resp = (
                self._client.table(MASTER_SPECS_VIEW)
                .select("*")
                .eq("variant_id", variant_id)
                .limit(1)
                .execute()
            )
            return resp.data[0] if resp.data else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("vehicle_master_specs lookup failed: %s", exc)
            return None

    # -- REPORT PERSISTENCE ---------------------------------------------

    async def save_report(
        self,
        *,
        report_number: str,
        user_id: Optional[str],
        request_payload: dict[str, Any],
        result_payload: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        row = {
            "report_number": report_number,
            "user_id": user_id,
            "make": request_payload.get("make"),
            "model": request_payload.get("model"),
            "trim": request_payload.get("trim"),
            "year": request_payload.get("year"),
            "mileage": request_payload.get("mileage"),
            "location": request_payload.get("location"),
            "condition": request_payload.get("condition"),
            "estimated_vehicle_value": result_payload.get("estimated_vehicle_value"),
            "confidence_score": result_payload.get("confidence_score"),
            "recommended_selling_price": result_payload.get("recommended_selling_price"),
            "payload": {"request": request_payload, "result": result_payload},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            resp = self._client.table(REPORTS_TABLE).insert(row).execute()
            return resp.data[0] if resp.data else row
        except Exception as exc:  # noqa: BLE001
            # Table may not exist yet -- don't break the valuation flow
            # over persistence. Caller still returns a valid report_number.
            logger.error(
                "Failed to persist valuation report %s (table missing or "
                "schema mismatch?): %s",
                report_number,
                exc,
            )
            return None

    async def get_report_by_id(self, report_id: UUID) -> Optional[dict[str, Any]]:
        try:
            resp = (
                self._client.table(REPORTS_TABLE)
                .select("*")
                .eq("id", str(report_id))
                .limit(1)
                .execute()
            )
            return resp.data[0] if resp.data else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_report_by_id failed: %s", exc)
            return None

    async def get_report_by_number(self, report_number: str) -> Optional[dict[str, Any]]:
        try:
            resp = (
                self._client.table(REPORTS_TABLE)
                .select("*")
                .eq("report_number", report_number)
                .limit(1)
                .execute()
            )
            return resp.data[0] if resp.data else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_report_by_number failed: %s", exc)
            return None

    async def list_reports_for_user(
        self, user_id: str, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict[str, Any]], int]:
        start = (page - 1) * page_size
        end = start + page_size - 1
        try:
            resp = (
                self._client.table(REPORTS_TABLE)
                .select("*", count="exact")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .range(start, end)
                .execute()
            )
            return resp.data or [], resp.count or 0
        except Exception as exc:  # noqa: BLE001
            logger.warning("list_reports_for_user failed: %s", exc)
            return [], 0

    async def get_stats(self) -> dict[str, Any]:
        try:
            resp = self._client.table(REPORTS_TABLE).select(
                "estimated_vehicle_value, confidence_score, make"
            ).execute()
            rows = resp.data or []
            if not rows:
                return {
                    "total_valuations": 0,
                    "avg_confidence_score": 0.0,
                    "avg_estimated_value": 0.0,
                    "top_makes": [],
                }
            total = len(rows)
            avg_conf = sum(r.get("confidence_score") or 0 for r in rows) / total
            avg_val = sum(r.get("estimated_vehicle_value") or 0 for r in rows) / total
            make_counts: dict[str, int] = {}
            for r in rows:
                m = r.get("make") or "Unknown"
                make_counts[m] = make_counts.get(m, 0) + 1
            top_makes = sorted(
                ({"make": k, "count": v} for k, v in make_counts.items()),
                key=lambda x: x["count"],
                reverse=True,
            )[:10]
            return {
                "total_valuations": total,
                "avg_confidence_score": round(avg_conf, 1),
                "avg_estimated_value": round(avg_val, 2),
                "top_makes": top_makes,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_stats failed: %s", exc)
            return {
                "total_valuations": 0,
                "avg_confidence_score": 0.0,
                "avg_estimated_value": 0.0,
                "top_makes": [],
            }
