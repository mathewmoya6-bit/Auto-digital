# app/modules/valuation/service.py
# ================================================================
# AUTO-D Kenya - Valuation Service
# ================================================================
#
# SINGLE SOURCE OF TRUTH:
#     public.vehicle_crsp_lookup
#
# IMPORTANT:
# - No vehicle_variants
# - No variant_id
# - No vehicle_master_specs
# - No vehicle_crsp_import
# - No await
# - CRSP lookup is handled by ValuationRepository
# ================================================================

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.modules.valuation.repository import ValuationRepository


logger = logging.getLogger(__name__)


class ValuationService:
    """
    AUTO-D Kenya vehicle valuation service.

    Architecture:

        Router
          ↓
        ValuationService
          ↓
        ValuationRepository
          ↓
        public.vehicle_crsp_lookup

    The service contains valuation business logic only.
    """

    CRSP_TABLE = "vehicle_crsp_lookup"
    CURRENT_YEAR = 2026

    def __init__(self):
        self.repository = ValuationRepository()

        # Backward compatibility for existing code.
        self.supabase = self.repository.supabase

        logger.info("ValuationService initialized")

    # ============================================================
    # CRSP LOOKUP
    # ============================================================

    def get_crsp_vehicle(
        self,
        vehicle_crsp_id: Optional[int] = None,
        crsp_id: Optional[int] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        manufacture_year: Optional[int] = None,
        engine_capacity_id: Optional[int] = None,
        fuel_type: Optional[str] = None,
        transmission: Optional[str] = None,
        body_type: Optional[str] = None,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve a CRSP vehicle.

        Priority:

        1. Direct CRSP ID
        2. Exact make/model/year/filter search
        3. Make/model without year
        4. Broad make/model search

        There is deliberately no variant lookup.
        """

        try:
            resolved_id = vehicle_crsp_id or crsp_id

            # ----------------------------------------------------
            # 1. DIRECT CRSP ID
            # ----------------------------------------------------

            if resolved_id is not None:
                try:
                    resolved_id = int(resolved_id)
                except (TypeError, ValueError):
                    resolved_id = None

            if resolved_id is not None:
                record = self.repository.get_crsp_by_id(resolved_id)

                if record:
                    logger.info(
                        "CRSP found directly: crsp_id=%s",
                        resolved_id,
                    )
                    return record

                logger.warning(
                    "CRSP ID %s was not found",
                    resolved_id,
                )

            # ----------------------------------------------------
            # 2. MAKE + MODEL REQUIRED FOR SEARCH
            # ----------------------------------------------------

            make = self._clean_text(make)
            model = self._clean_text(model)

            if not make or not model:
                logger.warning(
                    "CRSP search skipped: make/model not provided"
                )
                return None

            # ----------------------------------------------------
            # 3. EXACT SEARCH
            # ----------------------------------------------------

            logger.info(
                "CRSP search: make=%s model=%s year=%s",
                make,
                model,
                manufacture_year,
            )

            records = self.repository.search_crsp(
                make=make,
                model=model,
                manufacture_year=manufacture_year,
                engine_capacity_id=engine_capacity_id,
                fuel=fuel_type,
                transmission=transmission,
                body_type=body_type,
                limit=100,
            )

            selected = self._select_best_crsp(
                records,
                manufacture_year=manufacture_year,
                engine_capacity_id=engine_capacity_id,
            )

            if selected:
                logger.info(
                    "CRSP selected: crsp_id=%s",
                    selected.get("crsp_id"),
                )
                return selected

            # ----------------------------------------------------
            # 4. SEARCH WITHOUT YEAR
            # ----------------------------------------------------

            if manufacture_year is not None:
                logger.info(
                    "Retrying CRSP search without year: %s %s",
                    make,
                    model,
                )

                records = self.repository.search_crsp(
                    make=make,
                    model=model,
                    manufacture_year=None,
                    engine_capacity_id=engine_capacity_id,
                    fuel=fuel_type,
                    transmission=transmission,
                    body_type=body_type,
                    limit=100,
                )

                selected = self._select_best_crsp(
                    records,
                    manufacture_year=manufacture_year,
                    engine_capacity_id=engine_capacity_id,
                )

                if selected:
                    logger.info(
                        "CRSP selected without year: crsp_id=%s",
                        selected.get("crsp_id"),
                    )
                    return selected

            # ----------------------------------------------------
            # 5. BROAD MAKE + MODEL
            # ----------------------------------------------------

            logger.info(
                "Broad CRSP search: %s %s",
                make,
                model,
            )

            records = self.repository.search_crsp(
                make=make,
                model=model,
                manufacture_year=None,
                engine_capacity_id=None,
                fuel=None,
                transmission=None,
                body_type=None,
                limit=100,
            )

            selected = self._select_best_crsp(
                records,
                manufacture_year=manufacture_year,
                engine_capacity_id=engine_capacity_id,
            )

            if selected:
                logger.info(
                    "CRSP selected from broad search: crsp_id=%s",
                    selected.get("crsp_id"),
                )
                return selected

            logger.warning(
                "No CRSP record found for %s %s",
                make,
                model,
            )

            return None

        except Exception as exc:
            logger.exception(
                "CRSP lookup failed: %s",
                exc,
            )
            return None

    # ============================================================
    # PUBLIC CRSP SEARCH
    # ============================================================

    def search_crsp(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Public CRSP search used by API endpoints.
        """

        return self.repository.search_crsp(
            make=kwargs.get("make"),
            model=kwargs.get("model"),
            manufacture_year=kwargs.get(
                "manufacture_year"
            ),
            engine_capacity_id=kwargs.get(
                "engine_capacity_id"
            ),
            fuel=kwargs.get("fuel_type") or kwargs.get("fuel"),
            transmission=kwargs.get("transmission"),
            body_type=kwargs.get("body_type"),
            limit=kwargs.get("limit", 25),
        )

    # ============================================================
    # SELECT BEST CRSP
    # ============================================================

    def _select_best_crsp(
        self,
        records: Optional[List[Dict[str, Any]]],
        manufacture_year: Optional[int] = None,
        engine_capacity_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Select the strongest CRSP record from search results.
        """

        if not records:
            return None

        def score(row: Dict[str, Any]) -> int:
            score_value = 0

            # Valid CRSP price
            crsp_value = self._number(row.get("crsp_kes"))

            if crsp_value > 0:
                score_value += 40

            # Exact year
            row_year = row.get("manufacture_year")

            if (
                manufacture_year is not None
                and row_year is not None
            ):
                try:
                    difference = abs(
                        int(row_year)
                        - int(manufacture_year)
                    )

                    if difference == 0:
                        score_value += 30
                    elif difference == 1:
                        score_value += 20
                    elif difference == 2:
                        score_value += 10

                except (TypeError, ValueError):
                    pass

            # Engine capacity
            if (
                engine_capacity_id is not None
                and row.get("engine_capacity_id")
                == engine_capacity_id
            ):
                score_value += 15

            # Complete record
            if row.get("make"):
                score_value += 5

            if row.get("model"):
                score_value += 5

            if row.get("fuel"):
                score_value += 2

            if row.get("transmission"):
                score_value += 2

            if row.get("body_type"):
                score_value += 2

            # Prefer canonical records
            if row.get("canonical_id") is not None:
                score_value += 5

            if row.get("is_duplicate") is False:
                score_value += 5

            if row.get("is_inferred") is False:
                score_value += 3

            return score_value

        ranked = sorted(
            records,
            key=score,
            reverse=True,
        )

        best = ranked[0]

        logger.debug(
            "Best CRSP candidate: id=%s score=%s",
            best.get("crsp_id"),
            score(best),
        )

        return best

    # ============================================================
    # MAIN VALUATION
    # ============================================================

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
        """
        Calculate vehicle valuation.

        CRSP is the authoritative base value.
        """

        make = self._clean_text(make)
        model = self._clean_text(model)

        # --------------------------------------------------------
        # VALIDATE YEAR
        # --------------------------------------------------------

        if manufacture_year is not None:
            try:
                manufacture_year = int(manufacture_year)
            except (TypeError, ValueError):
                manufacture_year = None

        # --------------------------------------------------------
        # NORMALIZE MILEAGE
        # --------------------------------------------------------

        try:
            mileage = max(0, int(mileage or 0))
        except (TypeError, ValueError):
            mileage = 0

        # --------------------------------------------------------
        # CRSP LOOKUP
        # --------------------------------------------------------

        crsp = self.get_crsp_vehicle(
            vehicle_crsp_id=vehicle_crsp_id,
            crsp_id=crsp_id,
            make=make,
            model=model,
            manufacture_year=manufacture_year,
            engine_capacity_id=engine_capacity_id,
            fuel_type=fuel_type,
            transmission=transmission,
            body_type=body_type,
        )

        resolved_crsp_id = (
            crsp.get("crsp_id")
            if crsp
            else vehicle_crsp_id or crsp_id
        )

        crsp_value = (
            self._number(crsp.get("crsp_kes"))
            if crsp
            else 0.0
        )

        # --------------------------------------------------------
        # AGE
        # --------------------------------------------------------

        age = 0

        if manufacture_year:
            age = max(
                0,
                self.CURRENT_YEAR - manufacture_year,
            )

        # --------------------------------------------------------
        # VEHICLE SUMMARY
        # --------------------------------------------------------

        vehicle = self._vehicle_summary(
            crsp=crsp,
            make=make,
            model=model,
            manufacture_year=manufacture_year,
            fuel_type=fuel_type,
            transmission=transmission,
            body_type=body_type,
        )

        # --------------------------------------------------------
        # FACTORS
        # --------------------------------------------------------

        depreciation_rate = self._get_depreciation_rate(
            age,
            vehicle_type or body_type,
        )

        mileage_factor = self._mileage_factor(
            mileage,
            age,
        )

        condition_factor = self._condition_factor(
            condition
        )

        accident_factor = self._accident_factor(
            accident_history
        )

        owner_factor = self._owner_factor(
            previous_owners
        )

        location_factor = self._location_factor(
            location
        )

        # --------------------------------------------------------
        # CRSP FOUND
        # --------------------------------------------------------

        if crsp_value > 0:

            final_value = (
                crsp_value
                * (1.0 - depreciation_rate)
                * mileage_factor
                * condition_factor
                * accident_factor
                * owner_factor
                * location_factor
            )

            final_value = round(
                max(final_value, 0),
                2,
            )

            return self._build_success_response(
                vehicle=vehicle,
                crsp=crsp,
                crsp_value=crsp_value,
                final_value=final_value,
                resolved_crsp_id=resolved_crsp_id,
                age=age,
                depreciation_rate=depreciation_rate,
                mileage_factor=mileage_factor,
                condition_factor=condition_factor,
                accident_factor=accident_factor,
                owner_factor=owner_factor,
                location_factor=location_factor,
            )

        # --------------------------------------------------------
        # NO CRSP
        # --------------------------------------------------------

        logger.warning(
            "No CRSP value found for %s %s %s",
            make,
            model,
            manufacture_year,
        )

        estimated_base = (
            self._estimate_value_from_make_model(
                make=make,
                model=model,
                manufacture_year=manufacture_year,
                mileage=mileage,
                condition=condition,
            )
        )

        if estimated_base > 0:

            final_value = (
                estimated_base
                * (1.0 - depreciation_rate)
                * mileage_factor
                * accident_factor
                * owner_factor
                * location_factor
            )

            final_value = round(
                max(final_value, 0),
                2,
            )

            response = self._build_success_response(
                vehicle=vehicle,
                crsp=None,
                crsp_value=0,
                final_value=final_value,
                resolved_crsp_id=resolved_crsp_id,
                age=age,
                depreciation_rate=depreciation_rate,
                mileage_factor=mileage_factor,
                condition_factor=condition_factor,
                accident_factor=accident_factor,
                owner_factor=owner_factor,
                location_factor=location_factor,
            )

            response["crsp_found"] = False
            response["confidence_score"] = 35
            response["message"] = (
                "Valuation estimated from make/model "
                "baseline because no CRSP record was found."
            )
            response["warnings"] = [
                "No CRSP record found - using estimate"
            ]

            return response

        # --------------------------------------------------------
        # NOTHING AVAILABLE
        # --------------------------------------------------------

        return {
            "success": False,
            "status": "crsp_not_found",
            "crsp_found": False,
            "crsp_id": resolved_crsp_id,
            "crsp_value": 0.0,
            "estimated_value": None,
            "estimated_value_min": None,
            "estimated_value_max": None,
            "confidence_score": 0,
            "adjustments": {},
            "vehicle": vehicle,
            "message": (
                f"No valuation data available for "
                f"{make or ''} {model or ''} "
                f"{manufacture_year or ''}".strip()
            ),
            "market_value": None,
            "retail_value": None,
            "trade_value": None,
            "dealer_value": None,
            "recommended_selling_price": None,
            "currency": "KES",
            "calculated_at": datetime.utcnow().isoformat(),
            "warnings": [
                "No CRSP record found"
            ],
            "comparables": [],
            "sample_size": 0,
            "recommendation": (
                "Please check the vehicle CRSP ID "
                "or vehicle details."
            ),
            "depreciation": None,
        }

    # ============================================================
    # RESPONSE BUILDER
    # ============================================================

    def _build_success_response(
        self,
        vehicle: Dict[str, Any],
        crsp: Optional[Dict[str, Any]],
        crsp_value: float,
        final_value: float,
        resolved_crsp_id: Optional[int],
        age: int,
        depreciation_rate: float,
        mileage_factor: float,
        condition_factor: float,
        accident_factor: float,
        owner_factor: float,
        location_factor: float,
    ) -> Dict[str, Any]:

        retail_value = round(
            final_value * 1.08,
            2,
        )

        trade_value = round(
            final_value * 0.85,
            2,
        )

        dealer_value = round(
            final_value * 0.95,
            2,
        )

        recommended_price = round(
            final_value * 1.10,
            2,
        )

        return {
            "success": True,
            "status": "completed",

            "crsp_found": crsp_value > 0,

            "crsp_id": resolved_crsp_id,
            "crsp_value": round(
                crsp_value,
                2,
            ),

            "estimated_value": final_value,

            "estimated_value_min": round(
                final_value * 0.90,
                2,
            ),

            "estimated_value_max": round(
                final_value * 1.10,
                2,
            ),

            "confidence_score": self._confidence_score(
                crsp
            ),

            "adjustments": {
                "age": age,
                "depreciation_rate": depreciation_rate,
                "mileage_factor": mileage_factor,
                "condition_factor": condition_factor,
                "accident_factor": accident_factor,
                "owner_factor": owner_factor,
                "location_factor": location_factor,
            },

            "vehicle": vehicle,

            "message": (
                "Valuation completed successfully."
            ),

            "market_value": final_value,
            "retail_value": retail_value,
            "trade_value": trade_value,
            "dealer_value": dealer_value,
            "recommended_selling_price": recommended_price,

            "currency": "KES",

            "calculated_at": datetime.utcnow().isoformat(),

            "warnings": [],

            "comparables": [],

            "sample_size": 1 if crsp else 0,

            "recommendation": (
                "Market value is within the "
                "expected range."
            ),

            "depreciation": {
                "rate": depreciation_rate,
                "age_years": age,
                "remaining_value_percent": round(
                    (1.0 - depreciation_rate) * 100,
                    1,
                ),
            },
        }

    # ============================================================
    # VEHICLE SUMMARY
    # ============================================================

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
            "crsp_id": (
                crsp.get("crsp_id")
                if crsp
                else None
            ),

            "make": (
                crsp.get("make")
                if crsp and crsp.get("make")
                else make
            ),

            "model": (
                crsp.get("model")
                if crsp and crsp.get("model")
                else model
            ),

            "master_model_id": (
                crsp.get("master_model_id")
                if crsp
                else None
            ),

            "master_model_name": (
                crsp.get("master_model_name")
                if crsp
                else None
            ),

            "generation_id": (
                crsp.get("generation_id")
                if crsp
                else None
            ),

            "engine_capacity_id": (
                crsp.get("engine_capacity_id")
                if crsp
                else None
            ),

            "engine_capacity": (
                crsp.get("engine_capacity")
                if crsp
                else None
            ),

            "fuel": (
                crsp.get("fuel")
                if crsp and crsp.get("fuel")
                else fuel_type
            ),

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
                self._number(crsp.get("crsp_kes"))
                if crsp
                else None
            ),
        }

    # ============================================================
    # CONFIDENCE
    # ============================================================

    def _confidence_score(
        self,
        crsp: Optional[Dict[str, Any]],
    ) -> int:

        if not crsp:
            return 35

        score = 70

        if crsp.get("crsp_kes"):
            score += 5

        if crsp.get("make"):
            score += 3

        if crsp.get("model"):
            score += 3

        if crsp.get("manufacture_year"):
            score += 3

        if crsp.get("engine_capacity_id"):
            score += 3

        if crsp.get("generation_id"):
            score += 3

        if crsp.get("canonical_id"):
            score += 3

        return min(score, 96)

    # ============================================================
    # ESTIMATION FALLBACK
    # ============================================================

    def _estimate_value_from_make_model(
        self,
        make: str,
        model: str,
        manufacture_year: Optional[int],
        mileage: int,
        condition: str,
    ) -> float:

        make_lower = (make or "").lower()
        model_lower = (model or "").lower()

        base_values = {
            "toyota": 3_500_000,
            "honda": 2_800_000,
            "nissan": 2_500_000,
            "mazda": 2_400_000,
            "subaru": 3_000_000,
            "mercedes": 5_000_000,
            "bmw": 4_500_000,
            "audi": 4_200_000,
            "volkswagen": 3_000_000,
            "vw": 3_000_000,
            "ford": 3_200_000,
            "hyundai": 2_500_000,
            "kia": 2_400_000,
            "suzuki": 2_000_000,
            "mitsubishi": 2_600_000,
            "isuzu": 3_500_000,
            "land rover": 6_000_000,
            "jaguar": 5_500_000,
            "porsche": 8_000_000,
        }

        model_adjustments = {
            "land cruiser": 1.80,
            "prado": 1.50,
            "hilux": 1.30,
            "fortuner": 1.40,
            "rav4": 1.20,
            "harrier": 1.30,
            "venza": 1.20,
            "corolla": 0.80,
            "camry": 1.00,
            "premio": 0.85,
            "axio": 0.80,
            "civic": 0.90,
            "accord": 1.00,
            "cr-v": 1.20,
            "x-trail": 1.10,
            "patrol": 1.80,
            "cx-5": 1.10,
            "forester": 1.10,
            "outback": 1.00,
            "impreza": 0.90,
            "golf": 0.90,
            "passat": 1.00,
            "tiguan": 1.10,
            "c-class": 1.10,
            "e-class": 1.30,
            "s-class": 1.80,
            "x5": 1.50,
            "ranger": 1.20,
        }

        base_value = 0

        for key, value in base_values.items():
            if key in make_lower:
                base_value = value
                break

        if base_value == 0:
            base_value = 2_500_000

        model_factor = 1.0

        for key, factor in model_adjustments.items():
            if key in model_lower:
                model_factor = factor
                break

        # Year factor
        if manufacture_year:
            age = max(
                0,
                self.CURRENT_YEAR - manufacture_year,
            )

            if age <= 1:
                year_factor = 0.95
            elif age <= 3:
                year_factor = 0.80
            elif age <= 5:
                year_factor = 0.65
            elif age <= 8:
                year_factor = 0.50
            elif age <= 12:
                year_factor = 0.35
            else:
                year_factor = 0.20
        else:
            year_factor = 0.70

        if mileage <= 0:
            mileage_factor = 1.0
        elif mileage < 50_000:
            mileage_factor = 1.0
        elif mileage < 100_000:
            mileage_factor = 0.90
        elif mileage < 150_000:
            mileage_factor = 0.80
        elif mileage < 200_000:
            mileage_factor = 0.70
        else:
            mileage_factor = 0.60

        condition_factor = self._condition_factor(
            condition
        )

        estimated = (
            base_value
            * model_factor
            * year_factor
            * mileage_factor
            * condition_factor
        )

        return round(
            max(estimated, 50_000),
            2,
        )

    # ============================================================
    # ADJUSTMENT FACTORS
    # ============================================================

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

    def _mileage_factor(
        self,
        mileage: Optional[int],
        age: int,
    ) -> float:

        try:
            km = max(
                0,
                int(mileage or 0),
            )
        except (TypeError, ValueError):
            km = 0

        if km <= 0:
            return 1.00

        expected = max(
            15_000 * max(age, 1),
            1_000,
        )

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

    def _condition_factor(
        self,
        condition: Optional[str],
    ) -> float:

        value = str(
            condition or "good"
        ).strip().lower()

        return {
            "excellent": 1.10,
            "very good": 1.05,
            "very_good": 1.05,
            "good": 1.00,
            "fair": 0.90,
            "poor": 0.75,
        }.get(value, 1.00)

    def _accident_factor(
        self,
        accident_history: Optional[str],
    ) -> float:

        value = str(
            accident_history or "none"
        ).strip().lower()

        return {
            "none": 1.00,
            "no": 1.00,
            "minor": 0.92,
            "major": 0.75,
            "total loss": 0.35,
            "total_loss": 0.35,
        }.get(value, 1.00)

    def _owner_factor(
        self,
        previous_owners: Optional[int],
    ) -> float:

        try:
            owners = max(
                0,
                int(previous_owners or 0),
            )
        except (TypeError, ValueError):
            owners = 0

        if owners >= 5:
            return 0.95

        if owners >= 3:
            return 0.97

        return 1.00

    def _location_factor(
        self,
        location: Optional[str],
    ) -> float:
        """
        Location adjustment placeholder.

        Keep at 1.00 until county/location pricing
        is explicitly implemented.
        """

        return 1.00

    # ============================================================
    # UTILITY METHODS
    # ============================================================

    @staticmethod
    def _clean_text(value: Optional[Any]) -> Optional[str]:

        if value is None:
            return None

        value = str(value).strip()

        return value if value else None

    @staticmethod
    def _number(value: Any) -> float:

        try:
            if value is None:
                return 0.0

            return float(value)

        except (TypeError, ValueError):
            return 0.0

    # ============================================================
    # OPTIONAL HISTORY METHODS
    # ============================================================

    def get_valuation_history(
        self,
        user_id: Optional[str],
    ) -> List[Dict[str, Any]]:

        if not user_id:
            return []

        try:
            if hasattr(
                self.repository,
                "get_valuation_history",
            ):
                return self.repository.get_valuation_history(
                    user_id
                )

        except Exception as exc:
            logger.exception(
                "Failed to get valuation history: %s",
                exc,
            )

        return []

    def get_valuation_by_id(
        self,
        report_id: int,
        user_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:

        try:
            if hasattr(
                self.repository,
                "get_valuation_by_id",
            ):
                return self.repository.get_valuation_by_id(
                    report_id,
                    user_id,
                )

        except Exception as exc:
            logger.exception(
                "Failed to get valuation report: %s",
                exc,
            )

        return None

    def get_valuation_by_report_number(
        self,
        report_number: str,
        user_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:

        try:
            if hasattr(
                self.repository,
                "get_valuation_by_report_number",
            ):
                return (
                    self.repository
                    .get_valuation_by_report_number(
                        report_number,
                        user_id,
                    )
                )

        except Exception as exc:
            logger.exception(
                "Failed to get valuation report: %s",
                exc,
            )

        return None

    def get_valuation_stats(
        self,
        user_id: Optional[str],
    ) -> Dict[str, Any]:

        try:
            if hasattr(
                self.repository,
                "get_valuation_stats",
            ):
                return self.repository.get_valuation_stats(
                    user_id
                )

        except Exception as exc:
            logger.exception(
                "Failed to get valuation stats: %s",
                exc,
            )

        return {
            "total_valuations": 0,
            "average_value": 0,
            "highest_value": 0,
            "lowest_value": 0,
        }

    # ============================================================
    # HEALTH
    # ============================================================

    def health_check(self) -> Dict[str, Any]:

        database = "healthy"

        try:
            if hasattr(
                self.repository,
                "health_check",
            ):
                result = self.repository.health_check()

                if isinstance(result, dict):
                    return result

        except Exception as exc:
            database = "unhealthy"

            return {
                "status": "degraded",
                "service": "valuation",
                "version": "3.0",
                "timestamp": datetime.utcnow().isoformat(),
                "database": database,
                "error": str(exc),
            }

        return {
            "status": "healthy",
            "service": "valuation",
            "version": "3.0",
            "timestamp": datetime.utcnow().isoformat(),
            "database": database,
        }


# ================================================================
# SERVICE FACTORY
# ================================================================

def get_valuation_service() -> ValuationService:
    return ValuationService()
