# backend/app/engines/insurance_engine.py
from typing import Dict, Any
from app.schemas.response import CostComponent

class InsuranceEngine:
    def calculate(self, vehicle: Dict[str, Any], distance: float, driving_style: str) -> CostComponent:
        """Calculate insurance cost"""
        market_value = vehicle.get("market_value", 5000000)
        insurance_group = vehicle.get("insurance_group", 5)
        
        # Base insurance rate (percentage of vehicle value)
        base_rate = 0.02  # 2% of vehicle value
        
        # Adjust for insurance group (1-10)
        group_factor = 0.8 + (insurance_group - 1) * 0.05  # 0.8 to 1.25
        
        # Adjust for driving style
        style_factor = {
            "normal": 1.0,
            "aggressive": 1.2,
            "defensive": 0.9
        }.get(driving_style, 1.0)
        
        # Calculate annual insurance premium
        annual_premium = market_value * base_rate * group_factor * style_factor
        
        # Pro-rate for the distance (assume 20000km/year average)
        annual_distance = 20000
        insurance_cost = (annual_premium * distance) / annual_distance
        
        return CostComponent(
            component="Insurance",
            amount=round(insurance_cost, 2),
            description=f"Annual premium KES {round(annual_premium, 2)} prorated for {distance}km"
        )
