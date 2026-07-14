"""
Tyre Engine - Auto-D Kenya
Professional tyre cost calculator
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class TyreResult:
    """Tyre calculation result"""
    cost_per_km: float = 0.0
    trip_cost: float = 0.0
    annual_cost: float = 0.0
    tyre_size: str = ""
    total_tyre_cost: float = 0.0
    tyre_life_km: float = 0.0


# ─── TYRE DATABASE ──────────────────────────────────────────────────

TYRE_DATA = {
    "195/65R15": {"cost": 18000, "life_km": 45000},
    "205/55R16": {"cost": 20000, "life_km": 45000},
    "215/55R17": {"cost": 22000, "life_km": 50000},
    "225/45R17": {"cost": 25000, "life_km": 45000},
    "225/55R17": {"cost": 24000, "life_km": 50000},
    "225/60R17": {"cost": 26000, "life_km": 50000},
    "235/55R18": {"cost": 30000, "life_km": 50000},
    "245/45R18": {"cost": 32000, "life_km": 45000},
    "255/55R18": {"cost": 35000, "life_km": 45000},
    "265/60R18": {"cost": 38000, "life_km": 50000},
    "265/65R17": {"cost": 32000, "life_km": 50000},
    "265/70R16": {"cost": 28000, "life_km": 50000},
    "285/60R18": {"cost": 45000, "life_km": 45000},
    "175/65R14": {"cost": 14000, "life_km": 40000},
    "185/60R15": {"cost": 16000, "life_km": 40000},
    "default": {"cost": 25000, "life_km": 45000}
}

# ─── TYRE ENGINE ──────────────────────────────────────────────────

class TyreEngine:
    """Professional tyre cost calculation engine"""
    
    @staticmethod
    def calculate(
        tyre_size: str,
        distance_km: float,
        tyre_count: int = 4,
        annual_km: float = 20000,
        include_installation: bool = True,
        include_rotation: bool = True,
        include_balancing: bool = True
    ) -> TyreResult:
        """
        Calculate tyre costs.
        
        Args:
            tyre_size: Tyre size string
            distance_km: Trip distance
            tyre_count: Number of tyres
            annual_km: Annual mileage
            include_installation: Include installation cost
            include_rotation: Include rotation cost
            include_balancing: Include balancing cost
        
        Returns:
            TyreResult with cost breakdown
        """
        tyre_data = TYRE_DATA.get(tyre_size, TYRE_DATA["default"])
        
        cost_per_tyre = tyre_data["cost"]
        tyre_life_km = tyre_data["life_km"]
        
        # Additional costs
        installation_per_tyre = 500 if include_installation else 0
        rotation_cost = 1000 if include_rotation else 0  # Per rotation
        balancing_per_tyre = 300 if include_balancing else 0
        
        total_tyre_cost = (
            (cost_per_tyre + installation_per_tyre + balancing_per_tyre) *
            tyre_count
        ) + rotation_cost
        
        cost_per_km = total_tyre_cost / tyre_life_km
        trip_cost = distance_km * cost_per_km
        annual_cost = annual_km * cost_per_km
        
        return TyreResult(
            cost_per_km=round(cost_per_km, 4),
            trip_cost=round(trip_cost, 2),
            annual_cost=round(annual_cost, 2),
            tyre_size=tyre_size,
            total_tyre_cost=round(total_tyre_cost, 2),
            tyre_life_km=tyre_life_km
        )


def calculate_tyre_cost(
    tyre_size: str,
    distance_km: float,
    tyre_count: int = 4,
    annual_km: float = 20000
) -> Dict[str, Any]:
    """Convenience function for tyre cost calculation"""
    result = TyreEngine.calculate(
        tyre_size=tyre_size,
        distance_km=distance_km,
        tyre_count=tyre_count,
        annual_km=annual_km
    )
    
    return {
        "tyre_size": result.tyre_size,
        "cost_per_km": result.cost_per_km,
        "trip_cost": result.trip_cost,
        "annual_cost": result.annual_cost,
        "total_tyre_cost": result.total_tyre_cost,
        "tyre_life_km": result.tyre_life_km
    }
