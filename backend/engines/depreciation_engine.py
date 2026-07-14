"""
Depreciation Engine - Auto-D Kenya
Professional declining balance depreciation with market factors
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class DepreciationResult:
    """Depreciation calculation result"""
    current_value: float = 0.0
    total_depreciation: float = 0.0
    value_retained: float = 0.0
    depreciation_rate: float = 0.0
    yearly_breakdown: List[Dict[str, Any]] = field(default_factory=list)


# ─── DEPRECIATION RATES BY VEHICLE TYPE ────────────────────────────

DEPRECIATION_RATES = {
    "Car": {
        1: 0.20,   # Year 1: 20%
        2: 0.15,   # Year 2: 15%
        3: 0.12,   # Year 3: 12%
        4: 0.10,   # Year 4: 10%
        5: 0.08,   # Year 5: 8%
        6: 0.06,   # Year 6: 6%
        7: 0.05,   # Year 7: 5%
        8: 0.04,   # Year 8+: 4%
    },
    "Bike": {
        1: 0.25, 2: 0.18, 3: 0.14, 4: 0.11, 5: 0.09, 6: 0.07
    },
    "Tricycle": {
        1: 0.28, 2: 0.20, 3: 0.16, 4: 0.12, 5: 0.10, 6: 0.08
    },
    "Truck": {
        1: 0.18, 2: 0.14, 3: 0.11, 4: 0.09, 5: 0.07, 6: 0.05
    }
}

# ─── CONDITION MULTIPLIERS ──────────────────────────────────────────

CONDITION_MULTIPLIERS = {
    "Excellent": 0.85,
    "Good": 1.00,
    "Fair": 1.20,
    "Poor": 1.40
}

# ─── DEPRECIATION ENGINE ────────────────────────────────────────────

class DepreciationEngine:
    """Professional depreciation calculation engine"""
    
    @staticmethod
    def calculate(
        purchase_price: float,
        age_years: int,
        vehicle_type: str = "Car",
        condition: str = "Good",
        mileage: float = 0,
        market_adjustment: float = 1.0
    ) -> DepreciationResult:
        """
        Calculate depreciation using declining balance method.
        
        Args:
            purchase_price: Original purchase price
            age_years: Age of vehicle in years
            vehicle_type: Car, Bike, Tricycle, Truck
            condition: Excellent, Good, Fair, Poor
            mileage: Total mileage
            market_adjustment: Market condition factor
        
        Returns:
            DepreciationResult with full breakdown
        """
        rates = DEPRECIATION_RATES.get(vehicle_type, DEPRECIATION_RATES["Car"])
        cond_mult = CONDITION_MULTIPLIERS.get(condition, 1.0)
        
        # Mileage adjustment
        mileage_mult = 1.0
        if mileage > 150000:
            mileage_mult = 1.30
        elif mileage > 100000:
            mileage_mult = 1.15
        elif mileage > 60000:
            mileage_mult = 1.05
        
        current_value = purchase_price
        total_depreciation = 0
        yearly_breakdown = []
        
        for year in range(1, min(age_years + 1, 10)):
            # Get rate for this year, fall back to last available
            year_rate = rates.get(year, rates.get(8, 0.04))
            # Apply condition, mileage, and market adjustments
            adjusted_rate = min(
                year_rate * cond_mult * mileage_mult * market_adjustment,
                0.50
            )
            
            dep_amount = current_value * adjusted_rate
            current_value -= dep_amount
            total_depreciation += dep_amount
            
            yearly_breakdown.append({
                "year": year,
                "depreciation": round(dep_amount, 2),
                "depreciation_rate": round(adjusted_rate, 4),
                "value": round(max(current_value, purchase_price * 0.05), 2),
                "value_retained": round((current_value / purchase_price) * 100, 2)
            })
        
        final_value = max(current_value, purchase_price * 0.05)
        
        return DepreciationResult(
            current_value=round(final_value, 2),
            total_depreciation=round(total_depreciation, 2),
            value_retained=round((final_value / purchase_price) * 100, 2),
            depreciation_rate=adjusted_rate,
            yearly_breakdown=yearly_breakdown
        )


def calculate_depreciation(
    purchase_price: float,
    age_years: int,
    vehicle_type: str = "Car",
    condition: str = "Good",
    mileage: float = 0,
    market_adjustment: float = 1.0
) -> Dict[str, Any]:
    """Convenience function for depreciation calculation"""
    result = DepreciationEngine.calculate(
        purchase_price=purchase_price,
        age_years=age_years,
        vehicle_type=vehicle_type,
        condition=condition,
        mileage=mileage,
        market_adjustment=market_adjustment
    )
    
    return {
        "current_value": result.current_value,
        "total_depreciation": result.total_depreciation,
        "value_retained": result.value_retained,
        "depreciation_rate": result.depreciation_rate,
        "yearly_breakdown": result.yearly_breakdown
    }
