# app/modules/running_cost/service.py
"""Running Cost service for Auto-D Kenya"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.database import get_supabase
from app.modules.running_cost.schemas import RunningCostRequest

logger = logging.getLogger(__name__)


class RunningCostService:
    """Service for running cost calculations"""

    def __init__(self):
        self.supabase = get_supabase()
        self._variant_cache = {}

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

    # ─── VARIANT DATA ──────────────────────────────────────────────

    async def _get_variant_data_cached(self, variant_id: int) -> Dict[str, Any]:
        """Get variant data from database with manual caching"""
        if variant_id in self._variant_cache:
            return self._variant_cache[variant_id]

        try:
            result = self.supabase.table("vehicle_master_specs")\
                .select("*")\
                .eq("variant_id", variant_id)\
                .single()\
                .execute()

            if result.data:
                self._variant_cache[variant_id] = result.data
                return result.data
            return {}
        except Exception as e:
            logger.exception(f"Error getting variant data for ID {variant_id}: {str(e)}")
            return {}

    async def get_variant_data(self, variant_id: int) -> Dict[str, Any]:
        """Get variant data from cache or database"""
        return await self._get_variant_data_cached(variant_id)

    # ─── CRSP PRICE LOOKUP ──────────────────────────────────────────
    # CRITICAL: This is the authoritative source for the original vehicle price
    # The frontend variant_id maps to vehicle_crsp_prices.engine_capacity_id

    async def _get_crsp_price(self, variant_id: int) -> Dict[str, Any]:
        """
        Get the authoritative original vehicle price from vehicle_crsp_prices.

        IMPORTANT:
        variant_id from the frontend is the engine_capacity_id used by
        vehicle_crsp_prices in the current vehicle-selection flow.

        Returns:
            Dict containing the CRSP record or empty dict if not found
        """
        try:
            logger.info(f"🔍 Looking up CRSP for engine_capacity_id: {variant_id}")

            response = (
                self.supabase
                .table("vehicle_crsp_prices")
                .select("""
                    id,
                    make,
                    model,
                    model_number,
                    transmission,
                    drive_configuration,
                    engine_capacity,
                    body_type,
                    gvw,
                    seating,
                    fuel,
                    crsp_kes,
                    crsp_year,
                    currency,
                    source,
                    effective_date,
                    make_id,
                    model_id,
                    generation_id,
                    engine_capacity_id,
                    manufacture_year
                """)
                .eq("engine_capacity_id", variant_id)
                .order("effective_date", desc=True)
                .order("crsp_year", desc=True)
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.warning(
                    "❌ No CRSP price found for engine_capacity_id=%s",
                    variant_id
                )
                return {}

            crsp = response.data[0]
            price = crsp.get("crsp_kes")

            if price is None or float(price) <= 0:
                logger.warning(
                    "⚠️ CRSP record found but crsp_kes is invalid: %s",
                    crsp
                )
                return {}

            logger.info(
                "✅ CRSP record found: %s %s - KES %s",
                crsp.get("make", ""),
                crsp.get("model", ""),
                price
            )

            return crsp

        except Exception as exc:
            logger.exception(
                "❌ CRSP lookup failed for variant_id=%s: %s",
                variant_id,
                exc
            )
            return {}

    # ─── MAIN CALCULATION ───────────────────────────────────────────

    async def calculate_running_cost(self, request: RunningCostRequest, user_id: int) -> Dict[str, Any]:
        """
        Calculate running costs.

        FLOW:
        1. Resolve CRSP price from vehicle_crsp_prices (authoritative)
        2. Get variant details from vehicle_master_specs
        3. Calculate all costs using CRSP as the starting price
        4. Return comprehensive response
        """
        current_year = datetime.now().year
        logger.info(f"📊 Starting running cost calculation for variant_id: {request.variant_id}")

        # ─── Validations ─────────────────────────────────────────────
        if request.year < 1900 or request.year > current_year + 1:
            raise ValueError(f"Invalid year: {request.year}")

        if request.distance <= 0:
            raise ValueError("Distance must be greater than 0")

        if request.annual_mileage <= 0:
            raise ValueError("Annual mileage must be greater than 0")

        # ─── STEP 1: Resolve CRSP price (authoritative) ─────────────
        crsp_record = await self._get_crsp_price(request.variant_id)
        
        crsp_price = None
        crsp_data = {}
        
        if crsp_record:
            crsp_price = float(crsp_record["crsp_kes"])
            crsp_data = {
                "make": crsp_record.get("make", ""),
                "model": crsp_record.get("model", ""),
                "engine_capacity": crsp_record.get("engine_capacity", ""),
                "fuel": crsp_record.get("fuel", ""),
                "transmission": crsp_record.get("transmission", ""),
                "body_type": crsp_record.get("body_type", ""),
                "crsp_year": crsp_record.get("crsp_year"),
                "manufacture_year": crsp_record.get("manufacture_year"),
                "currency": crsp_record.get("currency", "KES")
            }
            logger.info(f"💰 CRSP price resolved: KES {crsp_price}")
        else:
            logger.warning(f"⚠️ No CRSP record found for variant_id: {request.variant_id}")

        # ─── STEP 2: Get variant data ──────────────────────────────
        variant = await self.get_variant_data(request.variant_id)
        if not variant:
            raise ValueError(f"Variant with ID {request.variant_id} not found")

        logger.info(f"📊 Variant: {variant.get('make_name')} {variant.get('model_name')}")

        # ─── STEP 3: Determine the authoritative original price ────
        # CRITICAL: CRSP is the authoritative source. Only use fallback if CRSP fails.
        if crsp_price is not None and crsp_price > 0:
            purchase_price = crsp_price
            original_price_source = "CRSP"
            logger.info(f"💰 Using CRSP price as original: KES {purchase_price}")
        else:
            # Fallback only when CRSP is unavailable
            # Try variant market_value, then insurance_value, then forced_sale_value
            purchase_price = (
                variant.get("market_value") or
                variant.get("insurance_value") or
                variant.get("forced_sale_value") or
                variant.get("trade_in_value") or
                None
            )
            if purchase_price:
                purchase_price = float(purchase_price)
                original_price_source = "Variant DB"
                logger.info(f"💰 Using variant market value: KES {purchase_price}")
            else:
                # Final fallback - but this should rarely happen
                purchase_price = 2500000.0
                original_price_source = "Fallback (2.5M)"
                logger.warning(f"⚠️ No CRSP or variant price found. Using fallback: KES {purchase_price}")

        logger.info(f"📊 Original price source: {original_price_source}, value: {purchase_price}")

        # ─── Load configuration from DB ──────────────────────────────
        config = await self._load_config_from_db()

        # ─── Fuel type normalization ────────────────────────────────
        fuel_type = (variant.get("fuel_type_name") or "petrol").strip().lower()
        fuel_type_map = {
            "petrol": "petrol", "gasoline": "petrol", "diesel": "diesel",
            "electric": "electric", "ev": "electric", "hybrid": "hybrid",
            "lpg": "lpg", "cng": "cng", "gas": "gas"
        }
        fuel_type = fuel_type_map.get(fuel_type, fuel_type)

        if fuel_type not in config["fuel_prices"]:
            fuel_type = "petrol"
            logger.warning(f"Unknown fuel type, using default: {fuel_type}")

        # ─── Vehicle details from variant ────────────────────────────
        engine_size = variant.get("engine_size_cc", 1800) / 1000
        if engine_size <= 0:
            engine_size = 1.8

        vehicle_year = request.year or variant.get("generation_start_year", 2020)
        vehicle_age = max(0, current_year - vehicle_year)

        # ─── INSURANCE VALUE from variant ────────────────────────────
        # Use insurance_value from variant, or fallback to purchase_price
        insurance_value = variant.get("insurance_value") or purchase_price
        insured_value = float(insurance_value)
        logger.info(f"📊 Insurance value: {insured_value}")

        # ─── FUEL CONSUMPTION from variant ──────────────────────────
        fuel_efficiency = variant.get("fuel_consumption_combined")
        if fuel_efficiency and fuel_efficiency > 0:
            fuel_efficiency = float(fuel_efficiency)
            logger.info(f"📊 Fuel consumption from DB: {fuel_efficiency} km/L")
        else:
            # Fallback calculation if NULL
            fuel_efficiency = self._calculate_fuel_efficiency(
                engine_size, vehicle_year, request.trip_type, fuel_type
            )
            if fuel_efficiency <= 0:
                fuel_efficiency = 10.0
            logger.info(f"📊 Fuel consumption calculated: {fuel_efficiency} km/L")

        # ─── Fuel price from DB ──────────────────────────────────────
        fuel_price = request.fuel_price or config["fuel_prices"].get(fuel_type, 193.00)
        if fuel_price <= 0:
            fuel_price = 193.00
        logger.info(f"📊 Fuel price: {fuel_price} KES/L")

        # ─── Driving factors ────────────────────────────────────────
        driving_style = getattr(request, 'driving_style', 'normal')
        trip_type = getattr(request, 'trip_type', 'mixed')
        usage_type = getattr(request, 'usage_type', 'private')
        condition = getattr(request, 'condition', 'good')
        location = getattr(request, 'location', 'urban')

        driving_factor = self._calculate_driving_factor(
            driving_style, trip_type, usage_type, condition, location
        )
        logger.info(f"📊 Driving factor: {driving_factor}")

        # ─── Inclusion flags ──────────────────────────────────────────
        include_insurance = getattr(request, 'include_insurance', True)
        include_tyres = getattr(request, 'include_tyres', True)
        include_maintenance = getattr(request, 'include_maintenance', True)
        include_depreciation = getattr(request, 'include_depreciation', True)

        # ─── Calculate costs ─────────────────────────────────────────

        # Fuel cost
        fuel_cost_per_km = (fuel_price / fuel_efficiency) * driving_factor
        fuel_cost_trip = fuel_cost_per_km * request.distance
        logger.info(f"📊 Fuel cost per km: {fuel_cost_per_km}, trip: {fuel_cost_trip}")

        # Maintenance cost
        maintenance_rate = config["maintenance_rates"].get(fuel_type, 2.50)
        age_factor = 1 + (vehicle_age * 0.05)
        maintenance_cost_per_km = maintenance_rate * age_factor * driving_factor
        maintenance_cost_trip = maintenance_cost_per_km * request.distance
        logger.info(f"📊 Maintenance per km: {maintenance_cost_per_km}")

        # Tyre cost
        tyre_cost_per_km = config["tyre_cost_per_set"] / config["tyre_lifespan_km"]
        tyre_cost_trip = tyre_cost_per_km * request.distance
        logger.info(f"📊 Tyre cost per km: {tyre_cost_per_km}")

        # Insurance cost (using insurance_value instead of purchase_price)
        insurance_type = getattr(request, 'insurance_type', 'comprehensive')
        insurance_rate = config["insurance_rates"].get(
            insurance_type, config["insurance_rates"].get("comprehensive", 0.04)
        )
        annual_insurance = insured_value * insurance_rate
        insurance_per_km = annual_insurance / max(request.annual_mileage, 1)
        insurance_cost_trip = insurance_per_km * request.distance
        logger.info(f"📊 Insurance rate: {insurance_rate}, annual: {annual_insurance}, per km: {insurance_per_km}")

        # ─── Yearly depreciation ──────────────────────────────────────
        total_depreciation = 0
        remaining_value = purchase_price  # Start with CRSP or variant price
        yearly_depreciation_data = []
        
        # Use current vehicle age as starting point
        age = vehicle_age
        for year in range(1, request.years + 1):
            dep_rate = self._get_depreciation_rate(age, config["depreciation_rates"])
            depreciation_amount = remaining_value * dep_rate
            total_depreciation += depreciation_amount
            remaining_value -= depreciation_amount
            yearly_depreciation_data.append({
                "year": year,
                "age": age,
                "rate": dep_rate,
                "amount": depreciation_amount,
                "remaining_value": max(remaining_value, purchase_price * 0.15)
            })
            age += 1
            
            if remaining_value <= purchase_price * 0.15:
                break

        remaining_value = max(remaining_value, purchase_price * 0.15)
        resale_value = remaining_value
        annual_depreciation = total_depreciation / max(request.years, 1)
        depreciation_per_km = annual_depreciation / max(request.annual_mileage, 1)
        depreciation_cost_trip = depreciation_per_km * request.distance
        logger.info(f"📊 Depreciation: total={total_depreciation}, remaining={remaining_value}")

        # ─── Apply inclusion flags ──────────────────────────────────
        if not include_insurance:
            insurance_cost_trip = 0
            insurance_per_km = 0
            annual_insurance = 0
        
        if not include_tyres:
            tyre_cost_trip = 0
            tyre_cost_per_km = 0
        
        if not include_maintenance:
            maintenance_cost_trip = 0
            maintenance_cost_per_km = 0
        
        if not include_depreciation:
            depreciation_cost_trip = 0
            depreciation_per_km = 0
            annual_depreciation = 0

        # ─── Finance calculation ──────────────────────────────────────
        financed = getattr(request, 'financed', False)
        interest_rate = getattr(request, 'interest_rate', 14.0) / 100
        loan_term = getattr(request, 'loan_term', 48)
        down_payment = getattr(request, 'down_payment', 0.2)

        finance_data = {}
        if financed:
            loan_amount = purchase_price * (1 - down_payment)
            monthly_interest_rate = interest_rate / 12
            if monthly_interest_rate > 0:
                monthly_payment = loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate) ** loan_term) / \
                                 ((1 + monthly_interest_rate) ** loan_term - 1)
            else:
                monthly_payment = loan_amount / loan_term
            
            total_interest = (monthly_payment * loan_term) - loan_amount
            
            finance_data = {
                "financed": True,
                "loan_amount": round(loan_amount, 2),
                "down_payment": round(purchase_price * down_payment, 2),
                "interest_rate": round(interest_rate * 100, 2),
                "loan_term": loan_term,
                "monthly_payment": round(monthly_payment, 2),
                "total_interest": round(total_interest, 2),
                "total_cost": round(monthly_payment * loan_term, 2)
            }

        # ─── Total costs ──────────────────────────────────────────────
        total_cost_per_km = (
            fuel_cost_per_km + maintenance_cost_per_km +
            tyre_cost_per_km + insurance_per_km + depreciation_per_km
        )
        total_cost_trip = total_cost_per_km * request.distance
        logger.info(f"📊 Total cost per km: {total_cost_per_km}, trip: {total_cost_trip}")

        # Monthly and annual costs
        monthly_mileage = request.annual_mileage / 12
        monthly_fuel = fuel_cost_per_km * monthly_mileage
        monthly_service = maintenance_cost_per_km * monthly_mileage
        monthly_tyre = tyre_cost_per_km * monthly_mileage
        monthly_insurance = annual_insurance / 12
        monthly_depreciation = annual_depreciation / 12

        # 5-year projection
        five_year_data = self._calculate_five_year_data(
            purchase_price,
            request,
            fuel_type,
            fuel_price,
            maintenance_rate,
            tyre_cost_per_km,
            insurance_rate,
            vehicle_year,
            engine_size,
            config["depreciation_rates"],
            driving_factor,
            include_insurance,
            include_tyres,
            include_maintenance,
            include_depreciation,
            insured_value
        )

        # ─── Build response ──────────────────────────────────────────
        try:
            response = {
                # ─── Trip Summary ─────────────────────────────────────
                "tripTotal": round(total_cost_trip, 2),
                "tripCostPerKm": round(total_cost_per_km, 2),
                "fuelCostTrip": round(fuel_cost_trip, 2),
                "serviceTrip": round(maintenance_cost_trip, 2),
                "tyreTrip": round(tyre_cost_trip, 2),
                "insuranceTrip": round(insurance_cost_trip, 2),
                "depreciationTrip": round(depreciation_cost_trip, 2),

                # ─── Per KM ──────────────────────────────────────────
                "fuelCostPerKm": round(fuel_cost_per_km, 2),
                "servicePerKm": round(maintenance_cost_per_km, 2),
                "tyrePerKm": round(tyre_cost_per_km, 2),
                "insurancePerKm": round(insurance_per_km, 2),
                "depreciationPerKm": round(depreciation_per_km, 2),

                # ─── Monthly ─────────────────────────────────────────
                "monthlyFuel": round(monthly_fuel, 2),
                "monthlyService": round(monthly_service, 2),
                "monthlyTyre": round(monthly_tyre, 2),
                "monthlyInsurance": round(monthly_insurance, 2),
                "monthlyDepreciation": round(monthly_depreciation, 2),

                # ─── Annual ──────────────────────────────────────────
                "annualFuel": round(monthly_fuel * 12, 2),
                "annualService": round(monthly_service * 12, 2),
                "annualTyre": round(monthly_tyre * 12, 2),
                "annualInsurance": round(annual_insurance, 2),
                "annualDepreciation": round(monthly_depreciation * 12, 2),

                # ─── Legacy fields ────────────────────────────────────
                "distance": request.distance,
                "cost_per_km": round(total_cost_per_km, 2),
                "fuel_cost": round(fuel_cost_trip, 2),
                "service_cost": round(maintenance_cost_trip, 2),
                "tyre_cost": round(tyre_cost_trip, 2),
                "insurance_cost": round(insurance_cost_trip, 2),
                "depreciation_cost": round(depreciation_cost_trip, 2),
                "purchase_price": round(purchase_price, 2),
                "market_value": round(purchase_price, 2),
                "insurance_value": round(insured_value, 2),
                "current_value": round(remaining_value, 2),
                "resale_value": round(resale_value, 2),
                "fuel_type": fuel_type.capitalize(),
                "fuel_consumption": round(fuel_efficiency, 1),
                "fiveYearData": five_year_data,
                "five_year_total": round(sum(y["total"] for y in five_year_data), 2),

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
                    "total": round(monthly_fuel + monthly_service + monthly_tyre + monthly_insurance + monthly_depreciation, 2)
                },
                "annual": {
                    "fuel": round(monthly_fuel * 12, 2),
                    "service": round(monthly_service * 12, 2),
                    "tyres": round(monthly_tyre * 12, 2),
                    "insurance": round(annual_insurance, 2),
                    "depreciation": round(monthly_depreciation * 12, 2),
                    "total": round((monthly_fuel + monthly_service + monthly_tyre + monthly_insurance + monthly_depreciation) * 12, 2)
                },
                "projection": {
                    "years": five_year_data,
                    "total_5_year_cost": round(sum(y["total"] for y in five_year_data), 2),
                    "total_5_year_running_cost": round(sum(y["running_cost"] for y in five_year_data), 2)
                },
                "vehicle": {
                    "initial_vehicle_cost": round(purchase_price, 2),
                    "purchase_price": round(purchase_price, 2),
                    "market_value": round(purchase_price, 2),
                    "insurance_value": round(insured_value, 2),
                    "current_value": round(remaining_value, 2),
                    "resale_value": round(resale_value, 2),
                    "depreciation_rate": round(self._get_depreciation_rate(vehicle_age, config["depreciation_rates"]), 3),
                    "fuel_type": fuel_type.capitalize(),
                    "fuel_efficiency": round(fuel_efficiency, 1),
                    "engine_size": round(engine_size, 1),
                    "year": vehicle_year,
                    "age": vehicle_age,
                    "category": variant.get("category_name", ""),
                    "body_type": variant.get("body_type_name", ""),
                    "trim_level": variant.get("trim_level", ""),
                    "power_hp": variant.get("power_hp", 0),
                    "transmission": variant.get("transmission_type_name", ""),
                    "drive_type": variant.get("drive_type_name", "")
                },
                "calculated_at": datetime.utcnow().isoformat(),
                "finance": finance_data,
                "options": {
                    "include_insurance": include_insurance,
                    "include_tyres": include_tyres,
                    "include_maintenance": include_maintenance,
                    "include_depreciation": include_depreciation,
                    "financed": financed
                },
                "driving_factors": {
                    "driving_style": driving_style,
                    "trip_type": trip_type,
                    "usage_type": usage_type,
                    "condition": condition,
                    "location": location,
                    "factor": round(driving_factor, 2)
                },
                "depreciation_breakdown": yearly_depreciation_data,
                "total5YearCost": round(sum(y["total"] for y in five_year_data), 2),
                "originalCost": round(purchase_price, 2),
                "ageAdjustedCost": round(remaining_value, 2),
                "remainingValue": round(resale_value, 2),
                "fuelTypeDisplay": fuel_type.capitalize(),
                "fuelConsumption": round(fuel_efficiency, 1),

                # ─── CRSP Data ──────────────────────────────────────
                "crsp": {
                    "found": bool(crsp_record),
                    "price": round(crsp_price, 2) if crsp_price else None,
                    "make": crsp_data.get("make", ""),
                    "model": crsp_data.get("model", ""),
                    "engine_capacity": crsp_data.get("engine_capacity", ""),
                    "fuel": crsp_data.get("fuel", ""),
                    "transmission": crsp_data.get("transmission", ""),
                    "body_type": crsp_data.get("body_type", ""),
                    "crsp_year": crsp_data.get("crsp_year"),
                    "manufacture_year": crsp_data.get("manufacture_year"),
                    "currency": crsp_data.get("currency", "KES"),
                    "price_source": original_price_source
                }
            }

            logger.info(
                f"✅ Running cost calculated: tripTotal={total_cost_trip}, "
                f"costPerKm={total_cost_per_km}, originalPrice={purchase_price} (source: {original_price_source})"
            )
            return response

        except Exception as e:
            logger.exception(f"Running cost calculation failed: {str(e)}")
            raise

    def _calculate_driving_factor(self, driving_style: str, trip_type: str, 
                                  usage_type: str, condition: str, location: str) -> float:
        """Calculate driving factor multiplier based on driving conditions"""
        factor = 1.0
        
        style_factors = {"economical": 0.85, "normal": 1.0, "aggressive": 1.25}
        factor *= style_factors.get(driving_style, 1.0)
        
        trip_factors = {"urban": 1.1, "highway": 0.85, "mixed": 1.0, "offroad": 1.2}
        factor *= trip_factors.get(trip_type, 1.0)
        
        usage_factors = {"private": 1.0, "commercial": 1.1, "fleet": 1.05, "taxi": 1.15}
        factor *= usage_factors.get(usage_type, 1.0)
        
        condition_factors = {"excellent": 0.95, "good": 1.0, "fair": 1.05, "poor": 1.15}
        factor *= condition_factors.get(condition, 1.0)
        
        location_factors = {"urban": 1.05, "suburban": 1.0, "rural": 0.95, "remote": 1.1}
        factor *= location_factors.get(location, 1.0)
        
        return factor

    def _calculate_fuel_efficiency(self, engine_size: float, year: int,
                                   trip_type: str, fuel_type: str) -> float:
        """Calculate fuel efficiency in km/litre (fallback method)"""
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

        pattern_factors = {"urban": 0.8, "highway": 1.2, "mixed": 1.0, "offroad": 0.7}
        efficiency *= pattern_factors.get(trip_type, 1.0)

        return max(efficiency, 5.0)

    def _get_depreciation_rate(self, age: int, depreciation_rates: Dict[int, float]) -> float:
        """Get depreciation rate based on age"""
        clamped_age = min(age, 15)
        return depreciation_rates.get(clamped_age, depreciation_rates.get(15, 0.02))

    def _calculate_five_year_data(self, purchase_price: float, request: RunningCostRequest,
                                  fuel_type: str, fuel_price: float,
                                  maintenance_rate: float, tyre_cost_per_km: float,
                                  insurance_rate: float, vehicle_year: int,
                                  engine_size: float,
                                  depreciation_rates: Dict[int, float],
                                  driving_factor: float,
                                  include_insurance: bool,
                                  include_tyres: bool,
                                  include_maintenance: bool,
                                  include_depreciation: bool,
                                  insured_value: float) -> List[Dict[str, Any]]:
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

            fuel_cost = (annual_mileage / max(fuel_efficiency, 0.1)) * fuel_price * driving_factor
            service_cost = maintenance_rate * annual_mileage * (1 + (age * 0.03)) * driving_factor
            tyre_cost = tyre_cost_per_km * annual_mileage
            
            # Use insured_value for insurance projection
            insurance_cost = insured_value * insurance_rate * (1 - min(age * 0.02, 0.4))
            
            if not include_insurance:
                insurance_cost = 0
            if not include_tyres:
                tyre_cost = 0
            if not include_maintenance:
                service_cost = 0

            dep_rate = self._get_depreciation_rate(age, depreciation_rates)
            depreciation = current_value * dep_rate
            current_value -= depreciation
            
            if not include_depreciation:
                depreciation = 0

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
