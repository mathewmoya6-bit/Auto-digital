"""
Environmental Engine - Auto-D Kenya
CO2 emissions and environmental impact calculations
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class EnvironmentalResult:
    """Environmental impact calculation result"""
    co2_kg: float = 0.0
    co2_per_km: float = 0.0
    fuel_consumed: float = 0.0
    co2_saved: float = 0.0
    trees_equivalent: float = 0.0


# ─── CO2 EMISSION FACTORS ──────────────────────────────────────────

CO2_FACTORS = {
    "petrol": 2.31,      # kg CO2 per litre
    "diesel": 2.68,      # kg CO2 per litre
    "electric": 0.00,    # Kenya is mostly renewable
    "hybrid": 1.50,      # kg CO2 per litre (combined)
    "lpg": 1.50,         # kg CO2 per kg
    "cng": 1.20,         # kg CO2 per kg
    "hydrogen": 0.00,    # Zero emissions if green hydrogen
    "kerosene": 2.45,    # kg CO2 per litre
    "ethanol": 1.80,     # kg CO2 per litre
    "methanol": 1.90     # kg CO2 per litre
}

# ─── TREE OFFSET ──────────────────────────────────────────────────

# Average tree absorbs ~22 kg CO2 per year
KG_CO2_PER_TREE_PER_YEAR = 22.0


class EnvironmentalEngine:
    """Professional environmental impact calculation engine"""
    
    @staticmethod
    def calculate_co2_emissions(
        fuel_type: str,
        fuel_consumption: float,
        distance_km: float
    ) -> EnvironmentalResult:
        """
        Calculate CO2 emissions for a trip.
        
        Args:
            fuel_type: Type of fuel
            fuel_consumption: Fuel consumption in L/100km or kWh/100km
            distance_km: Distance in kilometers
        
        Returns:
            EnvironmentalResult with CO2 breakdown
        """
        if distance_km <= 0 or fuel_consumption <= 0:
            return EnvironmentalResult()
        
        co2_factor = CO2_FACTORS.get(fuel_type, 2.31)
        
        # Calculate fuel used
        fuel_used = (distance_km / 100) * fuel_consumption
        
        # Calculate CO2 emissions
        co2_kg = fuel_used * co2_factor
        
        # Calculate trees needed to offset
        trees_equivalent = co2_kg / KG_CO2_PER_TREE_PER_YEAR
        
        return EnvironmentalResult(
            co2_kg=round(co2_kg, 2),
            co2_per_km=round(co2_kg / distance_km if distance_km > 0 else 0, 2),
            fuel_consumed=round(fuel_used, 2),
            trees_equivalent=round(trees_equivalent, 2)
        )
    
    @staticmethod
    def compare_vehicles(
        vehicle1: Dict[str, Any],
        vehicle2: Dict[str, Any],
        distance_km: float = 100
    ) -> Dict[str, Any]:
        """
        Compare CO2 emissions between two vehicles.
        
        Args:
            vehicle1: First vehicle data
            vehicle2: Second vehicle data
            distance_km: Distance in kilometers
        
        Returns:
            Dict with comparison results
        """
        result1 = EnvironmentalEngine.calculate_co2_emissions(
            fuel_type=vehicle1.get("fuel_type", "petrol"),
            fuel_consumption=vehicle1.get("fuel_consumption", 8),
            distance_km=distance_km
        )
        
        result2 = EnvironmentalEngine.calculate_co2_emissions(
            fuel_type=vehicle2.get("fuel_type", "petrol"),
            fuel_consumption=vehicle2.get("fuel_consumption", 8),
            distance_km=distance_km
        )
        
        co2_saved = abs(result1.co2_kg - result2.co2_kg)
        
        return {
            "vehicle1": {
                "name": vehicle1.get("name", "Vehicle 1"),
                "co2_kg": result1.co2_kg,
                "co2_per_km": result1.co2_per_km
            },
            "vehicle2": {
                "name": vehicle2.get("name", "Vehicle 2"),
                "co2_kg": result2.co2_kg,
                "co2_per_km": result2.co2_per_km
            },
            "co2_saved_kg": round(co2_saved, 2),
            "co2_saved_percentage": round(
                (co2_saved / max(result1.co2_kg, 0.001)) * 100, 1
            ),
            "trees_needed": round(co2_saved / KG_CO2_PER_TREE_PER_YEAR, 2)
        }


def calculate_co2_emissions(
    fuel_type: str,
    fuel_consumption: float,
    distance_km: float
) -> Dict[str, Any]:
    """
    Convenience function for CO2 calculation.
    
    Returns:
        Dict with CO2 breakdown
    """
    result = EnvironmentalEngine.calculate_co2_emissions(
        fuel_type=fuel_type,
        fuel_consumption=fuel_consumption,
        distance_km=distance_km
    )
    
    return {
        "co2_kg": result.co2_kg,
        "co2_per_km": result.co2_per_km,
        "fuel_consumed_litres": result.fuel_consumed,
        "trees_equivalent": result.trees_equivalent,
        "fuel_type": fuel_type,
        "distance_km": distance_km
    }


def compare_vehicle_emissions(
    vehicle1: Dict[str, Any],
    vehicle2: Dict[str, Any],
    distance_km: float = 100
) -> Dict[str, Any]:
    """
    Compare emissions between two vehicles.
    
    Returns:
        Dict with comparison results
    """
    return EnvironmentalEngine.compare_vehicles(
        vehicle1=vehicle1,
        vehicle2=vehicle2,
        distance_km=distance_km
    )


# ─── EXAMPLE USAGE ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("🌍 Environmental Impact Calculator")
    print("=" * 60)
    
    # Example: Petrol vs Electric
    result = calculate_co2_emissions(
        fuel_type="petrol",
        fuel_consumption=8,
        distance_km=100
    )
    
    print(f"\n🚗 Petrol Vehicle (8L/100km):")
    print(f"  CO2 Emissions: {result['co2_kg']} kg")
    print(f"  CO2 per km: {result['co2_per_km']} kg")
    print(f"  Trees needed to offset: {result['trees_equivalent']}")
    
    ev_result = calculate_co2_emissions(
        fuel_type="electric",
        fuel_consumption=15,
        distance_km=100
    )
    
    print(f"\n🔋 Electric Vehicle (15kWh/100km):")
    print(f"  CO2 Emissions: {ev_result['co2_kg']} kg")
    print(f"  CO2 per km: {ev_result['co2_per_km']} kg")
    print(f"  Trees needed to offset: {ev_result['trees_equivalent']}")
    
    print("\n" + "=" * 60)
