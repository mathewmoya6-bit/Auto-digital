# backend/app/engines/miscellaneous_engine.py
from typing import Dict, Any
from app.schemas.response import CostComponent

class MiscellaneousEngine:
    def calculate(self, vehicle: Dict[str, Any], distance: float, trip_type: str) -> CostComponent:
        """Calculate miscellaneous costs (parking, tolls, etc.)"""
        # Estimate misc costs based on trip type
        misc_rates = {
            "urban": 5.0,    # KES per km
            "highway": 3.0,
            "mixed": 4.0,
            "offroad": 8.0
        }
        
        rate = misc_rates.get(trip_type, 4.0)
        misc_cost = rate * distance
        
        return CostComponent(
            component="Miscellaneous",
            amount=round(misc_cost, 2),
            description=f"Parking, tolls, and other expenses at KES {rate}/km"
        )
