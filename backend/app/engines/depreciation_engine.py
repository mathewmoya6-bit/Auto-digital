# backend/app/engines/depreciation_engine.py
from typing import Dict, Any
from app.schemas.response import CostComponent

class DepreciationEngine:
    def calculate(self, vehicle: Dict[str, Any], distance: float, driving_style: str) -> CostComponent:
        """Calculate depreciation cost"""
        market_value = vehicle.get("market_value", 5000000)
        depreciation_class = vehicle.get("depreciation_class", "SUV_D")
        
        # Depreciation rates by class
        depreciation_rates = {
            "SUV_A": 0.12,    # 12% per year
            "SUV_B": 0.15,
            "SUV_C": 0.18,
            "SUV_D": 0.20,
            "SEDAN_A": 0.10,
            "SEDAN_B": 0.13,
            "SEDAN_C": 0.16,
            "SEDAN_D": 0.19,
            "PICKUP_A": 0.11,
            "PICKUP_B": 0.14,
            "PICKUP_C": 0.17,
            "LUXURY_A": 0.20,
            "LUXURY_B": 0.25,
            "LUXURY_C": 0.30,
        }
        
        # Get depreciation rate
        rate = depreciation_rates.get(depreciation_class, 0.15)
        
        # Adjust for driving style
        style_factor = {
            "normal": 1.0,
            "aggressive": 1.3,
            "defensive": 0.9
        }.get(driving_style, 1.0)
        
        # Calculate depreciation per km (assume 20,000km/year)
        annual_distance = 20000
        annual_depreciation = market_value * rate * style_factor
        depreciation_per_km = annual_depreciation / annual_distance
        
        total_depreciation = depreciation_per_km * distance
        
        return CostComponent(
            component="Depreciation",
            amount=round(total_depreciation, 2),
            description=f"{depreciation_class} class at {rate*100:.0f}% annual depreciation"
        )
