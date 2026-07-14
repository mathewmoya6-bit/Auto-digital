"""
Maintenance Engine - Auto-D Kenya
Professional service scheduling and cost calculation
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class MaintenanceResult:
    """Maintenance calculation result"""
    trip_cost: float = 0.0
    annual_cost: float = 0.0
    cost_per_km: float = 0.0
    service_interval: int = 0
    next_service_km: float = 0.0


# ─── SERVICE COSTS ──────────────────────────────────────────────────

SERVICE_COSTS = {
    "minor": 15000,
    "major": 45000,
    "brake_pads": 8000,
    "brake_discs": 25000,
    "oil_change": 5000,
    "transmission": 35000,
    "cooling": 12000,
    "filters": 3000,
    "suspension": 45000,
    "battery_12v": 12000,
    "air_con": 15000,
    "timing_belt": 25000,
    "clutch": 30000,
    "alternator": 18000,
    "starter": 12000,
    "spark_plugs": 6000,
    "fuel_filter": 4000
}

# ─── VEHICLE SERVICE SCHEDULES ─────────────────────────────────────

SERVICE_SCHEDULES = {
    "Toyota": {
        "Prado": {"interval": 10000, "minor_cost": 15000, "major_cost": 45000},
        "Hilux": {"interval": 10000, "minor_cost": 14000, "major_cost": 42000},
        "Corolla": {"interval": 15000, "minor_cost": 10000, "major_cost": 30000},
        "default": {"interval": 10000, "minor_cost": 12000, "major_cost": 35000}
    },
    "Nissan": {
        "X-Trail": {"interval": 15000, "minor_cost": 11000, "major_cost": 35000},
        "Patrol": {"interval": 10000, "minor_cost": 18000, "major_cost": 55000},
        "default": {"interval": 15000, "minor_cost": 10000, "major_cost": 32000}
    },
    "default": {"interval": 10000, "minor_cost": 12000, "major_cost": 35000}
}

# ─── MAINTENANCE ENGINE ─────────────────────────────────────────────

class MaintenanceEngine:
    """Professional maintenance cost calculation engine"""
    
    @staticmethod
    def calculate(
        distance_km: float,
        make: str = "",
        model: str = "",
        service_interval: int = 10000,
        annual_km: float = 20000,
        vehicle_age: int = 0,
        include_consumables: bool = True
    ) -> MaintenanceResult:
        """
        Calculate maintenance costs.
        
        Args:
            distance_km: Trip distance
            make: Vehicle make
            model: Vehicle model
            service_interval: Manual override
            annual_km: Annual mileage
            vehicle_age: Age of vehicle
            include_consumables: Include brake pads, filters, etc.
        
        Returns:
            MaintenanceResult with cost breakdown
        """
        # Get service schedule
        make_schedule = SERVICE_SCHEDULES.get(make, SERVICE_SCHEDULES["default"])
        model_schedule = make_schedule.get(model, make_schedule.get("default", SERVICE_SCHEDULES["default"]))
        
        interval = service_interval or model_schedule.get("interval", 10000)
        minor_cost = model_schedule.get("minor_cost", 12000)
        major_cost = model_schedule.get("major_cost", 35000)
        
        # Calculate services per year
        services_per_year = annual_km / interval
        
        # Age factor (older vehicles need more maintenance)
        age_multiplier = 1 + (vehicle_age * 0.05)
        
        # Major service every 3rd service
        major_factor = 0.33  # 1 in 3 services is major
        
        annual_service_cost = (
            minor_cost * (1 - major_factor) +
            major_cost * major_factor
        ) * services_per_year * age_multiplier
        
        # Consumables
        if include_consumables:
            # Brake pads (every 2 years)
            annual_brake_cost = SERVICE_COSTS.get("brake_pads", 8000) * 0.5
            # Filters (every service)
            annual_filter_cost = SERVICE_COSTS.get("filters", 3000) * services_per_year
            # Oil change (every service)
            annual_oil_cost = SERVICE_COSTS.get("oil_change", 5000) * services_per_year
            # Spark plugs (every 3 years)
            annual_spark_cost = SERVICE_COSTS.get("spark_plugs", 6000) * 0.33
            
            annual_service_cost += (
                annual_brake_cost +
                annual_filter_cost +
                annual_oil_cost +
                annual_spark_cost
            )
        
        cost_per_km = annual_service_cost / annual_km if annual_km > 0 else 0
        trip_cost = distance_km * cost_per_km
        
        # Next service calculation
        current_km = 0
        next_service_km = interval - (current_km % interval)
        
        return MaintenanceResult(
            trip_cost=round(trip_cost, 2),
            annual_cost=round(annual_service_cost, 2),
            cost_per_km=round(cost_per_km, 4),
            service_interval=interval,
            next_service_km=round(next_service_km, 2)
        )


def calculate_service_cost(
    distance_km: float,
    service_interval: int = 10000,
    annual_km: float = 20000,
    make: str = "",
    model: str = ""
) -> Dict[str, Any]:
    """Convenience function for service cost calculation"""
    result = MaintenanceEngine.calculate(
        distance_km=distance_km,
        make=make,
        model=model,
        service_interval=service_interval,
        annual_km=annual_km
    )
    
    return {
        "trip_cost": result.trip_cost,
        "annual_cost": result.annual_cost,
        "cost_per_km": result.cost_per_km,
        "service_interval": result.service_interval,
        "next_service_km": result.next_service_km
    }
