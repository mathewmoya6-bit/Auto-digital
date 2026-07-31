# app/modules/running_cost/service.py
"""Running Cost service for Auto-D Kenya"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import lru_cache

from app.core.database import get_supabase
from app.modules.running_cost.schemas import RunningCostRequest

logger = logging.getLogger(__name__)


class RunningCostService:
    """Service for running cost calculations with full vehicle endpoint integration"""

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
        self._default_tyre_cost_per_set = 48000

        # ─── CACHED CONFIGURATIONS ──────────────────────────────────
        self._config_cache = {}
        self._config_cache_time = None
        self._config_cache_ttl = 300  # 5 minutes

    # ─── CONFIGURATION LOADER ──────────────────────────────────────

    async def _load_config_from_db(self) -> Dict[str, Any]:
        """Load configuration from database with caching"""
        current_time = datetime.utcnow().timestamp()

        if self._config_cache and self._config_cache_time:
            if current_time - self._config_cache_time < self._config_cache_ttl:
                return self._config_cache

        try:
            config = {
                "fuel_prices": {},
                "maintenance_rates": {},
                "insurance_rates": {},
                "depreciation_rates": {},
                "tyre_lifespan_km": self._default_tyre_lifespan_km,
                "tyre_cost_per_set": self._default_tyre_cost_per_set
            }

            # ─── Load fuel prices ──────────────────────────────────
            try:
                fuel_result = self.supabase.table("fuel_prices")\
                    .select("fuel_type, price_per_unit")\
                    .eq("active", True)\
                    .execute()

                if fuel_result.data:
                    for item in fuel_result.data:
                        fuel_type = item.get("fuel_type", "").strip().lower()
                        price = item.get("price_per_unit", 0)
                        if fuel_type and price > 0:
                            config["fuel_prices"][fuel_type] = price
            except Exception as e:
                logger.warning(f"Could not load fuel prices from DB: {e}")

            # ─── Load maintenance rates ────────────────────────────
            try:
                maint_result = self.supabase.table("maintenance_rates")\
                    .select("fuel_type, rate_per_km")\
                    .eq("active", True)\
                    .execute()

                if maint_result.data:
                    for item in maint_result.data:
                        fuel_type = item.get("fuel_type", "").strip().lower()
                        rate = item.get("rate_per_km", 0)
                        if fuel_type and rate > 0:
                            config["maintenance_rates"][fuel_type] = rate
            except Exception as e:
                logger.warning(f"Could not load maintenance rates from DB: {e}")

            # ─── Load insurance rates ──────────────────────────────
            try:
                ins_result = self.supabase.table("insurance_rates")\
                    .select("insurance_type, rate")\
                    .eq("active", True)\
                    .execute()

                if ins_result.data:
                    for item in ins_result.data:
                        ins_type = item.get("insurance_type", "").strip().lower()
                        rate = item.get("rate", 0)
                        if ins_type and rate > 0:
                            config["insurance_rates"][ins_type] = rate
            except Exception as e:
                logger.warning(f"Could not load insurance rates from DB: {e}")

            # ─── Load depreciation rates ────────────────────────────
            try:
                dep_result = self.supabase.table("depreciation_rates")\
                    .select("age_years, rate")\
                    .eq("active", True)\
                    .order("age_years", ascending=True)\
                    .execute()

                if dep_result.data:
                    config["depreciation_rates"] = {}
                    for item in dep_result.data:
                        age = item.get("age_years", 0)
                        rate = item.get("rate", 0)
                        if age >= 0 and rate > 0:
                            config["depreciation_rates"][age] = rate
            except Exception as e:
                logger.warning(f"Could not load depreciation rates from DB: {e}")

            # ─── Load tyre configuration ────────────────────────────
            try:
                tyre_result = self.supabase.table("tyre_config")\
                    .select("config_key, config_value")\
                    .eq("active", True)\
                    .execute()

                if tyre_result.data:
                    for item in tyre_result.data:
                        key = item.get("config_key", "")
                        value = item.get("config_value", 0)
                        if key == "tyre_lifespan_km" and value > 0:
                            config["tyre_lifespan_km"] = value
                        elif key == "tyre_cost_per_set" and value > 0:
                            config["tyre_cost_per_set"] = value
            except Exception as e:
                logger.warning(f"Could not load tyre config from DB: {e}")

            # ─── Fill missing values with defaults ──────────────────
            for fuel_type, price in self._default_fuel_prices.items():
                if fuel_type not in config["fuel_prices"]:
                    config["fuel_prices"][fuel_type] = price

            for fuel_type, rate in self._default_maintenance_rates.items():
                if fuel_type not in config["maintenance_rates"]:
                    config["maintenance_rates"][fuel_type] = rate

            for ins_type, rate in self._default_insurance_rates.items():
                if ins_type not in config["insurance_rates"]:
                    config["insurance_rates"][ins_type] = rate

            if not config["depreciation_rates"]:
                config["depreciation_rates"] = self._default_depreciation_rates

            self._config_cache = config
            self._config_cache_time = current_time

            logger.info(f"Loaded configuration from DB: {len(config['fuel_prices'])} fuel types, "
                       f"{len(config['depreciation_rates'])} depreciation rates")

            return config

        except Exception as e:
            logger.exception(f"Error loading config from DB: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration when DB is unavailable"""
        return {
            "fuel_prices": self._default_fuel_prices.copy(),
            "maintenance_rates": self._default_maintenance_rates.copy(),
            "insurance_rates": self._default_insurance_rates.copy(),
            "depreciation_rates": self._default_depreciation_rates.copy(),
            "tyre_lifespan_km": self._default_tyre_lifespan_km,
            "tyre_cost_per_set": self._default_tyre_cost_per_set
        }

    # ─── VEHICLE ENDPOINT METHODS ──────────────────────────────────

    async def get_makes(self) -> List[Dict[str, Any]]:
        """GET /api/v1/makes - Get all vehicle makes"""
        try:
            # Check cache first
            if "makes" in self._make_cache:
                return self._make_cache["makes"]

            result = self.supabase.table("vehicle_master_specs")\
                .select("make_id, make_name, make_country")\
                .execute()

            # Deduplicate makes
            makes_dict = {}
            if result.data:
                for item in result.data:
                    make_id = item.get("make_id")
                    if make_id and make_id not in makes_dict:
                        makes_dict[make_id] = {
                            "make_id": make_id,
                            "make_name": item.get("make_name", "Unknown"),
                            "make_country": item.get("make_country", "")
                        }

            makes = list(makes_dict.values())
            # Sort by make_name
            makes.sort(key=lambda x: x.get("make_name", ""))

            self._make_cache["makes"] = makes
            return makes
        except Exception as e:
            logger.exception(f"Error getting makes: {e}")
            return []

    async def get_models(self, make_id: int) -> List[Dict[str, Any]]:
        """GET /api/v1/models/{make_id} - Get models by make ID"""
        try:
            cache_key = f"models_{make_id}"
            if cache_key in self._model_cache:
                return self._model_cache[cache_key]

            result = self.supabase.table("vehicle_master_specs")\
                .select("model_id, model_name, model_body_type")\
                .eq("make_id", make_id)\
                .execute()

            # Deduplicate models
            models_dict = {}
            if result.data:
                for item in result.data:
                    model_id = item.get("model_id")
                    if model_id and model_id not in models_dict:
                        models_dict[model_id] = {
                            "model_id": model_id,
                            "model_name": item.get("model_name", "Unknown"),
                            "model_body_type": item.get("model_body_type", "")
                        }

            models = list(models_dict.values())
            models.sort(key=lambda x: x.get("model_name", ""))

            self._model_cache[cache_key] = models
            return models
        except Exception as e:
            logger.exception(f"Error getting models for make {make_id}: {e}")
            return []

    async def get_generations(self, model_id: int) -> List[Dict[str, Any]]:
        """GET /api/v1/generations/{model_id} - Get generations by model ID"""
        try:
            cache_key = f"generations_{model_id}"
            if cache_key in self._generation_cache:
                return self._generation_cache[cache_key]

            result = self.supabase.table("vehicle_master_specs")\
                .select("generation_id, generation_code, generation_start_year, generation_end_year")\
                .eq("model_id", model_id)\
                .execute()

            # Deduplicate generations
            gen_dict = {}
            if result.data:
                for item in result.data:
                    gen_id = item.get("generation_id")
                    if gen_id and gen_id not in gen_dict:
                        gen_dict[gen_id] = {
                            "generation_id": gen_id,
                            "generation_code": item.get("generation_code", ""),
                            "generation_start_year": item.get("generation_start_year"),
                            "generation_end_year": item.get("generation_end_year")
                        }

            generations = list(gen_dict.values())
            generations.sort(key=lambda x: x.get("generation_start_year") or 0, reverse=True)

            self._generation_cache[cache_key] = generations
            return generations
        except Exception as e:
            logger.exception(f"Error getting generations for model {model_id}: {e}")
            return []

    async def get_variants(self, generation_id: int) -> List[Dict[str, Any]]:
        """GET /api/v1/variants/{generation_id} - Get variants by generation ID"""
        try:
            cache_key = f"variants_{generation_id}"
            if cache_key in self._variant_cache:
                return self._variant_cache[cache_key]

            result = self.supabase.table("vehicle_master_specs")\
                .select("*")\
                .eq("generation_id", generation_id)\
                .execute()

            variants = result.data if result.data else []

            # Sort by variant_name
            variants.sort(key=lambda x: x.get("variant_name", ""))

            # Store in cache
            self._variant_cache[cache_key] = variants
            return variants
        except Exception as e:
            logger.exception(f"Error getting variants for generation {generation_id}: {e}")
            return []

    async def get_variant(self, variant_id: int) -> Optional[Dict[str, Any]]:
        """GET /api/v1/variant/{variant_id} - Get variant by ID"""
        try:
            cache_key = f"variant_{variant_id}"
            if cache_key in self._variant_cache:
                return self._variant_cache[cache_key]

            result = self.supabase.table("vehicle_master_specs")\
                .select("*")\
                .eq("variant_id", variant_id)\
                .single()\
                .execute()

            variant = result.data if result.data else None

            if variant:
                self._variant_cache[cache_key] = variant

            return variant
        except Exception as e:
            logger.exception(f"Error getting variant {variant_id}: {e}")
            return None

    async def search_vehicles(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """GET /api/v1/search - Search vehicles by make, model, or variant name"""
        try:
            search_query = f"%{query}%"

            result = self.supabase.table("vehicle_master_specs")\
                .select("*")\
                .or_(
                    f"make_name.ilike.{search_query},"
                    f"model_name.ilike.{search_query},"
                    f"variant_name.ilike.{search_query}"
                )\
                .limit(limit)\
                .execute()

            return result.data if result.data else []
        except Exception as e:
            logger.exception(f"Error searching vehicles for '{query}': {e}")
            return []

    # ─── VARIANT DATA (with full hierarchy) ────────────────────────

    async def get_variant_with_details(self, variant_id: int) -> Optional[Dict[str, Any]]:
        """Get variant with full hierarchy (make, model, generation details)"""
        try:
            result = self.supabase.table("vehicle_master_specs")\
                .select("*")\
                .eq("variant_id", variant_id)\
                .single()\
                .execute()

            if not result.data:
                return None

            variant = result.data

            # Add hierarchy info
            variant["hierarchy"] = {
                "make": variant.get("make_name"),
                "make_id": variant.get("make_id"),
                "model": variant.get("model_name"),
                "model_id": variant.get("model_id"),
                "generation": variant.get("generation_code"),
                "generation_id": variant.get("generation_id")
            }

            return variant
        except Exception as e:
            logger.exception(f"Error getting variant with details for {variant_id}: {e}")
            return None

    # ─── MAIN CALCULATION ───────────────────────────────────────────

    async def calculate_running_cost(self, request: RunningCostRequest, user_id: int) -> Dict[str, Any]:
        """Calculate running costs with full vehicle data"""
        current_year = datetime.now().year

        # ─── Load configuration from DB ──────────────────────────────
        config = await self._load_config_from_db()

        # ─── Validations ─────────────────────────────────────────────
        if request.year < 1900 or request.year > current_year + 1:
            raise ValueError(f"Invalid year: {request.year}")

        if request.distance <= 0:
            raise ValueError("Distance must be greater than 0")

        if request.annual_mileage <= 0:
            raise ValueError("Annual mileage must be greater than 0")

        # ─── Get variant data with full hierarchy ──────────────────
        variant = await self.get_variant_with_details(request.variant_id)
        if not variant:
            raise ValueError(f"Variant with ID {request.variant_id} not found")

        # ─── Fuel type normalization ────────────────────────────────
        fuel_type = (
            variant.get("fuel_type_name") or "petrol"
        ).strip().lower()

        fuel_type_map = {
            "petrol": "petrol",
            "gasoline": "petrol",
            "diesel": "diesel",
            "electric": "electric",
            "ev": "electric",
            "hybrid": "hybrid",
            "lpg": "lpg",
            "cng": "cng",
            "gas": "gas"
        }
        fuel_type = fuel_type_map.get(fuel_type, fuel_type)

        if fuel_type not in config["fuel_prices"]:
            fuel_type = "petrol"
            logger.warning(f"Unknown fuel type, using default: {fuel_type}")

        # ─── Vehicle details ────────────────────────────────────────
        engine_size = variant.get("engine_size_cc", 1800) / 1000
        if engine_size <= 0:
            engine_size = 1.8
            logger.warning(f"Invalid engine size, using default: 1.8L")

        vehicle_year = request.year or variant.get("generation_start_year", 2020)
        vehicle_age = max(0, current_year - vehicle_year)

        purchase_price = variant.get("purchase_price") or 2500000
        if purchase_price <= 0:
            purchase_price = 2500000
            logger.warning(f"Invalid purchase price, using default: {purchase_price}")

        initial_vehicle_cost = purchase_price

        # ─── Fuel price ──────────────────────────────────────────────
        fuel_price = request.fuel_price or config["fuel_prices"].get(fuel_type, 193.00)
        if fuel_price <= 0:
            fuel_price = 193.00
            logger.warning(f"Invalid fuel price, using default: {fuel_price}")

        # ─── Fuel efficiency ─────────────────────────────────────────
        fuel_efficiency = self._calculate_fuel_efficiency(
            engine_size, vehicle_year, request.trip_type, fuel_type
        )
        if fuel_efficiency <= 0:
            fuel_efficiency = 10.0
            logger.warning(f"Invalid fuel efficiency, using default: {fuel_efficiency}")

        # ─── Calculate costs ─────────────────────────────────────────
        # Fuel cost
        fuel_cost_per_km = fuel_price / fuel_efficiency
        fuel_cost_trip = fuel_cost_per_km * request.distance

        # Maintenance cost
        maintenance_rate = config["maintenance_rates"].get(fuel_type, 2.50)
        age_factor = 1 + (vehicle_age * 0.05)
        maintenance_cost_per_km = maintenance_rate * age_factor
        maintenance_cost_trip = maintenance_cost_per_km * request.distance

        # Tyre cost
        tyre_cost_per_km = config["tyre_cost_per_set"] / config["tyre_lifespan_km"]
        tyre_cost_trip = tyre_cost_per_km * request.distance

        # Insurance cost
        insurance_type = getattr(request, 'insurance_type', 'comprehensive')
        insurance_rate = config["insurance_rates"].get(
            insurance_type,
            config["insurance_rates"].get("comprehensive", 0.04)
        )
        annual_insurance = purchase_price * insurance_rate
        insurance_per_km = annual_insurance / request.annual_mileage
        insurance_cost_trip = insurance_per_km * request.distance

        # Depreciation
        depreciation_rate = self._get_depreciation_rate(vehicle_age, config["depreciation_rates"])

        # Compound depreciation
        remaining_value = initial_vehicle_cost
        for _ in range(min(vehicle_age, 15)):
            remaining_value *= (1 - depreciation_rate)

        remaining_value = max(remaining_value, initial_vehicle_cost * 0.15)
        resale_value = remaining_value
        annual_depreciation = initial_vehicle_cost - remaining_value
        depreciation_per_km = annual_depreciation / request.annual_mileage
        depreciation_cost_trip = depreciation_per_km * request.distance

        # Total costs
        total_cost_per_km = (
            fuel_cost_per_km + maintenance_cost_per_km +
            tyre_cost_per_km + insurance_per_km + depreciation_per_km
        )
        total_cost_trip = total_cost_per_km * request.distance

        # Monthly and annual costs
        monthly_mileage = request.annual_mileage / 12
        monthly_fuel = fuel_cost_per_km * monthly_mileage
        monthly_service = maintenance_cost_per_km * monthly_mileage
        monthly_tyre = tyre_cost_per_km * monthly_mileage
        monthly_insurance = annual_insurance / 12
        monthly_depreciation = annual_depreciation / 12

        # 5-year projection
        five_year_data = self._calculate_five_year_data(
            initial_vehicle_cost,
            request,
            fuel_type,
            fuel_price,
            maintenance_rate,
            tyre_cost_per_km,
            insurance_rate,
            vehicle_year,
            engine_size,
            config["depreciation_rates"]
        )

        # ─── Build response with full vehicle info ──────────────────
        try:
            response = {
                # ─── Trip Summary ────────────────────────────────────
                "tripTotal": round(total_cost_trip, 2),
                "tripCostPerKm": round(total_cost_per_km, 2),
                "distance": request.distance,

                # ─── Trip Cost Breakdown ─────────────────────────────
                "fuelCostTrip": round(fuel_cost_trip, 2),
                "serviceTrip": round(maintenance_cost_trip, 2),
                "tyreTrip": round(tyre_cost_trip, 2),
                "insuranceTrip": round(insurance_cost_trip, 2),
                "depreciationTrip": round(depreciation_cost_trip, 2),

                # ─── Per KM Costs ────────────────────────────────────
                "fuelCostPerKm": round(fuel_cost_per_km, 2),
                "servicePerKm": round(maintenance_cost_per_km, 2),
                "tyrePerKm": round(tyre_cost_per_km, 2),
                "insurancePerKm": round(insurance_per_km, 2),
                "depreciationPerKm": round(depreciation_per_km, 2),

                # ─── Monthly Costs ───────────────────────────────────
                "monthlyFuel": round(monthly_fuel, 2),
                "monthlyService": round(monthly_service, 2),
                "monthlyTyre": round(monthly_tyre, 2),
                "monthlyInsurance": round(monthly_insurance, 2),
                "monthlyDepreciation": round(monthly_depreciation, 2),

                # ─── Annual Costs ────────────────────────────────────
                "annualFuel": round(monthly_fuel * 12, 2),
                "annualService": round(monthly_service * 12, 2),
                "annualTyre": round(monthly_tyre * 12, 2),
                "annualInsurance": round(annual_insurance, 2),
                "annualDepreciation": round(monthly_depreciation * 12, 2),

                # ─── 5-Year Projection ──────────────────────────────
                "fiveYearData": five_year_data,
                "total5YearCost": round(sum(y["total"] for y in five_year_data), 2),

                # ─── Vehicle Info ────────────────────────────────────
                "originalCost": round(initial_vehicle_cost, 2),
                "ageAdjustedCost": round(remaining_value, 2),
                "current_value": round(remaining_value, 2),
                "remainingValue": round(resale_value, 2),
                "resale_value": round(resale_value, 2),
                "fuelTypeDisplay": fuel_type.capitalize(),
                "fuelConsumption": round(fuel_efficiency, 1),

                # ─── Full Vehicle Hierarchy ──────────────────────────
                "vehicle_hierarchy": {
                    "make": variant.get("make_name"),
                    "make_id": variant.get("make_id"),
                    "model": variant.get("model_name"),
                    "model_id": variant.get("model_id"),
                    "generation": variant.get("generation_code"),
                    "generation_id": variant.get("generation_id"),
                    "variant_id": variant.get("variant_id"),
                    "variant_name": variant.get("variant_name"),
                    "engine_size_cc": variant.get("engine_size_cc"),
                    "fuel_type": variant.get("fuel_type_name"),
                    "transmission": variant.get("transmission_type_name"),
                    "drive_type": variant.get("drive_type_name"),
                    "body_type": variant.get("body_type_name"),
                    "seats": variant.get("seats"),
                    "doors": variant.get("doors"),
                    "power_hp": variant.get("power_hp"),
                    "torque_nm": variant.get("torque_nm"),
                    "fuel_consumption_combined": variant.get("fuel_consumption_combined"),
                    "co2_emissions": variant.get("co2_emissions")
                },

                # ─── New structured response ────────────────────────
                "trip": {
                    "distance": request.distance,
                    "running_cost": round(total_cost_trip, 2),
                    "cost_per_km": round(total_cost_per_km, 2)
                },
                "costs": {
                    "fuel": round(fuel_cost_trip, 2),
                    "service": round(maintenance_cost_trip, 2),
                    "tyres": round(tyre_cost_trip, 2),
                    "insurance": round(insurance_cost_trip, 2),
                    "depreciation": round(depreciation_cost_trip, 2)
                },
                "per_km": {
                    "fuel": round(fuel_cost_per_km, 2),
                    "service": round(maintenance_cost_per_km, 2),
                    "tyres": round(tyre_cost_per_km, 2),
                    "insurance": round(insurance_per_km, 2),
                    "depreciation": round(depreciation_per_km, 2)
                },
                "monthly": {
                    "fuel": round(monthly_fuel, 2),
                    "service": round(monthly_service, 2),
                    "tyres": round(monthly_tyre, 2),
                    "insurance": round(monthly_insurance, 2),
                    "depreciation": round(monthly_depreciation, 2),
                    "total": round(
                        monthly_fuel + monthly_service + monthly_tyre +
                        monthly_insurance + monthly_depreciation, 2
                    )
                },
                "annual": {
                    "fuel": round(monthly_fuel * 12, 2),
                    "service": round(monthly_service * 12, 2),
                    "tyres": round(monthly_tyre * 12, 2),
                    "insurance": round(annual_insurance, 2),
                    "depreciation": round(monthly_depreciation * 12, 2),
                    "total": round(
                        (monthly_fuel + monthly_service + monthly_tyre +
                         monthly_insurance + monthly_depreciation) * 12, 2
                    )
                },
                "projection": {
                    "years": five_year_data,
                    "total_5_year_cost": round(
                        sum(y["total"] for y in five_year_data), 2
                    ),
                    "total_5_year_running_cost": round(
                        sum(y["running_cost"] for y in five_year_data), 2
                    )
                },
                "vehicle": {
                    "initial_vehicle_cost": round(initial_vehicle_cost, 2),
                    "purchase_price": round(initial_vehicle_cost, 2),
                    "current_value": round(remaining_value, 2),
                    "resale_value": round(resale_value, 2),
                    "depreciation_rate": round(depreciation_rate, 3),
                    "fuel_type": fuel_type.capitalize(),
                    "fuel_efficiency": round(fuel_efficiency, 1),
                    "engine_size": round(engine_size, 1),
                    "year": vehicle_year,
                    "age": vehicle_age
                },
                "calculated_at": datetime.utcnow().isoformat()
            }

            return response

        except Exception as e:
            logger.exception(f"Running cost calculation failed: {str(e)}")
            raise

    def _calculate_fuel_efficiency(self, engine_size: float, year: int,
                                   trip_type: str, fuel_type: str) -> float:
        """Calculate fuel efficiency in km/litre"""
        base_efficiency = {
            "petrol": 12.0,
            "diesel": 14.0,
            "electric": 6.0,
            "hybrid": 18.0,
            "gas": 11.0,
            "lpg": 11.0,
            "cng": 10.0
        }

        efficiency = base_efficiency.get(fuel_type, 12.0)
        efficiency -= max(0, (engine_size - 1.5) * 1.5)

        age = datetime.now().year - year
        year_factor = max(0.75, 1 - age * 0.01)
        efficiency *= year_factor

        pattern_factors = {
            "urban": 0.8,
            "highway": 1.2,
            "mixed": 1.0,
            "offroad": 0.7
        }
        efficiency *= pattern_factors.get(trip_type, 1.0)

        return max(efficiency, 5.0)

    def _get_depreciation_rate(self, age: int, depreciation_rates: Dict[int, float]) -> float:
        """Get depreciation rate based on age"""
        clamped_age = min(age, 15)
        return depreciation_rates.get(
            clamped_age,
            depreciation_rates.get(15, 0.02)
        )

    def _calculate_five_year_data(self, purchase_price: float, request: RunningCostRequest,
                                  fuel_type: str, fuel_price: float,
                                  maintenance_rate: float, tyre_cost_per_km: float,
                                  insurance_rate: float, vehicle_year: int,
                                  engine_size: float,
                                  depreciation_rates: Dict[int, float]) -> list:
        """Calculate 5-year cost projection"""
        data = []
        current_value = purchase_price
        current_year = datetime.now().year

        for year in range(1, request.years + 1):
            age = (current_year - vehicle_year) + (year - 1)
            annual_mileage = request.annual_mileage

            fuel_efficiency = self._calculate_fuel_efficiency(
                engine_size, vehicle_year + year - 1, request.trip_type, fuel_type
            )

            fuel_cost = (annual_mileage / max(fuel_efficiency, 0.1)) * fuel_price
            service_cost = maintenance_rate * annual_mileage * (1 + (age * 0.03))
            tyre_cost = tyre_cost_per_km * annual_mileage
            insurance_cost = purchase_price * insurance_rate * (1 - min(age * 0.02, 0.4))

            dep_rate = self._get_depreciation_rate(age, depreciation_rates)
            depreciation = current_value * dep_rate
            current_value -= depreciation

            running_cost = fuel_cost + service_cost + tyre_cost + insurance_cost + depreciation
            total = running_cost

            data.append({
                "year": year,
                "fuel": round(fuel_cost, 2),
                "service": round(service_cost, 2),
                "tyres": round(tyre_cost, 2),
                "insurance": round(insurance_cost, 2),
                "depreciation": round(depreciation, 2),
                "running_cost": round(running_cost, 2),
                "total": round(total, 2),
                "value": round(max(current_value, purchase_price * 0.15), 2)
            })

        return data
