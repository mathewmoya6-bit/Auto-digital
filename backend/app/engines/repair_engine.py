# backend/app/engines/repair_engine.py
from typing import Dict, Any
from app.schemas.response import CostComponent

class RepairEngine:
    def calculate(self, vehicle: Dict[str, Any], distance: float, driving_style: str) -> CostComponent:
        """Calculate repair and maintenance cost"""
        market_value = vehicle.get("market_value", 5000000)
        
        # Repair cost as percentage of vehicle value
        repair_rate = 0.008  # 0.8% per year
        
        # Adjust for driving style
        style_factor = {
            "normal": 1.0,
            "aggressive": 1.4,
            "defensive": 0.8
        }.get(driving_style, 1.0)
        
        # Calculate annual repair cost
        annual_repair = market_value * repair_rate * style_factor
        
        # Pro-rate for distance (assume 20,000km/year)
        annual_distance = 20000
        repair_cost = (annual_repair * distance) / annual_distance
        
        return CostComponent(
            component="Repairs",
            amount=round(repair_cost, 2),
            description=f"Annual repairs estimated at KES {round(annual_repair, 2)}"
        )
