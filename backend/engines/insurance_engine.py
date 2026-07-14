"""
Insurance Engine - Auto-D Kenya
Professional insurance estimation
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class InsuranceResult:
    """Insurance calculation result"""
    annual_premium: float = 0.0
    monthly_premium: float = 0.0
    rate: float = 0.0
    coverage_type: str = ""
    vehicle_value: float = 0.0


# ─── INSURANCE RATES ────────────────────────────────────────────────

INSURANCE_RATES = {
    "Car": {
        "comprehensive": 0.045,
        "third_party": 0.012,
        "third_party_fire": 0.025,
        "fleet": 0.035,
        "commercial": 0.050
    },
    "Bike": {
        "comprehensive": 0.050,
        "third_party": 0.020,
        "commercial": 0.055
    },
    "Tricycle": {
        "comprehensive": 0.055,
        "third_party": 0.025,
        "commercial": 0.060
    },
    "Truck": {
        "comprehensive": 0.040,
        "third_party": 0.015,
        "fleet": 0.030,
        "commercial": 0.045
    }
}

# ─── INSURANCE ENGINE ──────────────────────────────────────────────

class InsuranceEngine:
    """Professional insurance estimation engine"""
    
    @staticmethod
    def estimate(
        vehicle_value: float,
        vehicle_type: str = "Car",
        coverage_type: str = "comprehensive",
        usage: str = "Personal",
        driver_age: int = 35,
        driver_experience: int = 10,
        claims_history: int = 0
    ) -> InsuranceResult:
        """
        Estimate insurance cost.
        
        Args:
            vehicle_value: Current vehicle value
            vehicle_type: Car, Bike, Tricycle, Truck
            coverage_type: comprehensive, third_party, third_party_fire, fleet, commercial
            usage: Personal, Commercial
            driver_age: Age of main driver
            driver_experience: Years of driving experience
            claims_history: Number of claims in last 3 years
        
        Returns:
            InsuranceResult with premium breakdown
        """
        rates = INSURANCE_RATES.get(vehicle_type, INSURANCE_RATES["Car"])
        base_rate = rates.get(coverage_type, 0.045)
        
        # Driver factor (younger drivers = higher risk)
        if driver_age < 25:
            driver_factor = 1.4
        elif driver_age < 30:
            driver_factor = 1.2
        elif driver_age < 40:
            driver_factor = 1.0
        elif driver_age < 50:
            driver_factor = 0.9
        else:
            driver_factor = 0.85
        
        # Experience factor
        if driver_experience < 1:
            exp_factor = 1.3
        elif driver_experience < 3:
            exp_factor = 1.1
        elif driver_experience < 5:
            exp_factor = 1.0
        else:
            exp_factor = 0.9
        
        # Claims history factor
        claims_factor = 1.0 + (claims_history * 0.15)
        
        # Usage factor
        usage_factor = 1.2 if usage == "Commercial" else 1.0
        
        effective_rate = (
            base_rate *
            driver_factor *
            exp_factor *
            claims_factor *
            usage_factor
        )
        
        annual_premium = vehicle_value * effective_rate
        annual_premium = max(annual_premium, 3000)  # Minimum premium
        
        return InsuranceResult(
            annual_premium=round(annual_premium, 2),
            monthly_premium=round(annual_premium / 12, 2),
            rate=round(effective_rate, 4),
            coverage_type=coverage_type,
            vehicle_value=vehicle_value
        )


def estimate_insurance(
    vehicle_value: float,
    vehicle_type: str = "Car",
    coverage_type: str = "comprehensive",
    usage: str = "Personal"
) -> Dict[str, Any]:
    """Convenience function for insurance estimation"""
    result = InsuranceEngine.estimate(
        vehicle_value=vehicle_value,
        vehicle_type=vehicle_type,
        coverage_type=coverage_type,
        usage=usage
    )
    
    return {
        "annual_premium": result.annual_premium,
        "monthly_premium": result.monthly_premium,
        "rate": result.rate,
        "coverage_type": result.coverage_type,
        "vehicle_value": result.vehicle_value,
        "estimated": True
    }
