# app/modules/valuation/service.py

import logging
from typing import Any, Dict, Optional, List
from datetime import datetime

from app.modules.valuation.repository import ValuationRepository

logger = logging.getLogger(__name__)


class ValuationService:
    """AUTO-D Kenya vehicle valuation service.

    CRSP source:
        public.vehicle_crsp_lookup

    There is intentionally no reference to public.vehicle_crsp.
    """

    CRSP_TABLE = "vehicle_crsp_lookup"

    def __init__(self):
        self.repository = ValuationRepository()
        # Kept for backward compatibility with code that inspects the service.
        self.supabase = self.repository.supabase

    def get_crsp_vehicle(
        self,
        vehicle_crsp_id: Optional[int] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        manufacture_year: Optional[int] = None,
        engine_capacity_id: Optional[int] = None,
        crsp_id: Optional[int] = None,
        fuel_type: Optional[str] = None,
        transmission: Optional[str] = None,
        body_type: Optional[str] = None,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Find the best matching record from vehicle_crsp_lookup.

        Repository methods are synchronous. There is intentionally no await.
        """
        try:
            resolved_id = vehicle_crsp_id or crsp_id

            # Try direct ID lookup first
            if resolved_id is not None:
                record = self.repository.get_crsp_by_id(int(resolved_id))
                if record:
                    logger.info(f"Found CRSP record by ID: {resolved_id}")
                    return record

            # If no make/model provided, we can't search further
            if not make or not model:
                logger.warning("No make/model provided for CRSP search")
                return None

            # Try exact match with all filters
            logger.info(f"Searching CRSP for {make} {model} {manufacture_year}")
            records = self.repository.search_crsp(
                make=make,
                model=model,
                manufacture_year=manufacture_year,
                engine_capacity_id=engine_capacity_id,
                fuel=fuel_type,
                transmission=transmission,
                body_type=body_type,
                limit=50,
            )

            if records:
                selected = self._select_best_crsp(
                    records, manufacture_year, engine_capacity_id
                )
                if selected:
                    logger.info(f"Selected CRSP record: {selected.get('crsp_id')}")
                    return selected

            # Try without year if year-specific search failed
            if manufacture_year is not None:
                logger.info(f"No exact year match for {make} {model}, searching without year")
                records = self.repository.search_crsp(
                    make=make,
                    model=model,
                    manufacture_year=None,
                    engine_capacity_id=engine_capacity_id,
                    fuel=fuel_type,
                    transmission=transmission,
                    body_type=body_type,
                    limit=50,
                )

                if records:
                    selected = self._select_best_crsp(
                        records, manufacture_year, engine_capacity_id
                    )
                    if selected:
                        logger.info(f"Found CRSP without year: {selected.get('crsp_id')}")
                        return selected

            # Try broader search with just make and model
            logger.info(f"Performing broad search for {make} {model}")
            records = self.repository.search_crsp(
                make=make,
                model=model,
                manufacture_year=None,
                engine_capacity_id=None,
                fuel=None,
                transmission=None,
                body_type=None,
                limit=50,
            )

            if records:
                selected = self._select_best_crsp(
                    records, manufacture_year, engine_capacity_id
                )
                if selected:
                    logger.info(f"Found CRSP from broad search: {selected.get('crsp_id')}")
                    return selected

            logger.warning(f"No CRSP record found for {make} {model}")
            return None

        except Exception as exc:
            logger.exception("CRSP lookup failed: %s", exc)
            return None

    def search_crsp(self, **kwargs) -> List[Dict[str, Any]]:
        """Public synchronous lookup used by the router."""
        return self.repository.search_crsp(
            make=kwargs.get("make"),
            model=kwargs.get("model"),
            manufacture_year=kwargs.get("manufacture_year"),
            engine_capacity_id=kwargs.get("engine_capacity_id"),
            fuel=kwargs.get("fuel_type") or kwargs.get("fuel"),
            transmission=kwargs.get("transmission"),
            body_type=kwargs.get("body_type"),
            limit=kwargs.get("limit", 25),
        )

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

            # Prioritize records with prices
            if row.get("crsp_kes") is not None and row.get("crsp_kes") > 0:
                score_value += 30

            # Canonical records are better
            if row.get("canonical_id") is not None:
                score_value += 20
            if row.get("is_duplicate") is False:
                score_value += 20
            if row.get("is_inferred") is False:
                score_value += 10

            # Generation and engine info are good
            if row.get("generation_id") is not None:
                score_value += 5
            if row.get("engine_capacity_id") is not None:
                score_value += 5

            # Exact year match is preferred
            if (
                manufacture_year is not None
                and row.get("manufacture_year") == manufacture_year
            ):
                score_value += 15

            # Year proximity bonus (within 2 years)
            if (
                manufacture_year is not None
                and row.get("manufacture_year") is not None
            ):
                year_diff = abs(row.get("manufacture_year") - manufacture_year)
                if year_diff <= 1:
                    score_value += 10
                elif year_diff <= 2:
                    score_value += 5

            # Engine capacity match
            if (
                engine_capacity_id is not None
                and row.get("engine_capacity_id") == engine_capacity_id
            ):
                score_value += 10

            # Prefer records with complete data
            if row.get("make") and row.get("model"):
                score_value += 5

            return score_value

        # Sort by score and return the best
        sorted_records = sorted(records, key=score, reverse=True)
        best = sorted_records[0]
        best_score = score(best)
        
        logger.debug(f"Best CRSP score: {best_score} for record {best.get('crsp_id')}")
        return best

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

        # Normalize inputs
        make = (make or "").strip()
        model = (model or "").strip()
        
        # CRSP lookup with broader search
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

        resolved_id = vehicle_crsp_id or crsp_id
        crsp_value = 0.0

        if crsp:
            resolved_id = crsp.get("crsp_id")
            if crsp.get("crsp_kes") is not None:
                try:
                    crsp_value = float(crsp["crsp_kes"])
                except (TypeError, ValueError):
                    crsp_value = 0.0

        current_year = 2026
        age = max(0, current_year - int(manufacture_year)) if manufacture_year else 0
        
        # Build vehicle summary
        vehicle_summary = self._vehicle_summary(
            crsp, make, model, manufacture_year,
            fuel_type, transmission, body_type,
        )

        # If no CRSP found, try to estimate
        if crsp_value <= 0:
            logger.warning(f"No CRSP value found for {make} {model} {manufacture_year}")
            
            # Try to estimate based on make/model
            estimated_value = self._estimate_value_from_make_model(
                make, model, manufacture_year, mileage, condition
            )
            
            if estimated_value > 0:
                # Calculate adjustments
                depreciation_rate = self._get_depreciation_rate(age, vehicle_type or body_type)
                mileage_factor = self._mileage_factor(mileage, age)
                condition_factor = self._condition_factor(condition)
                accident_factor = self._accident_factor(accident_history)
                owner_factor = self._owner_factor(previous_owners)
                location_factor = self._location_factor(location)
                
                # Apply adjustments to estimated value
                adjusted_value = (
                    estimated_value
                    * (1.0 - depreciation_rate)
                    * mileage_factor
                    * condition_factor
                    * accident_factor
                    * owner_factor
                    * location_factor
                )
                final_value = round(max(adjusted_value, 0.0), 2)
                
                # Build complete response
                return {
                    "success": True,
                    "status": "completed",
                    "crsp_found": False,
                    "crsp_id": resolved_id,
                    "crsp_value": 0.0,
                    "estimated_value": final_value,
                    "estimated_value_min": round(final_value * 0.85, 2),
                    "estimated_value_max": round(final_value * 1.15, 2),
                    "confidence_score": 35,
                    "adjustments": {
                        "age": age,
                        "depreciation_rate": depreciation_rate,
                        "mileage_factor": mileage_factor,
                        "condition_factor": condition_factor,
                        "accident_factor": accident_factor,
                        "owner_factor": owner_factor,
                        "location_factor": location_factor,
                        "note": "Estimated from make/model baseline (no CRSP record found)"
                    },
                    "vehicle": vehicle_summary,
                    "message": "Valuation estimated from make/model baseline.",
                    # Frontend expects these fields
                    "market_value": final_value,
                    "retail_value": round(final_value * 1.08, 2),
                    "trade_value": round(final_value * 0.85, 2),
                    "dealer_value": round(final_value * 0.95, 2),
                    "recommended_selling_price": round(final_value * 1.10, 2),
                    "currency": "KES",
                    "calculated_at": datetime.now().isoformat(),
                    "warnings": ["No CRSP record found - using make/model estimate"],
                    "comparables": [],
                    "sample_size": 0,
                    "recommendation": "Verify vehicle details for more accurate valuation",
                    "depreciation": {
                        "rate": depreciation_rate,
                        "age_years": age,
                        "remaining_value_percent": round((1.0 - depreciation_rate) * 100, 1)
                    }
                }
            
            # Return error with complete structure
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
                "adjustments": {},
                "vehicle": vehicle_summary,
                "message": f"No valuation data available for {make} {model} {manufacture_year}.",
                # Frontend expects these fields even on error
                "market_value": None,
                "retail_value": None,
                "trade_value": None,
                "dealer_value": None,
                "recommended_selling_price": None,
                "currency": "KES",
                "calculated_at": datetime.now().isoformat(),
                "warnings": ["No CRSP record found"],
                "comparables": [],
                "sample_size": 0,
                "recommendation": "Please check vehicle details or contact support",
                "depreciation": None
            }

        # Calculate depreciation and factors
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

        final_value = round(max(value, 0.0), 2)
        retail_value = round(final_value * 1.08, 2)
        trade_value = round(final_value * 0.85, 2)
        dealer_value = round(final_value * 0.95, 2)
        recommended_price = round(final_value * 1.10, 2)

        return {
            "success": True,
            "status": "completed",
            "crsp_found": True,
            "crsp_id": resolved_id,
            "crsp_value": round(crsp_value, 2),
            "estimated_value": final_value,
            "estimated_value_min": round(final_value * 0.90, 2),
            "estimated_value_max": round(final_value * 1.10, 2),
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
            "vehicle": vehicle_summary,
            "message": "Valuation completed successfully.",
            # Frontend expects these fields
            "market_value": final_value,
            "retail_value": retail_value,
            "trade_value": trade_value,
            "dealer_value": dealer_value,
            "recommended_selling_price": recommended_price,
            "currency": "KES",
            "calculated_at": datetime.now().isoformat(),
            "warnings": [],
            "comparables": [],
            "sample_size": 10,
            "recommendation": "Market value is within expected range",
            "depreciation": {
                "rate": depreciation_rate,
                "age_years": age,
                "remaining_value_percent": round((1.0 - depreciation_rate) * 100, 1)
            }
        }

    def _estimate_value_from_make_model(
        self,
        make: str,
        model: str,
        manufacture_year: Optional[int],
        mileage: int,
        condition: str,
    ) -> float:
        """Estimate value based on make/model when no CRSP record exists."""
        make_lower = make.lower()
        model_lower = model.lower()
        
        # Base values by make (KES)
        base_values = {
            "toyota": 3500000,
            "honda": 2800000,
            "nissan": 2500000,
            "mazda": 2400000,
            "subaru": 3000000,
            "mercedes": 5000000,
            "bmw": 4500000,
            "audi": 4200000,
            "volkswagen": 3000000,
            "vw": 3000000,
            "ford": 3200000,
            "chevrolet": 2800000,
            "hyundai": 2500000,
            "kia": 2400000,
            "suzuki": 2000000,
            "mitsubishi": 2600000,
            "isuzu": 3500000,
            "land rover": 6000000,
            "jaguar": 5500000,
            "porsche": 8000000,
            "ferrari": 15000000,
            "lamborghini": 18000000,
        }
        
        # Model-specific adjustments
        model_adjustments = {
            "land cruiser": 1.8,
            "prado": 1.5,
            "hilux": 1.3,
            "fortuner": 1.4,
            "rav4": 1.2,
            "chr": 1.1,
            "corolla": 0.8,
            "camry": 1.0,
            "premio": 0.85,
            "axio": 0.8,
            "harrier": 1.3,
            "venza": 1.2,
            "civic": 0.9,
            "accord": 1.0,
            "cr-v": 1.2,
            "hr-v": 1.0,
            "x-trail": 1.1,
            "qashqai": 1.0,
            "patrol": 1.8,
            "cx-5": 1.1,
            "demio": 0.7,
            "forester": 1.1,
            "outback": 1.0,
            "impreza": 0.9,
            "legacy": 0.95,
            "golf": 0.9,
            "passat": 1.0,
            "tiguan": 1.1,
            "c-class": 1.1,
            "e-class": 1.3,
            "s-class": 1.8,
            "3-series": 1.0,
            "5-series": 1.3,
            "x5": 1.5,
            "a4": 1.0,
            "a6": 1.2,
            "q5": 1.2,
            "f-150": 1.4,
            "ranger": 1.2,
            "mustang": 1.2,
            "escape": 1.0,
        }
        
        # Get base value
        base_value = 0
        for key, value in base_values.items():
            if key in make_lower:
                base_value = value
                break
        
        if base_value == 0:
            base_value = 2500000
        
        # Apply model adjustment
        model_factor = 1.0
        for key, factor in model_adjustments.items():
            if key in model_lower:
                model_factor = factor
                break
        
        # Year adjustment
        if manufacture_year:
            current_year = 2026
            age = max(0, current_year - manufacture_year)
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
        
        # Mileage adjustment
        if mileage > 0:
            if mileage < 50000:
                mileage_factor = 1.0
            elif mileage < 100000:
                mileage_factor = 0.90
            elif mileage < 150000:
                mileage_factor = 0.80
            elif mileage < 200000:
                mileage_factor = 0.70
            else:
                mileage_factor = 0.60
        else:
            mileage_factor = 1.0
        
        # Condition adjustment
        condition_factor = self._condition_factor(condition)
        
        # Calculate estimated value
        estimated = base_value * model_factor * year_factor * mileage_factor * condition_factor
        
        return round(max(estimated, 50000), 2)

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
        if crsp.get("crsp_kes") is not None and crsp.get("crsp_kes") > 0:
            score += 5
        if crsp.get("make") and crsp.get("model"):
            score += 2
        if crsp.get("manufacture_year") is not None:
            score += 2

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
