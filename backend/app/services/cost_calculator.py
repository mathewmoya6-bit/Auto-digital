"""
Cost Calculator Service
Calculates running costs, ownership costs, and mileage rates
"""

from __future__ import annotations

import logging
import random
from typing import Optional, Dict, List, Any
from datetime import datetime

from app.core.database import supabase
from app.core.config import settings

logger = logging.getLogger(__name__)


class CostCalculator:
    """Service for calculating vehicle costs"""
    
    def __init__(self):
        self.annual_mileage = getattr(settings, 'DEFAULT_ANNUAL_MILEAGE', 20000)
        self.depreciation_rate = getattr(settings, 'DEFAULT_DEPRECIATION_RATE', 0.15)
        self.insurance_rate = getattr(settings, 'DEFAULT_INSURANCE_RATE', 0.045)
        self.tyre_lifespan = getattr(settings, 'DEFAULT_TYRE_LIFESPAN', 45000)
        self.service_interval = getattr(settings, 'DEFAULT_SERVICE_INTERVAL', 10000)
        
        # Cost parameters with defaults
        self.fuel_consumption_factors = {
            "urban": getattr(settings, 'FUEL_CONSUMPTION_FACTOR_URBAN', 1.15),
            "highway": getattr(settings, 'FUEL_CONSUMPTION_FACTOR_HIGHWAY', 0.85),
            "mixed": getattr(settings, 'FUEL_CONSUMPTION_FACTOR_MIXED', 1.0)
        }
    
    def _get_vehicle_details(self, variant_id: str) -> Optional[Dict]:
        """Get vehicle details from database"""
        try:
            result = supabase.table(getattr(settings, 'TABLE_VEHICLE_VARIANTS', 'vehicle_variants'))\
                .select("*")\
                .eq("id", variant_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting vehicle details: {e}")
            return None
    
    def _get_fuel_consumption(self, vehicle: Optional[Dict], driving_style: str = "normal", trip_type: str = "mixed") -> float:
        """Get fuel consumption in L/100km"""
        if not vehicle:
            return 8.0
        
        base_consumption = vehicle.get("fuel_consumption_combined") or vehicle.get("fuel_consumption") or 8.0
        
        style_factors = {"eco": 0.85, "normal": 1.0, "aggressive": 1.15}
        style_factor = style_factors.get(driving_style, 1.0)
        
        trip_factors = {
            "urban": self.fuel_consumption_factors.get("urban", 1.15),
            "highway": self.fuel_consumption_factors.get("highway", 0.85),
            "mixed": self.fuel_consumption_factors.get("mixed", 1.0)
        }
        trip_factor = trip_factors.get(trip_type, 1.0)
        
        return base_consumption * style_factor * trip_factor
    
    def _get_base_price(self, vehicle: Dict) -> float:
        """Get base price for vehicle"""
        if vehicle.get("base_price"):
            return float(vehicle["base_price"])
        if vehicle.get("market_value"):
            return float(vehicle["market_value"])
        if vehicle.get("price"):
            return float(vehicle["price"])
        
        # Default price based on make
        make = vehicle.get("make") or vehicle.get("make_name") or ""
        base_prices = {
            "Toyota": 3500000,
            "Honda": 3000000,
            "Nissan": 2800000,
            "Mazda": 2700000,
            "Subaru": 3200000,
            "Mercedes": 6000000,
            "BMW": 5500000,
            "Audi": 5000000,
            "Volkswagen": 3500000,
            "Ford": 3000000,
            "default": 2500000
        }
        return base_prices.get(make, base_prices["default"])
    
    def _get_vehicle_age(self, year: int) -> int:
        """Calculate vehicle age"""
        current_year = datetime.now().year
        return max(0, current_year - year)
    
    # ─── Public Methods ───────────────────────────────────────────────
    
    def calculate_running_cost(
        self,
        variant_id: str,
        year: int,
        mileage: float,
        annual_km: float,
        fuel_price: float,
        driving_style: str = "normal",
        trip_type: str = "mixed",
        usage_type: str = "private",
        location: str = "nairobi",
        distance: float = 150,
        financed: bool = False,
        down_payment_percent: float = 30,
        interest_rate: float = 16,
        loan_term: int = 4
    ) -> Dict:
        """Calculate running cost for a trip"""
        
        vehicle = self._get_vehicle_details(variant_id)
        fuel_consumption = self._get_fuel_consumption(vehicle, driving_style, trip_type)
        base_price = self._get_base_price(vehicle) if vehicle else 3000000
        
        # Calculate per-trip costs
        fuel_cost = (distance / 100) * fuel_consumption * fuel_price
        
        service_cost = distance * 1.5
        tyre_cost = distance * 1.0
        insurance_cost = distance * 2.0
        depreciation_cost = distance * 3.0
        
        # Financing cost
        financing_cost = 0
        if financed:
            loan_amount = base_price * (1 - down_payment_percent / 100)
            annual_payment = loan_amount * (1 + interest_rate / 100) / loan_term
            financing_cost = (annual_payment / annual_km) * distance
        
        total_cost = fuel_cost + service_cost + tyre_cost + insurance_cost + depreciation_cost + financing_cost
        cost_per_km = total_cost / distance if distance > 0 else 0
        
        monthly_km = annual_km / 12
        monthly_cost = cost_per_km * monthly_km
        annual_cost = cost_per_km * annual_km
        
        # 5-year projection
        five_year_data = []
        current_value = base_price
        for i in range(1, 6):
            dep_rate = 0.15 - (i - 1) * 0.01
            dep_rate = max(0.08, min(0.25, dep_rate))
            depreciation = current_value * dep_rate
            current_value -= depreciation
            
            inflation = 1 + (i - 1) * 0.04
            yearly_fuel = (annual_km / 100) * fuel_consumption * fuel_price * inflation
            yearly_service = 15000 * (1 + (i - 1) * 0.05)
            yearly_insurance = base_price * 0.045 * (1 + (i - 1) * 0.03)
            yearly_tyres = 40000 * (1 + (i - 1) * 0.04)
            
            yearly_total = depreciation + yearly_fuel + yearly_service + yearly_insurance + yearly_tyres
            
            five_year_data.append({
                "year": i,
                "depreciation": round(depreciation, 2),
                "fuel": round(yearly_fuel, 2),
                "service": round(yearly_service, 2),
                "insurance": round(yearly_insurance, 2),
                "tyres": round(yearly_tyres, 2),
                "total": round(yearly_total, 2),
                "value": round(current_value, 2)
            })
        
        return {
            "trip": {
                "distance": distance,
                "total_cost": round(total_cost, 2),
                "cost_per_km": round(cost_per_km, 2)
            },
            "breakdown": {
                "fuel": round(fuel_cost, 2),
                "service": round(service_cost, 2),
                "tyres": round(tyre_cost, 2),
                "insurance": round(insurance_cost, 2),
                "depreciation": round(depreciation_cost, 2),
                "financing": round(financing_cost, 2)
            },
            "monthly": {
                "fuel": round(fuel_cost * monthly_km / distance, 2) if distance > 0 else 0,
                "service": round(service_cost * monthly_km / distance, 2) if distance > 0 else 0,
                "tyres": round(tyre_cost * monthly_km / distance, 2) if distance > 0 else 0,
                "insurance": round(insurance_cost * monthly_km / distance, 2) if distance > 0 else 0,
                "depreciation": round(depreciation_cost * monthly_km / distance, 2) if distance > 0 else 0,
                "total": round(monthly_cost, 2)
            },
            "annual": {
                "fuel": round(fuel_cost * annual_km / distance, 2) if distance > 0 else 0,
                "service": round(service_cost * annual_km / distance, 2) if distance > 0 else 0,
                "tyres": round(tyre_cost * annual_km / distance, 2) if distance > 0 else 0,
                "insurance": round(insurance_cost * annual_km / distance, 2) if distance > 0 else 0,
                "depreciation": round(depreciation_cost * annual_km / distance, 2) if distance > 0 else 0,
                "total": round(annual_cost, 2)
            },
            "five_year": five_year_data,
            "vehicle": {
                "make": vehicle.get("make") if vehicle else "Unknown",
                "model": vehicle.get("model") if vehicle else "Unknown",
                "variant": vehicle.get("variant") if vehicle else "Unknown",
                "fuel_type": vehicle.get("fuel_type") if vehicle else "Unknown",
                "fuel_consumption": round(fuel_consumption, 2)
            } if vehicle else None,
            "parameters": {
                "annual_km": annual_km,
                "fuel_price": fuel_price,
                "driving_style": driving_style,
                "trip_type": trip_type,
                "usage_type": usage_type,
                "location": location,
                "financed": financed
            }
        }
    
    def calculate_ownership_cost(
        self,
        variant_id: str,
        year: int,
        initial_value: float,
        current_value: float,
        annual_mileage: float,
        ownership_years: int,
        insurance_rate: float,
        insurance_type: str = "comprehensive",
        fuel_price: float = 200,
        location: str = "nairobi",
        is_new: bool = True,
        is_financed: bool = False,
        down_payment_percent: float = 30,
        interest_rate: float = 16,
        loan_term: int = 4
    ) -> Dict:
        """Calculate total cost of ownership"""
        
        vehicle = self._get_vehicle_details(variant_id)
        fuel_consumption = self._get_fuel_consumption(vehicle) if vehicle else 8
        
        years_data = []
        total_cost = 0
        current_value_remaining = current_value
        
        for i in range(ownership_years):
            year_num = i + 1
            
            dep_rate = 0.15 - (i * 0.01)
            dep_rate = max(0.08, min(0.25, dep_rate))
            depreciation = current_value_remaining * dep_rate
            current_value_remaining -= depreciation
            
            fuel_cost = (annual_mileage / 100) * fuel_consumption * fuel_price * (1 + i * 0.04)
            
            insurance = current_value_remaining * insurance_rate * (1 + i * 0.03)
            
            maintenance = 15000 * (1 + i * 0.08)
            tyre_cost = 40000 * (1 + i * 0.04)
            licensing = current_value_remaining * 0.01
            
            financing = 0
            if is_financed and i < loan_term:
                loan_amount = initial_value * (1 - down_payment_percent / 100)
                financing = (loan_amount / loan_term) + (loan_amount * interest_rate / 100)
            
            year_total = depreciation + fuel_cost + insurance + maintenance + tyre_cost + licensing + financing
            total_cost += year_total
            
            years_data.append({
                "year": year_num,
                "depreciation": round(depreciation, 2),
                "fuel": round(fuel_cost, 2),
                "insurance": round(insurance, 2),
                "maintenance": round(maintenance, 2),
                "tyres": round(tyre_cost, 2),
                "licensing": round(licensing, 2),
                "financing": round(financing, 2),
                "total": round(year_total, 2),
                "value": round(current_value_remaining, 2)
            })
        
        average_monthly = total_cost / (ownership_years * 12)
        cost_per_km = total_cost / (annual_mileage * ownership_years) if annual_mileage > 0 else 0
        
        return {
            "total_cost": round(total_cost, 2),
            "average_monthly": round(average_monthly, 2),
            "cost_per_km": round(cost_per_km, 2),
            "resale_value": round(current_value_remaining, 2),
            "years": years_data,
            "vehicle": {
                "make": vehicle.get("make") if vehicle else "Unknown",
                "model": vehicle.get("model") if vehicle else "Unknown",
                "variant": vehicle.get("variant") if vehicle else "Unknown"
            } if vehicle else None,
            "parameters": {
                "annual_mileage": annual_mileage,
                "ownership_years": ownership_years,
                "insurance_rate": insurance_rate,
                "insurance_type": insurance_type,
                "fuel_price": fuel_price,
                "is_new": is_new,
                "is_financed": is_financed
            }
        }
    
    def calculate_mileage_rate(
        self,
        variant_id: str,
        year: int,
        fuel_price: float,
        annual_km: float = 20000,
        driving_style: str = "normal"
    ) -> Dict:
        """Calculate mileage rate per km"""
        
        vehicle = self._get_vehicle_details(variant_id)
        fuel_consumption = self._get_fuel_consumption(vehicle, driving_style)
        base_price = self._get_base_price(vehicle) if vehicle else 3000000
        
        fuel_cost_per_km = (fuel_consumption / 100) * fuel_price
        service_cost_per_km = 1.5
        tyre_cost_per_km = 1.0
        
        age = self._get_vehicle_age(year)
        insurance_per_km = (base_price * 0.045) / annual_km
        dep_per_km = (base_price * 0.15) / annual_km
        
        total_per_km = fuel_cost_per_km + service_cost_per_km + tyre_cost_per_km + insurance_per_km + dep_per_km
        
        return {
            "cost_per_km": round(total_per_km, 2),
            "breakdown": {
                "fuel": round(fuel_cost_per_km, 2),
                "service": round(service_cost_per_km, 2),
                "tyres": round(tyre_cost_per_km, 2),
                "insurance": round(insurance_per_km, 2),
                "depreciation": round(dep_per_km, 2)
            },
            "annual_cost": round(total_per_km * annual_km, 2),
            "monthly_cost": round(total_per_km * annual_km / 12, 2),
            "fuel_consumption": round(fuel_consumption, 2),
            "vehicle": {
                "make": vehicle.get("make") if vehicle else "Unknown",
                "model": vehicle.get("model") if vehicle else "Unknown"
            } if vehicle else None
        }
