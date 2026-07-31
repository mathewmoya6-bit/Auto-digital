# app/modules/running_cost/service.py
"""Running Cost service for Auto-D Kenya

REBUILT FROM SCRATCH — the version this replaced had every method body as
a bare `pass` (comments like "# [Keep existing implementation - same as
before]" suggest the real logic was lost during a refactor). No prior
implementation was recoverable, so this is a fresh build against the
RunningCostRequest/RunningCostResponse contract in schemas.py.

⚠️ VERIFY BEFORE RELYING ON THIS: `get_variant()` below queries a
`vehicle_master_specs` view (confirmed to exist — mileage.html's own
console log referenced it: "Using view: vehicle_master_specs") but the
actual column names on that view were not available when this was written.
`_extract_field()` tries several plausible aliases per field and falls
back to a logged default rather than crashing, so this will *run*
regardless — but the numbers it produces are only as accurate as those
column-name guesses. Check the `logger.warning` output after your first
few real calls; every fallback that fires will tell you exactly which
field needs its real column name substituted in `_VARIANT_FIELD_ALIASES`.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from app.core.database import get_supabase
from app.modules.running_cost.schemas import RunningCostRequest, ProjectionYear

logger = logging.getLogger(__name__)


class RunningCostService:
    """Service for running cost calculations with full vehicle endpoint integration"""

    # Column-name aliases to try, in order, when reading a variant record.
    # Update the left-hand alias lists once you confirm the real schema —
    # this is the single place to fix if `get_variant` is reading wrong data.
    _VARIANT_FIELD_ALIASES = {
        "purchase_price": ["purchase_price", "price", "base_price", "msrp", "list_price"],
        "engine_size": ["engine_size", "engine_capacity", "engine_cc", "displacement"],
        "fuel_type": ["fuel_type", "fuel"],
        "make": ["make", "make_name"],
        "model": ["model", "model_name"],
        "generation": ["generation", "generation_name"],
        "variant_name": ["variant_name", "name", "trim"],
    }

    def __init__(self):
        self.supabase = get_supabase()
        self._variant_cache = {}
        self._make_cache = {}
        self._model_cache = {}
        self._generation_cache = {}

        # ─── DEFAULT FALLBACK VALUES (only used if DB is unreachable) ───
        self._default_fuel_prices = {
            "petrol": 193.00,
            "diesel": 180.00,
            "electric": 20.00,
            "hybrid": 193.00,
            "gas": 150.00,
            "lpg": 150.00,
            "cng": 140.00
        }

        self._default_maintenance_rates = {
            "petrol": 2.50,
            "diesel": 3.00,
            "electric": 1.50,
            "hybrid": 2.00,
            "gas": 2.20,
            "lpg": 2.20,
            "cng": 2.00
        }

        self._default_insurance_rates = {
            "comprehensive": 0.04,
            "third_party": 0.015
        }

        self._default_depreciation_rates = {
            0: 0.20, 1: 0.18, 2: 0.15, 3: 0.12,
            4: 0.10, 5: 0.08, 6: 0.07, 7: 0.06,
            8: 0.05, 9: 0.04, 10: 0.03, 11: 0.03,
            12: 0.03, 13: 0.02, 14: 0.02, 15: 0.02
        }

        self._default_tyre_lifespan_km = 50000
        self._default_tyre_cost_per_set = 48000  # 4 tyres, KES

        # ─── CACHED CONFIGURATIONS ──────────────────────────────────
        self._config_cache = {}
        self._config_cache_time = None
        self._config_cache_ttl = 300  # 5 minutes

    # ─── CONFIGURATION LOADER ──────────────────────────────────────

    async def _load_config_from_db(self) -> Dict[str, Any]:
        """Load configuration overrides from DB with caching. Falls back to
        defaults on any error — this must never be what breaks a calculation."""
        now = datetime.now(timezone.utc).timestamp()
        if (
            self._config_cache
            and self._config_cache_time
            and (now - self._config_cache_time) < self._config_cache_ttl
        ):
            return self._config_cache

        try:
            # Optional override table — safe to not exist. If you add one,
            # expected shape: single row with columns matching the keys in
            # _get_default_config()'s output.
            response = self.supabase.table("running_cost_config").select("*").limit(1).execute()
            if response.data:
                config = {**self._get_default_config(), **response.data[0]}
            else:
                config = self._get_default_config()
        except Exception as e:
            logger.warning(f"Could not load running_cost_config from DB, using defaults: {e}")
            config = self._get_default_config()

        self._config_cache = config
        self._config_cache_time = now
        return config

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration when DB is unavailable"""
        return {
            "fuel_prices": self._default_fuel_prices,
            "maintenance_rates": self._default_maintenance_rates,
            "insurance_rates": self._default_insurance_rates,
            "depreciation_rates": self._default_depreciation_rates,
            "tyre_lifespan_km": self._default_tyre_lifespan_km,
            "tyre_cost_per_set": self._default_tyre_cost_per_set,
        }

    # ─── FIELD EXTRACTION HELPER ────────────────────────────────────

    def _extract_field(self, record: Dict[str, Any], field: str, default: Any) -> Any:
        """Try each known alias for `field` in order; return the first hit,
        else `default` with a warning so misconfigured column names surface
        in logs instead of silently producing wrong numbers forever."""
        aliases = self._VARIANT_FIELD_ALIASES.get(field, [field])
        for alias in aliases:
            if alias in record and record[alias] is not None:
                return record[alias]
        logger.warning(
            f"None of the expected columns {aliases} found for '{field}' "
            f"on variant record (keys present: {list(record.keys())}); "
            f"using default {default!r}"
        )
        return default

    # ─── VEHICLE ENDPOINT METHODS ──────────────────────────────────

    async def get_makes(self) -> List[Dict[str, Any]]:
        """GET /api/v1/makes - Get all vehicle makes"""
        try:
            response = self.supabase.table("vehicle_makes").select("*").order("name").execute()
            return response.data or []
        except Exception as e:
            logger.error(f"get_makes failed: {e}")
            raise

    async def get_models(self, make_id: int) -> List[Dict[str, Any]]:
        """GET /api/v1/models/{make_id} - Get models by make ID"""
        try:
            response = (
                self.supabase.table("vehicle_models")
                .select("*")
                .eq("make_id", make_id)
                .order("name")
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"get_models failed for make_id={make_id}: {e}")
            raise

    async def get_generations(self, model_id: int) -> List[Dict[str, Any]]:
        """GET /api/v1/generations/{model_id} - Get generations by model ID

        NOTE: assumes a `vehicle_generations` table with a `model_id` FK.
        If your schema doesn't have a separate generations table (memory
        of this project's schema mentions vehicle_types → vehicle_makes →
        vehicle_models → vehicle_variants with no generations tier), this
        will 500 with a clean Postgrest "relation does not exist" error —
        that error message will tell you definitively whether to adjust
        this to skip straight to variants instead.
        """
        try:
            response = (
                self.supabase.table("vehicle_generations")
                .select("*")
                .eq("model_id", model_id)
                .order("name")
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"get_generations failed for model_id={model_id}: {e}")
            raise

    async def get_variants(self, generation_id: int) -> List[Dict[str, Any]]:
        """GET /api/v1/variants/{generation_id} - Get variants by generation ID"""
        try:
            response = (
                self.supabase.table("vehicle_variants")
                .select("*")
                .eq("generation_id", generation_id)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"get_variants failed for generation_id={generation_id}: {e}")
            raise

    async def get_variant(self, variant_id: int) -> Optional[Dict[str, Any]]:
        """GET /api/v1/variant/{variant_id} - Get variant by ID.

        Queries `vehicle_master_specs` (a flattened view, per mileage.html's
        own console log) rather than the raw `vehicle_variants` table, on
        the assumption it already joins make/model/generation/spec data.
        """
        if variant_id in self._variant_cache:
            return self._variant_cache[variant_id]

        try:
            response = (
                self.supabase.table("vehicle_master_specs")
                .select("*")
                .eq("id", variant_id)
                .limit(1)
                .execute()
            )
            if not response.data:
                return None
            variant = response.data[0]
            self._variant_cache[variant_id] = variant
            return variant
        except Exception as e:
            logger.error(f"get_variant failed for variant_id={variant_id}: {e}")
            raise

    async def search_vehicles(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """GET /api/v1/search - Search vehicles by make/model/variant name"""
        try:
            response = (
                self.supabase.table("vehicle_master_specs")
                .select("*")
                .or_(f"make.ilike.%{query}%,model.ilike.%{query}%,variant_name.ilike.%{query}%")
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"search_vehicles failed for query='{query}': {e}")
            raise

    async def get_variant_with_details(self, variant_id: int) -> Optional[Dict[str, Any]]:
        """Get variant with full hierarchy — vehicle_master_specs is already
        flattened, so this currently just delegates to get_variant()."""
        return await self.get_variant(variant_id)

    # ─── MAIN CALCULATION ───────────────────────────────────────────

    async def calculate_running_cost(self, request: RunningCostRequest, user_id: int) -> Dict[str, Any]:
        """Calculate running costs with full vehicle data.

        Returns a flat dict matching RunningCostResponse exactly — FastAPI
        validates it against that response_model in the router.
        """
        variant = await self.get_variant(request.variant_id)
        if not variant:
            raise ValueError(f"Vehicle variant {request.variant_id} not found")

        config = await self._load_config_from_db()

        # ─── Extract vehicle data (see _VARIANT_FIELD_ALIASES for column mapping) ───
        purchase_price = float(self._extract_field(variant, "purchase_price", 3_000_000))
        engine_size = float(self._extract_field(variant, "engine_size", 2.0))
        fuel_type = str(self._extract_field(variant, "fuel_type", "petrol")).lower()

        fuel_prices = config["fuel_prices"]
        maintenance_rates = config["maintenance_rates"]
        insurance_rates = config["insurance_rates"]
        depreciation_rates = {int(k): v for k, v in config["depreciation_rates"].items()}
        tyre_lifespan_km = config["tyre_lifespan_km"]
        tyre_cost_per_set = config["tyre_cost_per_set"]

        current_year = datetime.now(timezone.utc).year
        age = max(0, current_year - request.year)

        # ─── Fuel efficiency & cost ───────────────────────────────
        efficiency_km_per_l = self._calculate_fuel_efficiency(
            engine_size, request.year, request.trip_type, fuel_type
        )
        fuel_price = request.fuel_price if request.fuel_price else fuel_prices.get(fuel_type, 193.0)
        fuel_cost_per_km = fuel_price / efficiency_km_per_l if efficiency_km_per_l > 0 else 0.0
        fuel_cost_trip = fuel_cost_per_km * request.distance

        # ─── Maintenance ──────────────────────────────────────────
        if request.include_maintenance:
            base_maintenance_rate = maintenance_rates.get(fuel_type, 2.5)
            usage_multiplier = {
                "private": 1.0, "commercial": 1.2, "fleet": 1.3, "taxi": 1.4
            }.get(request.usage_type, 1.0)
            condition_multiplier = {
                "poor": 1.3, "fair": 1.1, "good": 1.0, "excellent": 0.9
            }.get(request.condition, 1.0)
            maintenance_per_km = base_maintenance_rate * usage_multiplier * condition_multiplier
        else:
            maintenance_per_km = 0.0
        service_cost_trip = maintenance_per_km * request.distance

        # ─── Tyres ────────────────────────────────────────────────
        if request.include_tyres:
            style_multiplier = {"eco": 0.9, "normal": 1.0, "aggressive": 1.25}.get(
                request.driving_style, 1.0
            )
            tyre_per_km = (tyre_cost_per_set / tyre_lifespan_km) * style_multiplier
        else:
            tyre_per_km = 0.0
        tyre_cost_trip = tyre_per_km * request.distance

        # ─── Insurance ────────────────────────────────────────────
        if request.include_insurance:
            insurance_rate = insurance_rates.get(request.insurance_type, 0.04)
            current_value = self._value_after_years(purchase_price, age, depreciation_rates)
            annual_insurance = current_value * insurance_rate
            insurance_per_km = annual_insurance / request.annual_mileage if request.annual_mileage else 0.0
        else:
            insurance_per_km = 0.0
        insurance_cost_trip = insurance_per_km * request.distance

        # ─── Depreciation ─────────────────────────────────────────
        if request.include_depreciation:
            value_before = self._value_after_years(purchase_price, age, depreciation_rates)
            value_after = self._value_after_years(purchase_price, age + 1, depreciation_rates)
            annual_depreciation = max(0.0, value_before - value_after)
            depreciation_per_km = annual_depreciation / request.annual_mileage if request.annual_mileage else 0.0
        else:
            depreciation_per_km = 0.0
        depreciation_cost_trip = depreciation_per_km * request.distance

        # ─── Trip totals ──────────────────────────────────────────
        trip_total = (
            fuel_cost_trip + service_cost_trip + tyre_cost_trip
            + insurance_cost_trip + depreciation_cost_trip
        )
        trip_cost_per_km = trip_total / request.distance if request.distance else 0.0

        # ─── Monthly / annual projections (based on annual_mileage) ─
        monthly_mileage = request.annual_mileage / 12
        annual_fuel = fuel_cost_per_km * request.annual_mileage
        annual_service = maintenance_per_km * request.annual_mileage
        annual_tyre = tyre_per_km * request.annual_mileage
        annual_insurance_total = insurance_per_km * request.annual_mileage
        annual_depreciation_total = depreciation_per_km * request.annual_mileage

        monthly_fuel = annual_fuel / 12
        monthly_service = annual_service / 12
        monthly_tyre = annual_tyre / 12
        monthly_insurance = annual_insurance_total / 12
        monthly_depreciation = annual_depreciation_total / 12

        # ─── 5(+)-year projection ─────────────────────────────────
        five_year_data = self._calculate_five_year_data(
            purchase_price=purchase_price,
            request=request,
            fuel_type=fuel_type,
            fuel_price=fuel_price,
            maintenance_rate=maintenance_per_km,
            tyre_cost_per_km=tyre_per_km,
            insurance_rate=insurance_rates.get(request.insurance_type, 0.04),
            vehicle_year=request.year,
            engine_size=engine_size,
            depreciation_rates=depreciation_rates,
        )
        total_5_year_cost = sum(y["total"] for y in five_year_data)

        current_value = self._value_after_years(purchase_price, age, depreciation_rates)
        final_projection_value = five_year_data[-1]["value"] if five_year_data else current_value

        result = {
            "tripTotal": round(trip_total, 2),
            "tripCostPerKm": round(trip_cost_per_km, 2),
            "distance": request.distance,

            "fuelCostTrip": round(fuel_cost_trip, 2),
            "serviceTrip": round(service_cost_trip, 2),
            "tyreTrip": round(tyre_cost_trip, 2),
            "insuranceTrip": round(insurance_cost_trip, 2),
            "depreciationTrip": round(depreciation_cost_trip, 2),

            "fuelCostPerKm": round(fuel_cost_per_km, 2),
            "servicePerKm": round(maintenance_per_km, 2),
            "tyrePerKm": round(tyre_per_km, 2),
            "insurancePerKm": round(insurance_per_km, 2),
            "depreciationPerKm": round(depreciation_per_km, 2),

            "monthlyFuel": round(monthly_fuel, 2),
            "monthlyService": round(monthly_service, 2),
            "monthlyTyre": round(monthly_tyre, 2),
            "monthlyInsurance": round(monthly_insurance, 2),
            "monthlyDepreciation": round(monthly_depreciation, 2),

            "annualFuel": round(annual_fuel, 2),
            "annualService": round(annual_service, 2),
            "annualTyre": round(annual_tyre, 2),
            "annualInsurance": round(annual_insurance_total, 2),
            "annualDepreciation": round(annual_depreciation_total, 2),

            "fiveYearData": five_year_data,
            "total5YearCost": round(total_5_year_cost, 2),

            "originalCost": round(purchase_price, 2),
            "ageAdjustedCost": round(current_value, 2),
            "current_value": round(current_value, 2),
            "remainingValue": round(final_projection_value, 2),
            "resale_value": round(final_projection_value, 2),
            "fuelTypeDisplay": fuel_type.capitalize(),
            "fuelConsumption": round(efficiency_km_per_l, 2),

            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }
        return result

    def _calculate_fuel_efficiency(self, engine_size: float, year: int,
                                   trip_type: str, fuel_type: str) -> float:
        """Calculate fuel efficiency in km/litre (approximate model —
        smaller engines and eco driving improve efficiency; larger engines,
        aggressive driving, and vehicle age reduce it)."""
        if fuel_type == "electric":
            # Different unit basis (km/kWh) but returned in the same field
            # for simplicity — flag if you need this split out separately.
            base_efficiency = 6.0
        else:
            base_efficiency = max(5.0, 18.0 - (max(engine_size, 1.0) - 1.0) * 3.0)

        trip_multiplier = {
            "urban": 0.85, "highway": 1.15, "mixed": 1.0, "offroad": 0.75
        }.get(trip_type, 1.0)

        current_year = datetime.now(timezone.utc).year
        age = max(0, current_year - year)
        age_multiplier = max(0.85, 1 - 0.01 * age)

        return base_efficiency * trip_multiplier * age_multiplier

    def _get_depreciation_rate(self, age: int, depreciation_rates: Dict[int, float]) -> float:
        """Get depreciation rate based on age, clamped to the table's max key."""
        if not depreciation_rates:
            return 0.03
        max_age_key = max(depreciation_rates.keys())
        lookup_age = min(age, max_age_key)
        return depreciation_rates.get(lookup_age, 0.03)

    def _value_after_years(self, purchase_price: float, years: int,
                            depreciation_rates: Dict[int, float]) -> float:
        """Apply compounding depreciation year-by-year from age 0 to `years`."""
        value = purchase_price
        for age in range(years):
            rate = self._get_depreciation_rate(age, depreciation_rates)
            value *= (1 - rate)
        return max(value, 0.0)

    def _calculate_five_year_data(self, purchase_price: float, request: RunningCostRequest,
                                  fuel_type: str, fuel_price: float,
                                  maintenance_rate: float, tyre_cost_per_km: float,
                                  insurance_rate: float, vehicle_year: int,
                                  engine_size: float,
                                  depreciation_rates: Dict[int, float]) -> list:
        """Calculate year-by-year cost projection for request.years years
        (field name kept as fiveYearData per the response schema, but the
        length follows request.years — default 5)."""
        current_year = datetime.now(timezone.utc).year
        starting_age = max(0, current_year - vehicle_year)

        efficiency_km_per_l = self._calculate_fuel_efficiency(
            engine_size, vehicle_year, request.trip_type, fuel_type
        )
        fuel_cost_per_km = fuel_price / efficiency_km_per_l if efficiency_km_per_l > 0 else 0.0

        years_data = []
        for year_num in range(1, request.years + 1):
            age_at_start = starting_age + year_num - 1
            age_at_end = starting_age + year_num

            value_start = self._value_after_years(purchase_price, age_at_start, depreciation_rates)
            value_end = self._value_after_years(purchase_price, age_at_end, depreciation_rates)
            year_depreciation = max(0.0, value_start - value_end) if request.include_depreciation else 0.0

            year_fuel = fuel_cost_per_km * request.annual_mileage if fuel_cost_per_km else 0.0
            year_service = (
                maintenance_rate * request.annual_mileage if request.include_maintenance else 0.0
            )
            year_tyres = (
                tyre_cost_per_km * request.annual_mileage if request.include_tyres else 0.0
            )
            year_insurance = (
                value_start * insurance_rate if request.include_insurance else 0.0
            )

            running_cost = year_fuel + year_service + year_tyres + year_insurance
            year_total = running_cost + year_depreciation

            years_data.append({
                "year": year_num,
                "fuel": round(year_fuel, 2),
                "service": round(year_service, 2),
                "tyres": round(year_tyres, 2),
                "insurance": round(year_insurance, 2),
                "depreciation": round(year_depreciation, 2),
                "running_cost": round(running_cost, 2),
                "total": round(year_total, 2),
                "value": round(value_end, 2),
            })

        return years_data
