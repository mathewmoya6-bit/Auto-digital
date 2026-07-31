# app/modules/running_cost/service.py
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

    # ─── Convert five_year_data to ProjectionYear objects ──────
    from app.modules.running_cost.schemas import ProjectionYear
    
    projection_years = [
        ProjectionYear(
            year=y["year"],
            fuel=y["fuel"],
            service=y["service"],
            tyres=y["tyres"],
            insurance=y["insurance"],
            depreciation=y["depreciation"],
            running_cost=y["running_cost"],
            total=y["total"],
            value=y["value"]
        )
        for y in five_year_data
    ]

    # ─── Build response with CORRECT camelCase field names ──────
    try:
        response = {
            # ─── ✅ Trip Summary (camelCase) ──────────────────────
            "tripTotal": round(total_cost_trip, 2),
            "tripCostPerKm": round(total_cost_per_km, 2),
            "distance": request.distance,

            # ─── ✅ Trip Cost Breakdown (camelCase) ───────────────
            "fuelCostTrip": round(fuel_cost_trip, 2),
            "serviceTrip": round(maintenance_cost_trip, 2),
            "tyreTrip": round(tyre_cost_trip, 2),
            "insuranceTrip": round(insurance_cost_trip, 2),
            "depreciationTrip": round(depreciation_cost_trip, 2),

            # ─── ✅ Per KM Costs (camelCase) ──────────────────────
            "fuelCostPerKm": round(fuel_cost_per_km, 2),
            "servicePerKm": round(maintenance_cost_per_km, 2),
            "tyrePerKm": round(tyre_cost_per_km, 2),
            "insurancePerKm": round(insurance_per_km, 2),
            "depreciationPerKm": round(depreciation_per_km, 2),

            # ─── ✅ Monthly Costs (camelCase) ─────────────────────
            "monthlyFuel": round(monthly_fuel, 2),
            "monthlyService": round(monthly_service, 2),
            "monthlyTyre": round(monthly_tyre, 2),
            "monthlyInsurance": round(monthly_insurance, 2),
            "monthlyDepreciation": round(monthly_depreciation, 2),

            # ─── ✅ Annual Costs (camelCase) ──────────────────────
            "annualFuel": round(monthly_fuel * 12, 2),
            "annualService": round(monthly_service * 12, 2),
            "annualTyre": round(monthly_tyre * 12, 2),
            "annualInsurance": round(annual_insurance, 2),
            "annualDepreciation": round(monthly_depreciation * 12, 2),

            # ─── ✅ 5-Year Projection (as ProjectionYear objects) ──
            "fiveYearData": projection_years,
            "total5YearCost": round(sum(y["total"] for y in five_year_data), 2),

            # ─── ✅ Vehicle Info (camelCase) ──────────────────────
            "originalCost": round(initial_vehicle_cost, 2),
            "ageAdjustedCost": round(remaining_value, 2),
            "current_value": round(remaining_value, 2),
            "remainingValue": round(resale_value, 2),
            "resale_value": round(resale_value, 2),
            "fuelTypeDisplay": fuel_type.capitalize(),
            "fuelConsumption": round(fuel_efficiency, 1),

            # ─── ✅ Full Vehicle Hierarchy ─────────────────────────
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

            # ─── ✅ New structured response ────────────────────────
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
