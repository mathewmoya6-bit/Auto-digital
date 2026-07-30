# app/modules/running_cost/service.py
"""Running Cost service for Auto-D Kenya"""
import logging
from typing import Dict, Any
from datetime import datetime
import math

from app.core.database import get_supabase
# Import the schema from router
from app.modules.running_cost.router import RunningCostRequest

logger = logging.getLogger(__name__)

class RunningCostService:
    """Service for running cost calculations"""
    
    def __init__(self):
        self.supabase = get_supabase()
        
        # Base rates for Kenya
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
        
        self.DEPRECIATION_RATES = {
            0: 0.00, 1: 0.20, 2: 0.15, 3: 0.12,
            4: 0.10, 5: 0.08, 6: 0.07, 7: 0.06,
            8: 0.05, 9: 0.04, 10: 0.03
        }
        
        self.TYRE_LIFESPAN_KM = 50000
        self.TYRE_COST_PER_SET = 48000  # 4 tyres * 12000
        
    async def get_variant_data(self, variant_id: int) -> Dict[str, Any]:
        """Get variant data from database"""
        try:
            result = self.supabase.table("vehicle_master_specs")\
                .select("*")\
                .eq("variant_id", variant_id)\
                .execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            return {}
        except Exception as e:
            logger.error(f"Error getting variant data: {str(e)}")
            return {}
    
    async def calculate_running_cost(self, request: RunningCostRequest, user_id: int) -> Dict[str, Any]:
        """Calculate running costs"""
        # Get variant data
        variant = await self.get_variant_data(request.variant_id)
        if not variant:
            raise ValueError("Variant not found")
        
        fuel_type = variant.get("fuel_type_name", "petrol").lower()
        engine_size = variant.get("engine_size_cc", 1800) / 1000  # Convert to litres
        year = request.year or variant.get("generation_start_year", 2020)
        
        # Calculate fuel efficiency
        fuel_efficiency = self._calculate_fuel_efficiency(
            engine_size, year, request.trip_type, fuel_type
        )
        
        # Fuel cost
        fuel_price = request.fuel_price or self.FUEL_PRICES.get(fuel_type, 193.00)
        fuel_cost_per_km = fuel_price / fuel_efficiency
        fuel_cost_trip = fuel_cost_per_km * request.distance
        
        # Maintenance cost
        maintenance_rate = self.MAINTENANCE_RATES.get(fuel_type, 2.50)
        age = datetime.now().year - year
        maintenance_rate *= (1 + (age * 0.05))
        maintenance_cost_per_km = maintenance_rate
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
        depreciation_rate = self._get_depreciation_rate(age)
        depreciation_per_km = (purchase_price * depreciation_rate) / request.annual_mileage
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
        monthly_depreciation = (purchase_price * depreciation_rate) / 12
        
        # 5-year projection
        five_year_data = self._calculate_five_year_data(
            purchase_price, request, fuel_type, maintenance_rate,
            tyre_cost_per_km, insurance_rate, depreciation_rate
        )
        
        # Resale value
        remaining_value = purchase_price * (1 - depreciation_rate * request.years)
        resale_value = max(remaining_value, purchase_price * 0.20)
        
        return {
            "tripTotal": round(total_cost_trip, 2),
            "tripCostPerKm": round(total_cost_per_km, 2),
            "distance": request.distance,
            "fuelCostTrip": round(fuel_cost_trip, 2),
            "serviceTrip": round(maintenance_cost_trip, 2),
            "tyreTrip": round(tyre_cost_trip, 2),
            "insuranceTrip": round(insurance_cost_trip, 2),
            "depreciationTrip": round(depreciation_cost_trip, 2),
            "fuelCostPerKm": round(fuel_cost_per_km, 2),
            "servicePerKm": round(maintenance_cost_per_km, 2),
            "tyrePerKm": round(tyre_cost_per_km, 2),
            "insurancePerKm": round(insurance_per_km, 2),
            "depreciationPerKm": round(depreciation_per_km, 2),
            "monthlyFuel": round(monthly_fuel, 2),
            "monthlyService": round(monthly_service, 2),
            "monthlyTyre": round(monthly_tyre, 2),
            "monthlyInsurance": round(monthly_insurance, 2),
            "monthlyDepreciation": round(monthly_depreciation, 2),
            "annualFuel": round(monthly_fuel * 12, 2),
            "annualService": round(monthly_service * 12, 2),
            "annualTyre": round(monthly_tyre * 12, 2),
            "annualInsurance": round(annual_insurance, 2),
            "annualDepreciation": round(monthly_depreciation * 12, 2),
            "fiveYearData": five_year_data,
            "total5YearCost": round(sum(y["total"] for y in five_year_data), 2),
            "originalCost": round(purchase_price, 2),
            "ageAdjustedCost": round(purchase_price * (1 - depreciation_rate * min(age, 10)), 2),
            "current_value": round(purchase_price * (1 - depreciation_rate * min(age, 10)), 2),
            "remainingValue": round(remaining_value, 2),
            "resale_value": round(resale_value, 2),
            "fuelTypeDisplay": fuel_type.capitalize(),
            "fuelConsumption": round(fuel_efficiency, 1),
            "calculated_at": datetime.utcnow()
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
        efficiency -= (engine_size - 1.5) * 1.5
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
                                  fuel_type: str, maintenance_rate: float,
                                  tyre_cost_per_km: float, insurance_rate: float,
                                  depreciation_rate: float) -> list:
        """Calculate 5-year cost projection"""
        data = []
        current_value = purchase_price
        
        for year in range(1, request.years + 1):
            age = request.year + year - datetime.now().year
            annual_mileage = request.annual_mileage
            
            # Costs for the year
            fuel_cost = (annual_mileage / self._calculate_fuel_efficiency(
                1.8, request.year, request.trip_type, fuel_type
            )) * request.fuel_price
            
            service_cost = maintenance_rate * annual_mileage
            tyre_cost = tyre_cost_per_km * annual_mileage
            insurance_cost = purchase_price * insurance_rate
            
            # Depreciation for the year
            dep_rate = self._get_depreciation_rate(age)
            depreciation = current_value * dep_rate
            current_value -= depreciation
            
            total = fuel_cost + service_cost + tyre_cost + insurance_cost + depreciation
            
            data.append({
                "year": year,
                "fuel": round(fuel_cost, 2),
                "service": round(service_cost, 2),
                "tyres": round(tyre_cost, 2),
                "insurance": round(insurance_cost, 2),
                "depreciation": round(depreciation, 2),
                "total": round(total, 2),
                "value": round(current_value, 2)
            })
        
        return data
