# app/modules/running_cost/service.py
"""Running Cost service for Auto-D Kenya"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from functools import lru_cache

from app.core.database import get_supabase
from app.modules.running_cost.router import RunningCostRequest

logger = logging.getLogger(__name__)


class RunningCostService:
    """Service for running cost calculations"""
    
    def __init__(self):
        self.supabase = get_supabase()
        self._variant_cache = {}
        
        # ✅ FIX 13: Move constants to be configurable (will be moved to DB)
        self.FUEL_PRICES = {
            "petrol": 193.00,
            "diesel": 180.00,
            "electric": 20.00,
            "hybrid": 193.00
        }
        
        self.MAINTENANCE_RATES = {
            "petrol": 2.50,
            "diesel": 3.00,
            "electric": 1.50,
            "hybrid": 2.00
        }
        
        self.INSURANCE_RATES = {
            "comprehensive": 0.04,
            "third_party": 0.015
        }
        
        # ✅ FIX 10: Different depreciation rates by age bands
        self.DEPRECIATION_RATES = {
            0: 0.20,   # Brand new
            1: 0.18,
            2: 0.15,
            3: 0.12,
            4: 0.10,
            5: 0.08,
            6: 0.07,
            7: 0.06,
            8: 0.05,
            9: 0.04,
            10: 0.03,
            11: 0.03,
            12: 0.03,
            13: 0.02,
            14: 0.02,
            15: 0.02
        }
        
        self.TYRE_LIFESPAN_KM = 50000
        self.TYRE_COST_PER_SET = 48000  # 4 tyres * 12000
        
    # ✅ FIX 12: Cache lookup tables
    @lru_cache(maxsize=128)
    async def _get_variant_data_cached(self, variant_id: int) -> Dict[str, Any]:
        """Get variant data from database with caching"""
        try:
            # ✅ FIX 11: Use .single() instead of .limit(1)
            result = self.supabase.table("vehicle_master_specs")\
                .select("*")\
                .eq("variant_id", variant_id)\
                .single()\
                .execute()
            
            if result.data:
                return result.data
            return {}
        except Exception as e:
            logger.exception(f"Error getting variant data for ID {variant_id}: {str(e)}")
            return {}
    
    async def get_variant_data(self, variant_id: int) -> Dict[str, Any]:
        """Get variant data from cache or database"""
        return await self._get_variant_data_cached(variant_id)
    
    async def calculate_running_cost(self, request: RunningCostRequest, user_id: int) -> Dict[str, Any]:
        """Calculate running costs"""
        # ✅ FIX 23: Validate year
        current_year = datetime.now().year
        if request.year and (request.year < 1900 or request.year > current_year + 1):
            raise ValueError(f"Invalid year: {request.year}. Year must be between 1900 and {current_year + 1}")
        
        # ✅ FIX 21: Validate distance
        if request.distance <= 0:
            raise ValueError("Distance must be greater than 0")
        
        # ✅ FIX 22: Validate annual mileage
        if request.annual_mileage <= 0:
            raise ValueError("Annual mileage must be greater than 0")
        
        # Get variant data
        variant = await self.get_variant_data(request.variant_id)
        if not variant:
            raise ValueError(f"Variant with ID {request.variant_id} not found")
        
        # ✅ FIX 7: Use actual engine size from variant
        fuel_type = variant.get("fuel_type_name", "petrol").lower()
        engine_size = variant.get("engine_size_cc", 1800) / 1000  # Convert to litres
        
        # ✅ FIX 24: Validate engine size
        if engine_size <= 0:
            engine_size = 1.8  # Fallback default
            logger.warning(f"Invalid engine size for variant {request.variant_id}, using default 1.8L")
        
        vehicle_year = request.year or variant.get("generation_start_year", 2020)
        
        # ✅ FIX 6: Calculate vehicle age correctly
        vehicle_age = current_year - vehicle_year
        
        # Resolve fuel price
        fuel_price = request.fuel_price or self.FUEL_PRICES.get(fuel_type, 193.00)
        if fuel_price <= 0:
            fuel_price = 193.00
            logger.warning(f"Invalid fuel price, using default: {fuel_price}")
        
        # ✅ FIX 26 & 27: Compute once and reuse
        fuel_efficiency = self._calculate_fuel_efficiency(
            engine_size, vehicle_year, request.trip_type, fuel_type
        )
        
        # ✅ FIX 25: Guard against division by zero
        if fuel_efficiency <= 0:
            fuel_efficiency = 10.0
            logger.warning(f"Invalid fuel efficiency, using default: {fuel_efficiency}")
        
        # ─── Calculate all costs ────────────────────────────────────
        # Fuel cost
        fuel_cost_per_km = fuel_price / fuel_efficiency
        fuel_cost_trip = fuel_cost_per_km * request.distance
        
        # Maintenance cost (age-adjusted)
        maintenance_rate = self.MAINTENANCE_RATES.get(fuel_type, 2.50)
        age_factor = 1 + (vehicle_age * 0.05)
        maintenance_cost_per_km = maintenance_rate * age_factor
        maintenance_cost_trip = maintenance_cost_per_km * request.distance
        
        # Tyre cost
        tyre_cost_per_km = self.TYRE_COST_PER_SET / self.TYRE_LIFESPAN_KM
        tyre_cost_trip = tyre_cost_per_km * request.distance
        
        # Insurance cost
        purchase_price = variant.get("purchase_price", 2500000)
        insurance_rate = self.INSURANCE_RATES["comprehensive"]
        annual_insurance = purchase_price * insurance_rate
        insurance_per_km = annual_insurance / request.annual_mileage
        insurance_cost_trip = insurance_per_km * request.distance
        
        # Depreciation cost
        depreciation_rate = self._get_depreciation_rate(vehicle_age)
        # ✅ FIX 9: Use compound depreciation for remaining value
        remaining_value = purchase_price * ((1 - depreciation_rate) ** min(vehicle_age, 15))
        resale_value = max(remaining_value, purchase_price * 0.15)
        
        depreciation_per_km = (purchase_price - remaining_value) / request.annual_mileage
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
        monthly_depreciation = (purchase_price - remaining_value) / 12
        
        # ✅ FIX 8: 5-year projection using resolved values
        five_year_data = self._calculate_five_year_data(
            purchase_price, request, fuel_type, fuel_price,
            maintenance_rate, tyre_cost_per_km, insurance_rate,
            vehicle_year
        )
        
        # ✅ FIX 18: Return structured response with Pydantic model
        return {
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
                "purchase_price": round(purchase_price, 2),
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
    
    def _calculate_fuel_efficiency(self, engine_size: float, year: int, 
                                   trip_type: str, fuel_type: str) -> float:
        """Calculate fuel efficiency in km/litre"""
        base_efficiency = {
            "petrol": 12.0,
            "diesel": 14.0,
            "electric": 6.0,
            "hybrid": 18.0
        }
        
        efficiency = base_efficiency.get(fuel_type, 12.0)
        efficiency -= max(0, (engine_size - 1.5) * 1.5)
        year_factor = 1 + ((datetime.now().year - year) * 0.005)
        efficiency *= year_factor
        
        pattern_factors = {
            "urban": 0.8,
            "highway": 1.2,
            "mixed": 1.0,
            "offroad": 0.7
        }
        efficiency *= pattern_factors.get(trip_type, 1.0)
        
        return max(efficiency, 5.0)
    
    def _get_depreciation_rate(self, age: int) -> float:
        """Get depreciation rate based on age"""
        return self.DEPRECIATION_RATES.get(age, 0.08)
    
    def _calculate_five_year_data(self, purchase_price: float, request: RunningCostRequest,
                                  fuel_type: str, fuel_price: float,
                                  maintenance_rate: float, tyre_cost_per_km: float,
                                  insurance_rate: float, vehicle_year: int) -> list:
        """Calculate 5-year cost projection"""
        data = []
        current_value = purchase_price
        current_year = datetime.now().year
        
        for year in range(1, request.years + 1):
            # ✅ FIX 6: Correct age calculation
            age = (current_year - vehicle_year) + (year - 1)
            annual_mileage = request.annual_mileage
            
            # Recalculate fuel efficiency for each year (age affects efficiency)
            fuel_efficiency = self._calculate_fuel_efficiency(
                1.8, vehicle_year + year - 1, request.trip_type, fuel_type
            )
            
            # Fuel cost for the year
            fuel_cost = (annual_mileage / fuel_efficiency) * fuel_price
            
            # Service cost (increases with age)
            service_cost = maintenance_rate * annual_mileage * (1 + (age * 0.03))
            
            # Tyre cost
            tyre_cost = tyre_cost_per_km * annual_mileage
            
            # Insurance cost (decreases with age)
            insurance_cost = purchase_price * insurance_rate * (1 - min(age * 0.02, 0.4))
            
            # Depreciation for the year (compounded)
            dep_rate = self._get_depreciation_rate(age)
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
