# backend/app/engines/finance_engine.py
from typing import Dict, Any
from app.schemas.response import CostComponent

class FinanceEngine:
    def calculate(self, vehicle: Dict[str, Any], distance: float) -> CostComponent:
        """Calculate finance cost if vehicle is financed"""
        market_value = vehicle.get("market_value", 5000000)
        
        # For now, return zero as this is optional
        # In future, could calculate interest on vehicle loan
        finance_cost = 0
        
        return CostComponent(
            component="Finance",
            amount=0.0,
            description="No finance costs included"
        )
