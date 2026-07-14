"""
Mileage and running cost calculations
Auto-D Kenya
"""

from services.fuel_service import get_fuel_price
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_mileage_cost(
    distance_km: float,
    fuel_type: str,
    fuel_consumption: float,
    maintenance_per_km: float = 0,
    insurance: float = 0,
    tax: float = 0
) -> Dict[str, Any]:
    """
    Calculate vehicle mileage and running cost.

    Args:
        distance_km: Distance travelled in kilometers
        fuel_type: petrol / diesel / electric / hybrid / lpg
        fuel_consumption: Litres per 100km (or kWh per 100km for electric)
        maintenance_per_km: Maintenance cost per kilometre
        insurance: Insurance cost for period
        tax: Tax/licensing cost for period

    Returns:
        Dict with cost breakdown including:
        - fuel_type: Type of fuel used
        - fuel_price: Price per unit (KES/litre or KES/kWh)
        - fuel_price_date: Date of fuel price
        - fuel_used_litres: Total fuel used in litres
        - fuel_cost: Total fuel cost in KES
        - maintenance_cost: Total maintenance cost in KES
        - total_cost: Total running cost in KES
        - cost_per_km: Cost per kilometre in KES
    """
    try:
        # Validate inputs
        distance_km = float(distance_km)
        fuel_consumption = float(fuel_consumption)
        maintenance_per_km = float(maintenance_per_km)
        insurance = float(insurance)
        tax = float(tax)

        if distance_km <= 0:
            return {
                "error": "Distance must be greater than 0",
                "fuel_type": fuel_type,
                "fuel_cost": 0,
                "maintenance_cost": 0,
                "total_cost": 0,
                "cost_per_km": 0
            }

        if fuel_consumption <= 0:
            return {
                "error": "Fuel consumption must be greater than 0",
                "fuel_type": fuel_type,
                "fuel_cost": 0,
                "maintenance_cost": 0,
                "total_cost": 0,
                "cost_per_km": 0
            }

    except (ValueError, TypeError) as e:
        return {
            "error": f"Invalid input: {str(e)}",
            "fuel_type": fuel_type,
            "fuel_cost": 0,
            "maintenance_cost": 0,
            "total_cost": 0,
            "cost_per_km": 0
        }

    # Get current fuel price automatically
    fuel = get_fuel_price(fuel_type)

    if not fuel:
        return {
            "error": f"Fuel type '{fuel_type}' not available",
            "fuel_type": fuel_type,
            "fuel_cost": 0,
            "maintenance_cost": 0,
            "total_cost": 0,
            "cost_per_km": 0
        }

    fuel_price = fuel.get("price", 0)
    effective_date = fuel.get("effective_date", None)

    # Calculate fuel consumption
    fuel_used = (distance_km / 100) * fuel_consumption
    fuel_cost = fuel_used * fuel_price

    # Calculate maintenance cost
    maintenance_cost = distance_km * maintenance_per_km

    # Calculate total cost
    total_cost = fuel_cost + maintenance_cost + insurance + tax
    cost_per_km = total_cost / distance_km if distance_km > 0 else 0

    return {
        "fuel_type": fuel_type,
        "fuel_price": round(fuel_price, 2),
        "fuel_price_date": effective_date,
        "fuel_used_litres": round(fuel_used, 2),
        "fuel_cost": round(fuel_cost, 2),
        "maintenance_cost": round(maintenance_cost, 2),
        "insurance_cost": round(insurance, 2),
        "tax_cost": round(tax, 2),
        "total_cost": round(total_cost, 2),
        "cost_per_km": round(cost_per_km, 2),
        "distance_km": distance_km,
        "fuel_consumption": fuel_consumption
    }


def calculate_mileage_cost_with_breakdown(
    distance_km: float,
    fuel_type: str,
    fuel_consumption: float,
    maintenance_per_km: float = 0,
    insurance: float = 0,
    tax: float = 0,
    include_breakdown: bool = True
) -> Dict[str, Any]:
    """
    Calculate vehicle mileage and running cost with detailed breakdown.

    Args:
        distance_km: Distance travelled in kilometers
        fuel_type: petrol / diesel / electric / hybrid / lpg
        fuel_consumption: Litres per 100km (or kWh per 100km for electric)
        maintenance_per_km: Maintenance cost per kilometre
        insurance: Insurance cost for period
        tax: Tax/licensing cost for period
        include_breakdown: Whether to include detailed breakdown

    Returns:
        Dict with cost breakdown including detailed component costs
    """
    result = calculate_mileage_cost(
        distance_km=distance_km,
        fuel_type=fuel_type,
        fuel_consumption=fuel_consumption,
        maintenance_per_km=maintenance_per_km,
        insurance=insurance,
        tax=tax
    )

    if "error" in result:
        return result

    if include_breakdown:
        # Add detailed breakdown components
        result["breakdown"] = {
            "fuel": {
                "percentage": (result["fuel_cost"] / result["total_cost"] * 100) if result["total_cost"] > 0 else 0,
                "description": f"Fuel cost at KES {result['fuel_price']}/litre"
            },
            "maintenance": {
                "percentage": (result["maintenance_cost"] / result["total_cost"] * 100) if result["total_cost"] > 0 else 0,
                "description": f"Maintenance at KES {maintenance_per_km}/km"
            },
            "insurance": {
                "percentage": (insurance / result["total_cost"] * 100) if result["total_cost"] > 0 else 0,
                "description": "Insurance cost"
            },
            "tax": {
                "percentage": (tax / result["total_cost"] * 100) if result["total_cost"] > 0 else 0,
                "description": "Tax/licensing cost"
            }
        }

    return result


def calculate_mileage_for_route(
    route_data: Dict[str, Any],
    vehicle_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate mileage cost for a specific route with vehicle data.

    Args:
        route_data: Dict with route information (distance, terrain, etc.)
        vehicle_data: Dict with vehicle information (fuel_type, consumption, etc.)

    Returns:
        Dict with cost breakdown for the route
    """
    distance_km = route_data.get("distance_km", 0)
    terrain_factor = route_data.get("terrain_factor", 1.0)  # 1.0 = flat, 1.2 = hilly, etc.

    # Adjust fuel consumption based on terrain
    base_consumption = vehicle_data.get("fuel_consumption", 8)
    adjusted_consumption = base_consumption * terrain_factor

    return calculate_mileage_cost(
        distance_km=distance_km,
        fuel_type=vehicle_data.get("fuel_type", "petrol"),
        fuel_consumption=adjusted_consumption,
        maintenance_per_km=vehicle_data.get("maintenance_per_km", 0),
        insurance=vehicle_data.get("insurance", 0),
        tax=vehicle_data.get("tax", 0)
    )


def get_fuel_estimate(
    distance_km: float,
    fuel_type: str,
    fuel_consumption: float
) -> Dict[str, Any]:
    """
    Get a quick fuel-only estimate without full cost breakdown.

    Args:
        distance_km: Distance travelled in kilometers
        fuel_type: petrol / diesel / electric / hybrid / lpg
        fuel_consumption: Litres per 100km (or kWh per 100km for electric)

    Returns:
        Dict with fuel estimate
    """
    result = calculate_mileage_cost(
        distance_km=distance_km,
        fuel_type=fuel_type,
        fuel_consumption=fuel_consumption,
        maintenance_per_km=0,
        insurance=0,
        tax=0
    )

    if "error" in result:
        return result

    return {
        "fuel_type": result["fuel_type"],
        "fuel_price": result["fuel_price"],
        "fuel_used_litres": result["fuel_used_litres"],
        "fuel_cost": result["fuel_cost"],
        "cost_per_km": result["cost_per_km"],
        "distance_km": distance_km
    }


# ─── BACKEND API COMPATIBILITY FUNCTION ──────────────────────

def calculate_mileage_for_api(
    distance_km: float,
    fuel_type: str = "petrol",
    fuel_consumption: float = None,
    maintenance_per_km: float = 0,
    insurance: float = 0,
    tax: float = 0
) -> Dict[str, Any]:
    """
    API-compatible version of calculate_mileage_cost.
    Matches the expected format for the /api/service/mileage endpoint.

    Args:
        distance_km: Distance travelled in kilometers
        fuel_type: petrol / diesel / electric / hybrid / lpg
        fuel_consumption: Litres per 100km (or km/l if provided as string)
        maintenance_per_km: Maintenance cost per kilometre
        insurance: Insurance cost for period
        tax: Tax/licensing cost for period

    Returns:
        Dict with cost breakdown in API format
    """
    # Handle case where fuel_consumption is provided as km/l instead of L/100km
    if fuel_consumption is not None and fuel_consumption < 10:
        # If fuel_consumption is less than 10, assume it's km/l and convert to L/100km
        fuel_consumption = 100 / fuel_consumption

    result = calculate_mileage_cost(
        distance_km=distance_km,
        fuel_type=fuel_type,
        fuel_consumption=fuel_consumption or 8,
        maintenance_per_km=maintenance_per_km,
        insurance=insurance,
        tax=tax
    )

    if "error" in result:
        return {"success": False, "error": result["error"]}

    return {
        "success": True,
        "data": {
            "distance_km": result["distance_km"],
            "fuel_type": result["fuel_type"],
            "fuel_consumption": result["fuel_consumption"],
            "fuel_price": result["fuel_price"],
            "fuel_cost": result["fuel_cost"],
            "maintenance_cost": result["maintenance_cost"],
            "insurance_cost": result["insurance_cost"],
            "tax_cost": result["tax_cost"],
            "total_cost": result["total_cost"],
            "cost_per_km": result["cost_per_km"]
        }
    }


# ─── EXAMPLE USAGE ─────────────────────────────────────────────

if __name__ == "__main__":
    # Example 1: Basic mileage calculation
    result = calculate_mileage_cost(
        distance_km=100,
        fuel_type="petrol",
        fuel_consumption=8,
        maintenance_per_km=2,
        insurance=5000,
        tax=2000
    )
    print("Basic Mileage Calculation:")
    print(f"Total Cost: KES {result['total_cost']}")
    print(f"Cost per km: KES {result['cost_per_km']}")
    print("-" * 40)

    # Example 2: Route calculation
    route = {"distance_km": 150, "terrain_factor": 1.1}
    vehicle = {"fuel_type": "diesel", "fuel_consumption": 7, "maintenance_per_km": 2.5}
    result2 = calculate_mileage_for_route(route, vehicle)
    print("Route Calculation:")
    print(f"Total Cost: KES {result2['total_cost']}")
    print(f"Cost per km: KES {result2['cost_per_km']}")
    print("-" * 40)

    # Example 3: API-compatible calculation
    result3 = calculate_mileage_for_api(
        distance_km=200,
        fuel_type="electric",
        fuel_consumption=15,
        maintenance_per_km=1.5
    )
    print("API-Compatible Calculation:")
    print(f"Total Cost: KES {result3['data']['total_cost']}")
    print(f"Cost per km: KES {result3['data']['cost_per_km']}")
