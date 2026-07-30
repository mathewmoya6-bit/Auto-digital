# mileage_engine.py
# Auto-D Kenya - Mileage Calculator Service Engine
# ================================================================
# TYPE: SERVICE - Core mileage calculation engine

import logging
import math
from datetime import datetime
from typing import Optional, Dict, Any

from config import settings
from database import get_supabase

logger = logging.getLogger(__name__)


class MileageEngine:
    """
    Mileage Calculation Engine.
    
    Calculates:
    - Fuel consumption
    - Fuel cost for a trip
    - Cost per kilometer
    - Annual fuel cost
    - CO2 emissions
    """
    
    def __init__(self):
        self.supabase = get_supabase()
        
        # CO2 emission factors (kg CO2 per litre)
        self.co2_factors = {
            "petrol": 2.31,
            "diesel": 2.68,
            "electric": 0.0,
            "hybrid": 1.50,
            "lpg": 1.50,
            "cng": 1.70
        }
    
    def calculate_fuel_consumption(
        self,
        variant: Dict[str, Any],
        trip_type: str = "mixed",
        driving_style: str = "normal"
    ) -> float:
        """
        Calculate fuel consumption in km/l.
        
        Args:
            variant: Vehicle variant data
            trip_type: urban, highway, mixed
            driving_style: eco, normal, aggressive
            
        Returns:
            Fuel consumption in km/l
        """
        # Get base consumption from variant
        base_consumption = variant.get("fuel_consumption_combined", 10.0)
        
        # Trip type factors
        type_factors = {
            "urban": 1.15,
            "highway": 0.85,
            "mixed": 1.00
        }
        
        # Driving style factors
        style_factors = {
            "eco": 0.90,
            "normal": 1.00,
            "aggressive": 1.15
        }
        
        type_factor = type_factors.get(trip_type, 1.00)
        style_factor = style_factors.get(driving_style, 1.00)
        
        effective_consumption = base_consumption / (type_factor * style_factor)
        
        return max(effective_consumption, 1.0)
    
    def calculate_fuel_cost(
        self,
        distance: float,
        fuel_consumption: float,
        fuel_price: float
    ) -> float:
        """Calculate fuel cost for a trip."""
        if fuel_consumption <= 0:
            return 0
        fuel_needed = distance / fuel_consumption
        return fuel_needed * fuel_price
    
    def calculate_co2_emissions(
        self,
        distance: float,
        fuel_consumption: float,
        fuel_type: str = "petrol"
    ) -> float:
        """Calculate CO2 emissions for a trip in kg."""
        if fuel_type.lower() == "electric":
            return 0
        
        co2_factor = self.co2_factors.get(fuel_type.lower(), 2.31)
        
        if fuel_consumption <= 0:
            return 0
        
        fuel_needed = distance / fuel_consumption
        return fuel_needed * co2_factor
    
    async def calculate_mileage(
        self,
        variant_id: str,
        distance: float,
        annual_mileage: float,
        fuel_price: float,
        trip_type: str = "mixed",
        driving_style: str = "normal",
        variant_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete mileage calculation.
        
        Args:
            variant_id: Vehicle variant ID
            distance: Trip distance in km
            annual_mileage: Annual mileage in km
            fuel_price: Fuel price per litre
            trip_type: urban, highway, mixed
            driving_style: eco, normal, aggressive
            variant_data: Optional pre-fetched variant data
            
        Returns:
            Complete mileage result
        """
        try:
            # Get variant data if not provided
            if not variant_data:
                variant_result = self.supabase.table("vehicle_variants").select("*").eq("variant_id", variant_id).execute()
                variant_data = variant_result.data[0] if variant_result.data else {}
            
            # Calculate fuel consumption
            fuel_consumption = self.calculate_fuel_consumption(
                variant_data, trip_type, driving_style
            )
            
            # Get fuel type
            fuel_type = variant_data.get("fuel_type_name", "petrol")
            
            # Calculate costs
            fuel_cost = self.calculate_fuel_cost(distance, fuel_consumption, fuel_price)
            cost_per_km = fuel_cost / distance if distance > 0 else 0
            annual_fuel_cost = (annual_mileage / fuel_consumption) * fuel_price
            
            # Calculate CO2 emissions
            co2_emissions = self.calculate_co2_emissions(distance, fuel_consumption, fuel_type)
            
            return {
                "variant_id": variant_id,
                "distance": distance,
                "annual_mileage": annual_mileage,
                "fuel_price": fuel_price,
                "fuel_consumption": round(fuel_consumption, 2),
                "fuel_cost": round(fuel_cost, 2),
                "cost_per_km": round(cost_per_km, 2),
                "annual_fuel_cost": round(annual_fuel_cost, 2),
                "co2_emissions": round(co2_emissions, 2),
                "fuel_type": fuel_type
            }
            
        except Exception as e:
            logger.error(f"Mileage calculation error: {str(e)}")
            raise
