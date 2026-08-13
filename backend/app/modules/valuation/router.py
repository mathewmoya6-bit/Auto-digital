# app/modules/valuation/engine.py
# ================================================================
# Auto-D Kenya - Valuation Engine
# ================================================================
# TYPE: MODULE - Valuation calculation engine
# ================================================================

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ValuationEngine:
    """
    Vehicle valuation calculation engine.
    
    This is a lightweight wrapper around the repository's valuation logic.
    It provides additional business logic and validation.
    """
    
    def __init__(self):
        logger.info("ValuationEngine initialized")
    
    def calculate(
        self,
        base_value: float,
        year: int,
        mileage: int,
        condition: str = "good",
        accident_history: str = "none",
        previous_owners: int = 1,
        location: str = "nairobi",
        fuel_type: Optional[str] = None,
        transmission: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        profit_margin: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Calculate valuation based on base value and adjustments.
        
        Args:
            base_value: Base vehicle value
            year: Manufacture year
            mileage: Odometer reading
            condition: Vehicle condition
            accident_history: Accident history
            previous_owners: Number of previous owners
            location: Vehicle location
            fuel_type: Fuel type
            transmission: Transmission type
            vehicle_type: Vehicle type
            profit_margin: Profit margin percentage
            
        Returns:
            Dict[str, Any]: Valuation results with all adjustments
        """
        # Calculate age
        from datetime import datetime, timezone
        current_year = datetime.now(timezone.utc).year
        age = max(0, current_year - year)
        
        # Depreciation rate
        depreciation_rate = self._get_depreciation_rate(age, vehicle_type)
        
        # Adjustment factors
        mileage_factor = self._get_mileage_factor(mileage, age)
        condition_factor = self._get_condition_factor(condition)
        accident_factor = self._get_accident_factor(accident_history)
        owner_factor = self._get_owner_factor(previous_owners)
        location_factor = self._get_location_factor(location)
        fuel_factor = self._get_fuel_factor(fuel_type)
        transmission_factor = self._get_transmission_factor(transmission)
        
        # Apply adjustments
        adjusted_value = (
            base_value
            * (1.0 - depreciation_rate)
            * mileage_factor
            * condition_factor
            * accident_factor
            * owner_factor
            * location_factor
            * fuel_factor
            * transmission_factor
        )
        
        final_value = max(round(adjusted_value, 2), 0.0)
        
        # Market values
        retail_value = round(final_value * 1.08, 2)
        trade_value = round(final_value * 0.85, 2)
        dealer_value = round(final_value * 0.95, 2)
        
        return {
            "market_value": final_value,
            "retail_value": retail_value,
            "trade_value": trade_value,
            "dealer_value": dealer_value,
            "depreciation_rate": round(depreciation_rate * 100, 1),
            "adjustments": {
                "age": age,
                "mileage_factor": round(mileage_factor, 2),
                "condition_factor": round(condition_factor, 2),
                "accident_factor": round(accident_factor, 2),
                "owner_factor": round(owner_factor, 2),
                "location_factor": round(location_factor, 2),
                "fuel_factor": round(fuel_factor, 2),
                "transmission_factor": round(transmission_factor, 2),
            }
        }
    
    # ─── Adjustment Factors ──────────────────────────────────────────
    
    def _get_depreciation_rate(self, age: int, vehicle_type: Optional[str] = None) -> float:
        if age <= 1:
            return 0.10
        elif age <= 3:
            return 0.20
        elif age <= 5:
            return 0.30
        elif age <= 8:
            return 0.45
        elif age <= 12:
            return 0.60
        else:
            return 0.70
    
    def _get_mileage_factor(self, mileage: int, age: int) -> float:
        if mileage <= 0:
            return 1.0
        expected = max(15000 * max(age, 1), 1000)
        ratio = mileage / expected
        if ratio <= 0.75:
            return 1.03
        elif ratio <= 1.25:
            return 1.00
        elif ratio <= 1.75:
            return 0.95
        elif ratio <= 2.50:
            return 0.88
        else:
            return 0.80
    
    def _get_condition_factor(self, condition: str) -> float:
        factors = {
            "excellent": 1.10,
            "very_good": 1.05,
            "good": 1.00,
            "fair": 0.90,
            "poor": 0.75,
        }
        return factors.get(condition.lower(), 1.00)
    
    def _get_accident_factor(self, accident_history: str) -> float:
        factors = {
            "none": 1.00,
            "minor": 0.92,
            "major": 0.75,
            "total_loss": 0.35,
        }
        return factors.get(accident_history.lower(), 1.00)
    
    def _get_owner_factor(self, previous_owners: int) -> float:
        if previous_owners <= 1:
            return 1.00
        elif previous_owners <= 2:
            return 0.98
        elif previous_owners <= 3:
            return 0.95
        elif previous_owners <= 4:
            return 0.92
        else:
            return 0.88
    
    def _get_location_factor(self, location: str) -> float:
        factors = {
            "nairobi": 1.02,
            "mombasa": 1.00,
            "kisumu": 0.98,
            "nakuru": 0.98,
            "eldoret": 0.97,
            "thika": 0.97,
            "kiambu": 1.00,
            "kajiado": 0.98,
            "machakos": 0.97,
            "meru": 0.96,
            "nyeri": 0.96,
            "embu": 0.95,
            "malindi": 0.98,
            "nanyuki": 0.97,
        }
        return factors.get(location.lower(), 0.95)
    
    def _get_fuel_factor(self, fuel_type: Optional[str]) -> float:
        if not fuel_type:
            return 1.0
        factors = {
            "petrol": 1.00,
            "diesel": 1.02,
            "electric": 1.05,
            "lpg": 0.95,
        }
        return factors.get(fuel_type.lower(), 1.00)
    
    def _get_transmission_factor(self, transmission: Optional[str]) -> float:
        if not transmission:
            return 1.0
        factors = {
            "manual": 0.95,
            "automatic": 1.00,
            "cvt": 0.98,
            "amt": 0.97,
        }
        return factors.get(transmission.lower(), 1.00)


# ================================================================
# EXPORTS
# ================================================================

__all__ = ["ValuationEngine"]
