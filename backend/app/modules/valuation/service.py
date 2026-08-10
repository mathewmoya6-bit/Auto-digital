# app/modules/valuation/service.py
# Auto-D Kenya - Valuation Service
# ================================================================

import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException, ValidationException
from app.modules.valuation.engine import ValuationEngine
from app.modules.valuation.repository import ValuationRepository

logger = logging.getLogger(__name__)


class ValuationService:
    """
    Valuation service for business logic.

    Canonical vehicle identifier:
        crsp_id

    For backward compatibility this service also accepts:
        vehicle_crsp_id
        variant_id

    The CRSP record is read from vehicle_crsp_prices.
    """

    def __init__(self):
        self.engine = ValuationEngine()
        self.repository = ValuationRepository()
        self.supabase = get_supabase()
        logger.info("ValuationService initialized")

    # ================================================================
    # HELPERS
    # ================================================================

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _resolve_crsp_id(
        crsp_id: Optional[int],
        vehicle_crsp_id: Optional[int],
        variant_id: Optional[int],
    ) -> int:
        """
        Resolve the vehicle identifier.

        Priority:
            1. crsp_id
            2. vehicle_crsp_id
            3. variant_id

        variant_id is retained only for compatibility with older routers.
        """
        resolved = crsp_id or vehicle_crsp_id or variant_id

        if resolved is None:
            raise ValidationException("Vehicle CRSP ID is required")

        try:
            resolved = int(resolved)
        except (TypeError, ValueError):
            raise ValidationException("Vehicle CRSP ID must be an integer")

        if resolved <= 0:
            raise ValidationException("Vehicle CRSP ID must be greater than zero")

        return resolved

    # ================================================================
    # MAIN VALUATION METHOD
    # ================================================================

    async def calculate_valuation(
        self,
        crsp_id: Optional[int] = None,
        year: int = 0,
        mileage: int = 0,
        condition: str = "good",
        accident_history: str = "none",
        location: str = "nairobi",
        fuel_type: Optional[str] = None,
        transmission: Optional[str] = None,
        ownership_count: int = 1,
        service_history: bool = True,
        user_id: Optional[str] = None,
        profit_margin_percent: float = 5.00,
        # Backward-compatible aliases:
        vehicle_crsp_id: Optional[int] = None,
        variant_id: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Calculate vehicle valuation.

        Canonical caller argument:
            crsp_id

        Backward-compatible arguments:
            vehicle_crsp_id
            variant_id

        This prevents failures when an older router still sends
        variant_id while the API schema uses crsp_id.
        """

        resolved_crsp_id = self._resolve_crsp_id(
            crsp_id=crsp_id,
            vehicle_crsp_id=vehicle_crsp_id,
            variant_id=variant_id,
        )

        logger.info(
            "Starting valuation: crsp_id=%s year=%s mileage=%s",
            resolved_crsp_id,
            year,
            mileage,
        )

        # ------------------------------------------------------------
        # VALIDATION
        # ------------------------------------------------------------

        current_year = self._utc_now().year

        if year < 1980 or year > current_year + 1:
            raise ValidationException(f"Invalid year: {year}")

        if mileage < 0:
            raise ValidationException(f"Invalid mileage: {mileage}")

        if profit_margin_percent < 0:
            raise ValidationException("Profit margin cannot be negative")

        condition = (condition or "good").lower().strip()
        accident_history = (accident_history or "none").lower().strip()
        location = (location or "nairobi").upper().strip()

        condition_map = {
            "very_good": "EXCELLENT",
            "excellent": "EXCELLENT",
            "good": "GOOD",
            "fair": "FAIR",
            "poor": "POOR",
        }
        condition_db = condition_map.get(condition, "GOOD")

        accident_map = {
            "none": "NONE",
            "minor": "MINOR_REPAIR",
            "major": "ACCIDENT_REPAIRED",
            "total_loss": "STRUCTURAL_DAMAGE",
        }
        accident_history_db = accident_map.get(accident_history, "NONE")

        logger.info(
            "Valuation request: crsp_id=%s year=%s mileage=%s "
            "condition=%s accident=%s location=%s",
            resolved_crsp_id,
            year,
            mileage,
            condition_db,
            accident_history_db,
            location,
        )

        # ------------------------------------------------------------
        # GET CRSP VEHICLE
        # ------------------------------------------------------------

        try:
            crsp_vehicle = self._get_crsp_vehicle(resolved_crsp_id)
            crsp_price = self._get_crsp_price(crsp_vehicle)
        except NotFoundException:
            raise
        except ValidationException:
            raise
        except Exception as exc:
            logger.exception(
                "Error fetching CRSP vehicle %s",
                resolved_crsp_id,
            )
            raise NotFoundException(
                f"Failed to fetch CRSP vehicle: {exc}"
            )

        vehicle = {
            "crsp_id": resolved_crsp_id,
            "make": crsp_vehicle.get("make")
            or crsp_vehicle.get("make_name"),
            "model": crsp_vehicle.get("model")
            or crsp_vehicle.get("model_name"),
            "variant_name": crsp_vehicle.get("variant")
            or crsp_vehicle.get("variant_name"),
            "fuel_type": crsp_vehicle.get("crsp_fuel")
            or crsp_vehicle.get("fuel_type")
            or crsp_vehicle.get("fuel_type_name"),
            "transmission": crsp_vehicle.get("transmission")
            or crsp_vehicle.get("transmission_type_name"),
            "engine_size_cc": crsp_vehicle.get("engine_capacity_cc")
            or crsp_vehicle.get("engine_capacity")
            or crsp_vehicle.get("engine_size_cc"),
            "body_type": crsp_vehicle.get("body_type")
            or crsp_vehicle.get("body_type_name"),
            "crsp_price": crsp_price,
            "year": year,
        }

        if fuel_type:
            vehicle["fuel_type"] = fuel_type

        if transmission:
            vehicle["transmission"] = transmission

        logger.info(
            "Vehicle: %s %s (%s)",
            vehicle.get("make"),
            vehicle.get("model"),
            vehicle.get("variant_name"),
        )

        # ------------------------------------------------------------
        # VEHICLE TYPE
        # ------------------------------------------------------------

        vehicle_type = self._infer_vehicle_type(vehicle.get("body_type"))

        logger.info("Vehicle type: %s", vehicle_type)

        # ------------------------------------------------------------
        # REPOSITORY VALUATION
        # ------------------------------------------------------------

        try:
            result_data = self.repository.calculate_valuation(
                vehicle_crsp_id=resolved_crsp_id,
                manufacture_year=year,
                mileage_km=mileage,
                vehicle_type=vehicle_type,
                condition_name=condition_db,
                accident_status=accident_history_db,
                location_name=location,
                profit_margin_percent=profit_margin_percent,
            )

            result_data = result_data or {}

            final_value = float(result_data.get("final_value") or 0)
            confidence_score = int(
                result_data.get("confidence_score") or 65
            )

            logger.info(
                "Valuation calculation completed: crsp_id=%s final_value=%s",
                resolved_crsp_id,
                final_value,
            )

            now = self._utc_now()
            report_number = self._generate_report_number()

            vehicle_info = self._build_vehicle_info(
                vehicle,
                resolved_crsp_id,
                year,
            )

            response = self._build_success_response(
                report_number=report_number,
                now=now,
                vehicle_info=vehicle_info,
                final_value=final_value,
                confidence_score=confidence_score,
                result_data=result_data,
            )

            if user_id:
                await self._save_valuation_history(
                    user_id=user_id,
                    variant_id=resolved_crsp_id,
                    report_number=report_number,
                    make=vehicle.get("make"),
                    model=vehicle.get("model"),
                    market_value=response["market_value"],
                    retail_value=response["retail_value"],
                    trade_value=response["trade_value"],
                    confidence_score=response["confidence_score"],
                    year=year,
                    mileage=mileage,
                    location=location,
                    condition=condition_db,
                    accident_history=accident_history_db,
                )

            logger.info(
                "Valuation report %s generated successfully",
                report_number,
            )

            return response

        except (NotFoundException, ValidationException):
            raise

        except ValueError as exc:
            logger.error("Valuation validation error: %s", exc)
            raise ValidationException(str(exc))

        except Exception as exc:
            logger.exception(
                "Valuation engine/repository failed for CRSP %s",
                resolved_crsp_id,
            )

            # Do not return zero. Use a deterministic fallback based on
            # the CRSP price already retrieved from the database.
            base_price = crsp_price or self._estimate_base_price(
                vehicle,
                year,
            )

            fallback_result = self._create_fallback_valuation(
                vehicle=vehicle,
                year=year,
                mileage=mileage,
                base_price=base_price,
            )

            return self._build_response_from_result(
                result=fallback_result,
                vehicle=vehicle,
                vehicle_crsp_id=resolved_crsp_id,
                year=year,
            )

    # ================================================================
    # VEHICLE TYPE
    # ================================================================

    @staticmethod
    def _infer_vehicle_type(body_type: Optional[str]) -> str:
        body = (body_type or "").upper().strip()

        if "SUV" in body or "CROSSOVER" in body:
            return "SUV"
        if "PICKUP" in body or "TRUCK" in body:
            return "PICKUP"
        if "VAN" in body or "MINIVAN" in body:
            return "VAN"
        if "HATCHBACK" in body:
            return "HATCHBACK"
        if "COUPE" in body:
            return "COUPE"
        if "CONVERTIBLE" in body:
            return "CONVERTIBLE"
        if "WAGON" in body or "ESTATE" in body:
            return "WAGON"
        if "MOTORCYCLE" in body or "BIKE" in body:
            return "MOTORCYCLE"

        return "SEDAN"

    # ================================================================
    # CRSP LOOKUP
    # ================================================================

    def _get_crsp_vehicle(self, crsp_id: int) -> Dict[str, Any]:
        """Get a vehicle from vehicle_crsp_prices using crsp_id."""
        try:
            response = (
                self.supabase
                .table("vehicle_crsp_prices")
                .select("*")
                .eq("crsp_id", crsp_id)
                .limit(1)
                .execute()
            )

            if not response.data:
                raise NotFoundException(
                    f"CRSP vehicle {crsp_id} not found"
                )

            vehicle = response.data[0]

            logger.info(
                "CRSP vehicle found: crsp_id=%s make=%s model=%s",
                crsp_id,
                vehicle.get("make"),
                vehicle.get("model"),
            )

            return vehicle

        except NotFoundException:
            raise

        except Exception as exc:
            logger.exception(
                "Failed to fetch CRSP vehicle %s",
                crsp_id,
            )
            raise NotFoundException(
                f"Failed to fetch CRSP vehicle {crsp_id}: {exc}"
            )

    def _get_crsp_price(self, crsp_vehicle: Dict[str, Any]) -> float:
        """Extract a valid CRSP base price."""
        price_fields = (
            "crsp_price",
            "crsp_kes",
            "base_price",
            "price",
            "market_value",
            "retail_price",
        )

        for field in price_fields:
            value = crsp_vehicle.get(field)

            if value is None:
                continue

            try:
                price = float(value)
            except (TypeError, ValueError):
                continue

            if price > 0:
                return price

        crsp_id = crsp_vehicle.get("crsp_id")

        logger.error(
            "CRSP vehicle %s has no valid price",
            crsp_id,
        )

        raise ValidationException(
            f"CRSP vehicle {crsp_id} does not have a valid CRSP price"
        )

    # ================================================================
    # RESPONSE HELPERS
    # ================================================================

    @staticmethod
    def _generate_report_number() -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        suffix = secrets.token_hex(4).upper()
        return f"AUTO-VAL-{timestamp}-{suffix}"

    @staticmethod
    def _build_vehicle_info(
        vehicle: Dict[str, Any],
        crsp_id: int,
        year: int,
    ) -> Dict[str, Any]:
        return {
            "crsp_id": crsp_id,
            # Kept for compatibility with older frontend responses.
            "variant_id": crsp_id,
            "make": vehicle.get("make"),
            "model": vehicle.get("model"),
            "variant_name": vehicle.get("variant_name"),
            "year": year,
            "fuel_type": vehicle.get("fuel_type"),
            "transmission": vehicle.get("transmission"),
            "engine_size_cc": vehicle.get("engine_size_cc"),
            "body_type": vehicle.get("body_type"),
        }

    def _build_success_response(
        self,
        report_number: str,
        now: datetime,
        vehicle_info: Dict[str, Any],
        final_value: float,
        confidence_score: int,
        result_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        retail_value = round(final_value * 1.08, 2)
        trade_value = round(final_value * 0.85, 2)
        dealer_value = round(final_value * 0.95, 2)
        recommended_price = round(final_value * 1.10, 2)

        return {
            "report_number": report_number,
            "generated_at": now,
            "status": "completed",
            "version": "2.0",
            "vehicle": vehicle_info,
            "valuation": {
                "vehicle": vehicle_info,
                "market_value": round(final_value, 2),
                "retail_value": retail_value,
                "trade_value": trade_value,
                "dealer_value": dealer_value,
                "recommended_selling_price": recommended_price,
                "currency": "KES",
                "confidence_score": confidence_score,
                "estimated_value_range": {
                    "minimum": round(final_value * 0.90, 2),
                    "maximum": round(final_value * 1.10, 2),
                },
                "sample_size": result_data.get("sample_size", 0),
                "adjustments": result_data.get("adjustments", []),
                "comparables": result_data.get("comparables", []),
                "warnings": result_data.get("warnings", []),
                "calculated_at": now,
            },
            "market_value": round(final_value, 2),
            "retail_value": retail_value,
            "trade_value": trade_value,
            "dealer_value": dealer_value,
            "confidence_score": confidence_score,
            "calculated_at": now,
            "adjustments": result_data.get("adjustments", []),
            "comparables": result_data.get("comparables", []),
            "recommendation": result_data.get("recommendation"),
            "warnings": result_data.get("warnings", []),
            "currency": "KES",
            "depreciation": result_data.get("depreciation"),
            "disclaimer": (
                "This valuation is generated using the AUTO-D vehicle "
                "valuation engine and should be treated as an indicative "
                "market estimate."
            ),
        }

    def _build_response_from_result(
        self,
        result: Dict[str, Any],
        vehicle: Dict[str, Any],
        vehicle_crsp_id: int,
        year: int,
    ) -> Dict[str, Any]:
        """Build a response from a normal or fallback result."""
        now = self._utc_now()
        report_number = self._generate_report_number()

        market_value = float(result.get("market_value") or 0)
        confidence_score = int(result.get("confidence_score") or 40)

        vehicle_info = self._build_vehicle_info(
            vehicle=vehicle,
            crsp_id=vehicle_crsp_id,
            year=year,
        )

        return self._build_success_response(
            report_number=report_number,
            now=now,
            vehicle_info=vehicle_info,
            final_value=market_value,
            confidence_score=confidence_score,
            result_data=result,
        )

    # ================================================================
    # FALLBACK
    # ================================================================

    @staticmethod
    def _estimate_base_price(
        vehicle: Dict[str, Any],
        year: int,
    ) -> float:
        make = (vehicle.get("make") or "").lower()
        model = (vehicle.get("model") or "").lower()

        if "toyota" in make:
            if "land cruiser" in model or "prado" in model:
                return 8_500_000.0
            if "hilux" in model or "fortuner" in model:
                return 5_500_000.0
            if "corolla" in model or "premio" in model or "axio" in model:
                return 3_500_000.0
            if "rav4" in model or "chr" in model:
                return 4_500_000.0
            if "harrier" in model or "venza" in model:
                return 5_000_000.0
            return 3_000_000.0

        if "mercedes" in make or "bmw" in make or "audi" in make:
            return 6_000_000.0
        if "nissan" in make or "honda" in make or "mazda" in make:
            return 3_500_000.0
        if "subaru" in make:
            return 4_000_000.0
        if "volkswagen" in make or "vw" in make:
            return 3_500_000.0
        if "ford" in make:
            return 4_000_000.0
        if "isuzu" in make:
            return 5_000_000.0

        return 2_500_000.0

    @staticmethod
    def _create_fallback_valuation(
        vehicle: Dict[str, Any],
        year: int,
        mileage: int,
        base_price: float,
    ) -> Dict[str, Any]:
        logger.warning(
            "Creating fallback valuation for %s %s",
            vehicle.get("make"),
            vehicle.get("model"),
        )

        current_year = datetime.now(timezone.utc).year
        age = max(0, current_year - year)

        depreciation_rate = min(0.85, age * 0.05)
        current_value = max(
            base_price * (1 - depreciation_rate),
            base_price * 0.15,
        )

        mileage_factor = 1.0

        if mileage > 50_000:
            mileage_penalty = min(
                ((mileage - 50_000) / 50_000) * 0.05,
                0.20,
            )
            mileage_factor = 1 - mileage_penalty
            current_value *= mileage_factor

        return {
            "market_value": round(current_value, 2),
            "retail_value": round(current_value * 1.08, 2),
            "trade_value": round(current_value * 0.85, 2),
            "dealer_value": round(current_value * 0.95, 2),
            "confidence_score": 40,
            "adjustments": {
                "age_factor": round(1 - depreciation_rate, 4),
                "mileage_factor": round(mileage_factor, 4),
            },
            "sample_size": 0,
            "comparables": [],
            "warnings": [
                "Fallback valuation used because the primary valuation "
                "calculation failed."
            ],
        }

    # ================================================================
    # HISTORY
    # ================================================================

    async def _save_valuation_history(
        self,
        user_id: str,
        variant_id: int,
        report_number: str,
        make: str,
        model: str,
        market_value: float,
        retail_value: float,
        trade_value: float,
        confidence_score: int,
        year: int,
        mileage: int,
        location: str,
        condition: str,
        accident_history: str,
    ) -> None:
        """Save valuation history without breaking the valuation response."""
        history_data = {
            "user_id": user_id,
            "variant_id": variant_id,
            "report_number": report_number,
            "make": make,
            "model": model,
            "market_value": market_value,
            "retail_value": retail_value,
            "trade_value": trade_value,
            "confidence_score": confidence_score,
            "year": year,
            "mileage": mileage,
            "location": location,
            "condition": condition,
            "accident_history": accident_history,
            "created_at": self._utc_now().isoformat(),
        }

        try:
            self.supabase.table(
                "valuation_history"
            ).insert(history_data).execute()

            logger.info(
                "Valuation history saved for user %s",
                user_id,
            )

        except Exception as exc:
            logger.warning(
                "Full valuation history insert failed: %s",
                exc,
            )

            # Retry with the most commonly available core fields.
            safe_history = {
                key: value
                for key, value in history_data.items()
                if key not in {
                    "accident_history",
                    "location",
                    "report_number",
                }
            }

            try:
                self.supabase.table(
                    "valuation_history"
                ).insert(safe_history).execute()

                logger.info(
                    "Valuation history saved using core fields"
                )

            except Exception as retry_exc:
                logger.warning(
                    "Valuation history could not be saved: %s",
                    retry_exc,
                )

    async def get_valuation_history(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        try:
            response = (
                self.supabase
                .table("valuation_history")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
            return response.data or []

        except Exception as exc:
            logger.error(
                "Error getting valuation history: %s",
                exc,
            )
            return []

    async def get_valuation_by_id(
        self,
        report_id: int,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            response = (
                self.supabase
                .table("valuation_history")
                .select("*")
                .eq("id", report_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None

        except Exception as exc:
            logger.error(
                "Error getting valuation %s: %s",
                report_id,
                exc,
            )
            return None

    async def get_valuation_by_report_number(
        self,
        report_number: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            response = (
                self.supabase
                .table("valuation_history")
                .select("*")
                .eq("report_number", report_number)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None

        except Exception as exc:
            logger.error(
                "Error getting valuation by report number %s: %s",
                report_number,
                exc,
            )
            return None

    # ================================================================
    # STATISTICS
    # ================================================================

    async def get_valuation_stats(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        empty_stats = {
            "total_valuations": 0,
            "average_value": 0.0,
            "highest_value": 0.0,
            "lowest_value": 0.0,
            "last_valuation_date": None,
            "total_value": 0.0,
            "valuations_by_make": {},
            "valuations_by_month": {},
            "average_confidence": 0.0,
        }

        try:
            history = await self.get_valuation_history(user_id)

            if not history:
                return empty_stats

            values: List[float] = []
            makes: Dict[str, int] = {}
            months: Dict[str, int] = {}
            confidences: List[float] = []

            for item in history:
                try:
                    value = float(item.get("market_value") or 0)
                except (TypeError, ValueError):
                    value = 0

                if value > 0:
                    values.append(value)

                try:
                    confidence = float(
                        item.get("confidence_score") or 0
                    )
                except (TypeError, ValueError):
                    confidence = 0

                if confidence > 0:
                    confidences.append(confidence)

                make = item.get("make") or "Unknown"
                makes[make] = makes.get(make, 0) + 1

                created_at = item.get("created_at")

                if created_at:
                    try:
                        parsed_date = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        )
                        month_key = parsed_date.strftime("%Y-%m")
                        months[month_key] = months.get(month_key, 0) + 1
                    except (TypeError, ValueError):
                        pass

            return {
                "total_valuations": len(history),
                "average_value": (
                    sum(values) / len(values)
                    if values else 0.0
                ),
                "highest_value": max(values) if values else 0.0,
                "lowest_value": min(values) if values else 0.0,
                "last_valuation_date": (
                    history[0].get("created_at")
                    if history else None
                ),
                "total_value": sum(values),
                "valuations_by_make": makes,
                "valuations_by_month": months,
                "average_confidence": (
                    sum(confidences) / len(confidences)
                    if confidences else 0.0
                ),
            }

        except Exception as exc:
            logger.exception(
                "Error getting valuation statistics: %s",
                exc,
            )
            return empty_stats

    # ================================================================
    # HEALTH CHECK
    # ================================================================

    async def health_check(self) -> Dict[str, Any]:
        try:
            self.supabase.table(
                "vehicle_crsp_prices"
            ).select("crsp_id").limit(1).execute()

            db_status = "healthy"

        except Exception as exc:
            logger.error(
                "Database health check failed: %s",
                exc,
            )
            db_status = "unhealthy"

        return {
            "status": (
                "healthy"
                if db_status == "healthy"
                else "degraded"
            ),
            "service": "valuation",
            "version": "2.2",
            "timestamp": self._utc_now().isoformat(),
            "database": db_status,
        }
