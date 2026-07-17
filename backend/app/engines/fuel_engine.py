# backend/app/engines/fuel_engine.py
from typing import Dict, Any
from app.schemas.response import CostComponent

class FuelEngine:
    def __init__(self):
        # Fuel prices in KES per liter
        self.fuel_prices = {
            "petrol": 180.0,
            "diesel": 170.0,
            "electric": 20.0,  # KES per kWh
            "hybrid": 160.0
        }
    
    def calculate(self, vehicle: Dict[str, Any], distance: float, trip_type: str) -> CostComponent:
        """Calculate fuel cost for a trip"""
        fuel_type = vehicle.get("fuel_type", "petrol")
        fuel_consumption = vehicle.get("fuel_consumption", 10.0)  # L/100km
        
        # Adjust consumption based on trip type
        if trip_type == "urban":
            consumption_factor = 1.15
        elif trip_type == "highway":
            consumption_factor = 0.85
        elif trip_type == "mixed":
            consumption_factor = 1.0
        else:
            consumption_factor = 1.0
        
        # Calculate fuel consumed
        fuel_consumed = (fuel_consumption * consumption_factor * distance) / 100.0
        
        # Get fuel price
        price_per_unit = self.fuel_prices.get(fuel_type, 180.0)
        
        # Calculate cost
        fuel_cost = fuel_consumed * price_per_unit
        
        return CostComponent(
            component="Fuel",
            amount=round(fuel_cost, 2),
            description=f"{fuel_consumed:.2f} {fuel_type} at KES {price_per_unit}/liter"
        )
