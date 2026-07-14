"""
Battery Engine - Auto-D Kenya
EV battery degradation and replacement reserve
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


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
    },
    "Hyundai_Kona": {
        "cost_per_kwh": 17000,
        "life_km": 200000,
        "degradation_per_year": 0.018
    },
    "BMW_i3": {
        "cost_per_kwh": 20000,
        "life_km": 150000,
        "degradation_per_year": 0.025
    },
    "Mercedes_EQC": {
        "cost_per_kwh": 19000,
        "life_km": 180000,
        "degradation_per_year": 0.02
    },
    "Audi_e_tron": {
        "cost_per_kwh": 18500,
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
        age_years: int = 0,
        replacement_cost: Optional[float] = None
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
            replacement_cost: Optional manual override for replacement cost
        
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
        if replacement_cost is None:
            replacement_cost = battery_capacity * cost_per_kwh
        
        cost_per_km = replacement_cost / battery_life_km if battery_life_km > 0 else 0
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
    
    @staticmethod
    def estimate_battery_life(
        battery_capacity: float,
        make: str = "",
        model: str = "",
        age_years: int = 0,
        annual_km: float = 20000
    ) -> Dict[str, Any]:
        """
        Estimate remaining battery life.
        
        Returns:
            Dict with battery life estimates
        """
        battery_key = make if make in BATTERY_DATA else "default"
        if model and f"{make}_{model}" in BATTERY_DATA:
            battery_key = f"{make}_{model}"
        
        battery_data = BATTERY_DATA.get(battery_key, BATTERY_DATA["default"])
        
        base_life_km = battery_data["life_km"]
        degradation = battery_data["degradation_per_year"]
        
        # Calculate remaining life
        age_factor = 1 - (age_years * degradation)
        remaining_life = base_life_km * age_factor
        remaining_life = max(remaining_life, base_life_km * 0.5)
        
        # Calculate replacement cost
        cost_per_kwh = battery_data["cost_per_kwh"]
        replacement_cost = battery_capacity * cost_per_kwh
        
        return {
            "battery_capacity": battery_capacity,
            "base_life_km": base_life_km,
            "remaining_life_km": round(remaining_life, 2),
            "degradation_rate": degradation,
            "replacement_cost": round(replacement_cost, 2),
            "cost_per_km": round(replacement_cost / remaining_life if remaining_life > 0 else 0, 2),
            "annual_reserve": round((replacement_cost / remaining_life) * annual_km if remaining_life > 0 else 0, 2)
        }


def calculate_battery_reserve(
    battery_capacity: float,
    distance_km: float,
    battery_life_km: float = 250000,
    replacement_cost: Optional[float] = None,
    annual_km: float = 20000,
    make: str = "",
    model: str = ""
) -> Dict[str, Any]:
    """
    Convenience function for battery reserve calculation.
    
    Args:
        battery_capacity: Battery capacity in kWh
        distance_km: Trip distance
        battery_life_km: Expected battery life in km
        replacement_cost: Cost to replace battery
        annual_km: Annual mileage
        make: Vehicle make
        model: Vehicle model
    
    Returns:
        Dict with battery reserve breakdown
    """
    engine = BatteryEngine()
    
    # Estimate replacement cost if not provided
    if replacement_cost is None:
        battery_key = make if make in BATTERY_DATA else "default"
        if model and f"{make}_{model}" in BATTERY_DATA:
            battery_key = f"{make}_{model}"
        battery_data = BATTERY_DATA.get(battery_key, BATTERY_DATA["default"])
        cost_per_kwh = battery_data.get("cost_per_kwh", 15000)
        replacement_cost = battery_capacity * cost_per_kwh
    
    result = engine.calculate_reserve(
        battery_capacity=battery_capacity,
        distance_km=distance_km,
        make=make,
        model=model,
        annual_km=annual_km,
        replacement_cost=replacement_cost
    )
    
    return {
        "battery_capacity": result.battery_capacity,
        "battery_life_km": result.battery_life_km,
        "replacement_cost": result.replacement_cost,
        "cost_per_km": result.cost_per_km,
        "trip_reserve": result.trip_reserve,
        "annual_reserve": result.annual_reserve
    }


def calculate_battery_degradation(
    battery_capacity: float,
    age_years: int,
    make: str = "",
    model: str = ""
) -> Dict[str, Any]:
    """
    Calculate battery degradation over time.
    
    Returns:
        Dict with degradation analysis
    """
    battery_key = make if make in BATTERY_DATA else "default"
    if model and f"{make}_{model}" in BATTERY_DATA:
        battery_key = f"{make}_{model}"
    
    battery_data = BATTERY_DATA.get(battery_key, BATTERY_DATA["default"])
    
    degradation_rate = battery_data.get("degradation_per_year", 0.02)
    base_capacity = battery_capacity
    
    yearly_degradation = []
    current_capacity = base_capacity
    
    for year in range(1, min(age_years + 1, 15)):
        loss = current_capacity * degradation_rate
        current_capacity -= loss
        yearly_degradation.append({
            "year": year,
            "capacity": round(current_capacity, 2),
            "capacity_retained": round((current_capacity / base_capacity) * 100, 2),
            "loss": round(loss, 2)
        })
    
    return {
        "battery_capacity": battery_capacity,
        "degradation_rate": degradation_rate,
        "current_capacity": round(current_capacity, 2),
        "capacity_retained": round((current_capacity / base_capacity) * 100, 2),
        "yearly_degradation": yearly_degradation
    }


# ─── EXAMPLE USAGE ─────────────────────────────────────────────

if __name__ == "__main__":
    # Example: Tesla Model 3 battery reserve
    print("=" * 60)
    print("🔋 EV Battery Reserve Calculator")
    print("=" * 60)
    
    result = calculate_battery_reserve(
        battery_capacity=75,
        distance_km=100,
        make="Tesla",
        model="Model_3",
        annual_km=20000
    )
    
    print(f"Battery Capacity: {result['battery_capacity']} kWh")
    print(f"Battery Life: {result['battery_life_km']:,} km")
    print(f"Replacement Cost: KES {result['replacement_cost']:,.2f}")
    print(f"Cost per km: KES {result['cost_per_km']:.4f}")
    print(f"Trip Reserve: KES {result['trip_reserve']:.2f}")
    print(f"Annual Reserve: KES {result['annual_reserve']:.2f}")
    print("=" * 60)
    
    # Example 2: Degradation analysis
    print("\n📊 Battery Degradation Analysis")
    print("-" * 40)
    
    degradation = calculate_battery_degradation(
        battery_capacity=75,
        age_years=5,
        make="Tesla",
        model="Model_3"
    )
    
    print(f"Current Capacity: {degradation['current_capacity']:.2f} kWh")
    print(f"Capacity Retained: {degradation['capacity_retained']:.1f}%")
    print(f"Yearly Degradation:")
    for year in degradation['yearly_degradation'][:3]:
        print(f"  Year {year['year']}: {year['capacity']:.2f} kWh ({year['capacity_retained']:.1f}%)")
    print("=" * 60)
