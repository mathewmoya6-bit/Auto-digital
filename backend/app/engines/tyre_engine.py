# backend/app/engines/tyre_engine.py
"""
Tyre Engine - Tyre cost calculations
"""

from typing import Dict, Any
from app.schemas.response import CostComponent


class TyreEngine:
    """Engine for calculating tyre costs"""
    
    def calculate(self, vehicle: Dict[str, Any], distance: float) -> CostComponent:
        """
        Calculate tyre cost for a trip
        
        Args:
            vehicle: Vehicle data dictionary
            distance: Distance in km
        
        Returns:
            CostComponent with tyre cost details
        """
        # Get tyre cost and lifespan from vehicle data
        tyre_cost_per_unit = vehicle.get("tyre_cost", 12000)  # KES per tyre
        tyre_lifespan = vehicle.get("tyre_lifespan", 45000)  # km
        
        # Calculate tyre cost per km
        # 4 tyres needed
        tyre_cost_per_km = (tyre_cost_per_unit * 4) / tyre_lifespan
        
        # Calculate total tyre cost for the trip
        total_tyre_cost = tyre_cost_per_km * distance
        
        return CostComponent(
            component="Tyres",
            amount=round(total_tyre_cost, 2),
            description=f"4 tyres at KES {tyre_cost_per_unit} each, lasting {tyre_lifespan}km"
        )
