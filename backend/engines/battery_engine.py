"""
Battery Engine - Auto-D Kenya
EV battery degradation and replacement reserve
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class BatteryResult:
    """Battery calculation result"""
    cost_per_km: float = 0.0
    trip_reserve: float = 0.0
    annual_reserve: float = 0.0
    battery_life_km: float = 0.0
    replacement_cost: float = 0.0
    battery_capacity: float = 0.0
    degradation_per_year: float = 0.0


# ─── BATTERY DATA ──────────────────────────────────────────────────

BATTERY_DATA = {
    "default": {
        "cost_per_kwh": 15000,  # KES per kWh
        "life_km": 250000,
        "degradation_per_year": 0.02  # 2% per year
    },
    "Tesla": {
        "cost_per_kwh": 18000,
        "life_km": 300000,
        "degradation_per_year": 0.015
    },
    "Nissan_Leaf": {
        "cost_per_kwh": 12000,
        "life_km": 150000,
        "degradation_per_year": 0.035
    },
    "Toyota_bZ4X": {
        "cost_per_kwh": 16000,
        "life_km": 200000,
        "degradation_per_year": 0.02
    }
}

# ─── BATTERY ENGINE ────────────────────────────────────────────────

class BatteryEngine:
    """Professional EV battery cost engine"""
    
    @staticmethod
    def calculate_reserve(
        battery_capacity: float,  # kWh
        distance_km: float,
        make: str = "",
        model: str = "",
        annual_km: float = 20000,
        age_years: int = 0
    ) -> BatteryResult:
        """
        Calculate battery replacement reserve.
        
        Args:
            battery_capacity: Battery capacity in kWh
            distance_km: Trip distance
            make: Vehicle make
            model: Vehicle model
            annual_km: Annual mileage
            age_years: Vehicle age
        
        Returns:
            BatteryResult with reserve breakdown
        """
        # Get battery data
        battery_key = make if make in BATTERY_DATA else "default"
        if model and f"{make}_{model}" in BATTERY_DATA:
            battery_key = f"{make}_{model}"
        
        battery_data = BATTERY_DATA.get(battery_key, BATTERY_DATA["default"])
        
        cost_per_kwh = battery_data["cost_per_kwh"]
        base_life_km = battery_data["life_km"]
        degradation = battery_data["degradation_per_year"]
        
        # Adjust life based on age
        age_factor = 1 - (age_years * degradation)
        battery_life_km = base_life_km * age_factor
        battery_life_km = max(battery_life_km, base_life_km * 0.6)  # Minimum 60% life
        
        # Replacement cost
        replacement_cost = battery_capacity * cost_per_kwh
        
        cost_per_km = replacement_cost / battery_life_km
        trip_reserve = distance_km * cost_per_km
        annual_reserve = annual_km * cost_per_km
        
        return BatteryResult(
            cost_per_km=round(cost_per_km, 4),
            trip_reserve=round(trip_reserve, 2),
            annual_reserve=round(annual_reserve, 2),
            battery_life_km=round(battery_life_km, 2),
            replacement_cost=round(replacement_cost, 2),
            battery_capacity=battery_capacity,
            degradation_per_year=degradation
        )


def calculate_battery_reserve(
    battery_capacity: float,
    distance_km: float,
    battery_life_km: float
