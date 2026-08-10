# app/modules/valuation/service.py

import logging
from typing import Any, Dict, Optional, List

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class ValuationService:
    """AUTO-D Kenya vehicle valuation service.

    CRSP source:
        public.vehicle_crsp_lookup

    There is intentionally no reference to public.vehicle_crsp.
    """

    CRSP_TABLE = "vehicle_crsp_lookup"

    def __init__(self):
        self.supabase = get_supabase()

    def get_crsp_vehicle(
        self,
        vehicle_crsp_id: Optional[int] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        manufacture_year: Optional[int] = None,
        engine_capacity_id: Optional[int] = None,
        crsp_id: Optional[int] = None,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Find the best matching record in vehicle_crsp_lookup."""

        try:
            resolved_id = vehicle_crsp_id or crsp_id

            if resolved_id is not None:
                response = (
                    self.supabase
                    .table(self.CRSP_TABLE)
                    .select("*")
                    .eq("crsp_id", int(resolved_id))
                    .limit(1)
                    .execute()
                )
                if response.data:
                    return response.data[0]

            if not make or not model:
                return None

            base_query = (
                self.supabase
                .table(self.CRSP_TABLE)
                .select("*")
                .ilike("make", str(make).strip())
                .ilike("model", str(model).strip())
            )

            if manufacture_year is not None:
                query = base_query.eq(
                    "manufacture_year", int(manufacture_year)
                )
                if engine_capacity_id is not None:
                    query = query.eq(
                        "engine_capacity_id", int(engine_capacity_id)
                    )
                response = query.limit(25).execute()
                if response.data:
                    return self._select_best_crsp(
                        response.data,
                        manufacture_year,
                        engine_capacity_id,
                    )

            response = base_query.limit(50).execute()
            if response.data:
                return self._select_best_crsp(
                    response.data,
                    manufacture_year,
                    engine_capacity_id,
                )

            return None

        except Exception as exc:
            logger.exception("CRSP lookup failed: %s", exc)
            return None

    def _select_best_crsp(
        self,
        records: List[Dict[str, Any]],
        manufacture_year: Optional[int] = None,
        engine_capacity_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        if not records:
            return None

        def score(row: Dict[str, Any]) -> int:
            score_value = 0

            if row.get("canonical_id") is not None:
                score_value += 20
            if row.get("is_duplicate") is False:
                score_value += 20
            if row.get("is_inferred") is False:
                score_value += 10
            if row.get("crsp_kes") is not None:
                score_value += 30
            if row.get("generation_id") is not None:
                score_value += 5
            if row.get("engine_capacity_id") is not None:
                score_value += 5
            if (
                manufacture_year is not None
                and row.get("manufacture_year") == manufacture_year
            ):
                score_value += 10
            if (
                engine_capacity_id is not None
                and row.get("engine_capacity_id") == engine_capacity_id
            ):
                score_value += 10

            return score_value

        return max(records, key=score)

    def calculate_valuation(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        manufacture_year: Optional[int] = None,
        mileage: int = 0,
        condition: str = "good",
        accident_history: str = "none",
        previous_owners: int = 0,
        location: Optional[str] = None,
        fuel_type: Optional[str] = None,
        transmission: Optional[str] = None,
        engine_capacity_id: Optional[int] = None,
        vehicle_crsp_id: Optional[int] = None,
        crsp_id: Optional[int] = None,
        vehicle_type: Optional[str] = None,
        body_type: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Calculate an indicative vehicle value."""

        crsp = self.get_crsp_vehicle(
            vehicle_crsp_id=vehicle_crsp_id,
            crsp_id=crsp_id,
            make=make,
            model=model,
            manufacture_year=manufacture_year,
            engine_capacity_id=engine_capacity_id,
        )

        resolved_id = vehicle_crsp_id or crsp_id
        crsp_value = 0.0

        if crsp:
            resolved_id = crsp.get("crsp_id")
            if crsp.get("crsp_kes") is not None:
                crsp_value = float(crsp["crsp_kes"])

        current_year = 2026
        age = max(0, current_year - int(manufacture_year)) if manufacture_year else 0

        if crsp_value <= 0:
            return {
                "success": False,
                "status": "crsp_not_found",
                "crsp_found": False,
                "crsp_id": resolved_id,
                "crsp_value": 0.0,
                "estimated_value": None,
                "estimated_value_min": None,
                "estimated_value_max": None,
                "confidence_score": 0,
                "message": "No matching CRSP record was found.",
                "vehicle": self._vehicle_summary(
                    crsp, make, model, manufacture_year,
                    fuel_type, transmission, body_type,
                ),
            }

        depreciation_rate = self._get_depreciation_rate(
            age,
            (crsp or {}).get("body_type") or body_type or vehicle_type,
        )
        mileage_factor = self._mileage_factor(mileage, age)
        condition_factor = self._condition_factor(condition)
        accident_factor = self._accident_factor(accident_history)
        owner_factor = self._owner_factor(previous_owners)
        location_factor = self._location_factor(location)

        value = (
            crsp_value
            * (1.0 - depreciation_rate)
            * mileage_factor
            * condition_factor
            * accident_factor
            * owner_factor
            * location_factor
        )

        estimated_value = round(max(value, 0.0), 2)

        return {
            "success": True,
            "status": "completed",
            "crsp_found": True,
            "crsp_id": resolved_id,
            "crsp_value": round(crsp_value, 2),
            "estimated_value": estimated_value,
            "estimated_value_min": round(estimated_value * 0.90, 2),
            "estimated_value_max": round(estimated_value * 1.10, 2),
            "confidence_score": self._confidence_score(crsp),
            "adjustments": {
                "age": age,
                "depreciation_rate": depreciation_rate,
                "mileage_factor": mileage_factor,
                "condition_factor": condition_factor,
                "accident_factor": accident_factor,
                "owner_factor": owner_factor,
                "location_factor": location_factor,
            },
            "vehicle": self._vehicle_summary(
                crsp, make, model, manufacture_year,
                fuel_type, transmission, body_type,
            ),
            "message": "Valuation completed successfully.",
        }

    def _vehicle_summary(
        self,
        crsp: Optional[Dict[str, Any]],
        make: Optional[str],
        model: Optional[str],
        manufacture_year: Optional[int],
        fuel_type: Optional[str],
        transmission: Optional[str],
        body_type: Optional[str],
    ) -> Dict[str, Any]:
        return {
            "crsp_id": crsp.get("crsp_id") if crsp else None,
            "make": crsp.get("make") if crsp and crsp.get("make") else make,
            "model": crsp.get("model") if crsp and crsp.get("model") else model,
            "master_model_id": crsp.get("master_model_id") if crsp else None,
            "master_model_name": crsp.get("master_model_name") if crsp else None,
            "generation_id": crsp.get("generation_id") if crsp else None,
            "engine_capacity_id": crsp.get("engine_capacity_id") if crsp else None,
            "engine_capacity": crsp.get("engine_capacity") if crsp else None,
            "fuel": crsp.get("fuel") if crsp and crsp.get("fuel") else fuel_type,
            "transmission": (
                crsp.get("transmission")
                if crsp and crsp.get("transmission")
                else transmission
            ),
            "body_type": (
                crsp.get("body_type")
                if crsp and crsp.get("body_type")
                else body_type
            ),
            "manufacture_year": (
                crsp.get("manufacture_year")
                if crsp and crsp.get("manufacture_year")
                else manufacture_year
            ),
            "crsp_kes": (
                float(crsp["crsp_kes"])
                if crsp and crsp.get("crsp_kes") is not None
                else None
            ),
        }

    def _confidence_score(self, crsp: Optional[Dict[str, Any]]) -> int:
        if not crsp:
            return 0

        score = 70
        score += 10
        if crsp.get("canonical_id") is not None:
            score += 5
        if crsp.get("generation_id") is not None:
            score += 3
        if crsp.get("engine_capacity_id") is not None:
            score += 3
        if crsp.get("crsp_kes") is not None:
            score += 5

        return min(score, 96)

    def _get_depreciation_rate(
        self,
        age: int,
        vehicle_type: Optional[str] = None,
    ) -> float:
        if age <= 1:
            return 0.10
        if age <= 3:
            return 0.20
        if age <= 5:
            return 0.30
        if age <= 8:
            return 0.45
        if age <= 12:
            return 0.60
        return 0.70

    def _mileage_factor(self, mileage: Optional[int], age: int) -> float:
        try:
            km = max(0, int(mileage or 0))
        except (TypeError, ValueError):
            km = 0

        if km <= 0:
            return 1.00

        expected = max(15000 * max(age, 1), 1000)
        ratio = km / expected

        if ratio <= 0.75:
            return 1.03
        if ratio <= 1.25:
            return 1.00
        if ratio <= 1.75:
            return 0.95
        if ratio <= 2.50:
            return 0.88
        return 0.80

    def _condition_factor(self, condition: Optional[str]) -> float:
        return {
            "excellent": 1.10,
            "very good": 1.05,
            "very_good": 1.05,
            "good": 1.00,
            "fair": 0.90,
            "poor": 0.75,
        }.get(str(condition or "good").strip().lower(), 1.00)

    def _accident_factor(self, accident_history: Optional[str]) -> float:
        return {
            "none": 1.00,
            "no": 1.00,
            "minor": 0.92,
            "major": 0.75,
            "total loss": 0.35,
            "total_loss": 0.35,
        }.get(str(accident_history or "none").strip().lower(), 1.00)

    def _owner_factor(self, previous_owners: Optional[int]) -> float:
        try:
            owners = max(0, int(previous_owners or 0))
        except (TypeError, ValueError):
            owners = 0

        if owners >= 5:
            return 0.95
        if owners >= 3:
            return 0.97
        return 1.00

    def _location_factor(self, location: Optional[str]) -> float:
        return 1.00


def get_valuation_service() -> ValuationService:
    return ValuationService()
