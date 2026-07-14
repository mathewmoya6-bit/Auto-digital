"""
Running Cost Engine - Auto-D Kenya
Orchestrates all cost calculations for a trip
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import logging

from .fuel_service import get_fuel_price, calculate_energy_cost
from .depreciation_engine import calculate_depreciation
from .insurance_engine import estimate_insurance
from .tyre_engine import calculate_tyre_cost
from .maintenance_engine import calculate_service_cost
from .finance_engine import calculate_loan_amortization
from .battery_engine import calculate_battery_reserve
from .environmental_engine import calculate_co2_emissions

logger = logging.getLogger(__name__)


@dataclass
class RunningCostResult:
    """Complete running cost result"""
    summary: Dict[str, Any] = field(default_factory=dict)
    fixed_costs: Dict[str, Any] = field(default_factory=dict)
    operating_costs: Dict[str, Any] = field(default_factory=dict)
    energy: Dict[str, Any] = field(default_factory=dict)
    environmental: Dict[str, Any] = field(default_factory=dict)
    projection: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[Dict[str, str]] = field(default_factory=list)
    assumptions: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class RunningCostEngine:
    """
    Professional Running Cost Engine.
    Orchestrates all cost calculations for a trip.
    """
    
    def __init__(self):
        self.fuel_service = None
    
    def calculate_trip_cost(
        self,
        distance_km: float,
        vehicle_data: Dict[str, Any],
        include_fixed_costs: bool = True,
        include_operating_costs: bool = True,
        include_environmental: bool = True,
        include_projection: bool = True,
        include_recommendations: bool = True
    ) -> RunningCostResult:
        """
        Calculate complete trip cost breakdown.
        
        Returns:
            RunningCostResult with all costs
        """
        # ─── Extract Vehicle Data ──────────────────────────────────
        make = vehicle_data.get("make", "")
        model = vehicle_data.get("model", "")
        year = vehicle_data.get("year", 2020)
        fuel_type = vehicle_data.get("fuel_type", "petrol")
        fuel_consumption = vehicle_data.get("fuel_consumption", 8.0)
        purchase_price = vehicle_data.get("purchase_price", 0)
        current_value = vehicle_data.get("current_value", 0)
        vehicle_type = vehicle_data.get("vehicle_type", "Car")
        condition = vehicle_data.get("condition", "Good")
        mileage = vehicle_data.get("mileage", 0)
        annual_km = vehicle_data.get("annual_km", 20000)
        years_owned = vehicle_data.get("years_owned", 5)
        tyre_size = vehicle_data.get("tyre_size", "")
        tyre_count = vehicle_data.get("tyre_count", 4)
        service_interval = vehicle_data.get("service_interval", 10000)
        battery_capacity = vehicle_data.get("battery_capacity", 0)
        financed = vehicle_data.get("financed", False)
        deposit = vehicle_data.get("deposit", 0)
        loan_amount = vehicle_data.get("loan_amount", 0)
        interest_rate = vehicle_data.get("interest_rate", 16.0)
        loan_term = vehicle_data.get("loan_term", 4)
        coverage_type = vehicle_data.get("coverage_type", "comprehensive")
        usage_type = vehicle_data.get("usage_type", "Personal")
        
        # ─── Energy Cost ──────────────────────────────────────────
        energy_result = calculate_energy_cost(
            fuel_type=fuel_type,
            distance_km=distance_km,
            consumption=fuel_consumption
        )
        
        if not energy_result:
            return RunningCostResult(
                warnings=[f"Energy type not available: {fuel_type}"]
            )
        
        # ─── Fixed Costs ──────────────────────────────────────────
        fixed_costs = {}
        
        if include_fixed_costs:
            # Insurance
            if current_value > 0:
                insurance_result = estimate_insurance(
                    vehicle_value=current_value,
                    vehicle_type=vehicle_type,
                    coverage_type=coverage_type,
                    usage=usage_type
                )
                fixed_costs["insurance"] = (
                    insurance_result["annual_premium"] / annual_km
                ) * distance_km
            
            # Depreciation
            dep_result = calculate_depreciation(
                purchase_price=purchase_price,
                age_years=min(years_owned, 8),
                vehicle_type=vehicle_type,
                condition=condition,
                mileage=mileage
            )
            
            dep_per_km = dep_result["total_depreciation"] / (
                annual_km * years_owned
            ) if annual_km > 0 else 0
            fixed_costs["depreciation"] = dep_per_km * distance_km
            
            # Licensing
            licensing_annual = vehicle_data.get("licensing_annual", 5000)
            fixed_costs["licensing"] = (licensing_annual / annual_km) * distance_km
            
            # Interest on capital
            if financed and loan_amount > 0:
                loan_result = calculate_loan_amortization(
                    principal=loan_amount,
                    annual_rate=interest_rate,
                    years=loan_term
                )
                annual_interest = loan_result.get("total_interest", 0) / loan_term
                fixed_costs["interest"] = (annual_interest / annual_km) * distance_km
            
            # Tracking (if applicable)
            if vehicle_data.get("has_tracking", False):
                tracking_annual = vehicle_data.get("tracking_annual", 12000)
                fixed_costs["tracking"] = (tracking_annual / annual_km) * distance_km
        
        fixed_total = sum(fixed_costs.values())
        
        # ─── Operating Costs ──────────────────────────────────────
        operating_costs = {}
        
        if include_operating_costs:
            # Energy
            operating_costs["energy"] = energy_result.get("energy_cost", 0)
            
            # Maintenance
            service_result = calculate_service_cost(
                distance_km=distance_km,
                make=make,
                model=model,
                service_interval=service_interval,
                annual_km=annual_km
            )
            operating_costs["maintenance"] = service_result.get("trip_cost", 0)
            
            # Tyres
            if tyre_size:
                tyre_result = calculate_tyre_cost(
                    tyre_size=tyre_size,
                    distance_km=distance_km,
                    tyre_count=tyre_count,
                    annual_km=annual_km
                )
                operating_costs["tyres"] = tyre_result.get("trip_cost", 0)
            
            # Battery reserve (EV)
            if battery_capacity > 0:
                battery_cost = vehicle_data.get("battery_replacement_cost", battery_capacity * 15000)
                battery_result = calculate_battery_reserve(
                    battery_capacity=battery_capacity,
                    distance_km=distance_km,
                    battery_life_km=vehicle_data.get("battery_life", 250000),
                    replacement_cost=battery_cost,
                    annual_km=annual_km
                )
                operating_costs["battery_reserve"] = battery_result.get("trip_reserve", 0)
            
            # Repairs (estimated)
            repair_per_km = vehicle_data.get("repair_per_km", 1.0)
            operating_costs["repairs"] = repair_per_km * distance_km
            
            # Brake wear
            brake_per_km = vehicle_data.get("brake_per_km", 0.50)
            operating_costs["brake_wear"] = brake_per_km * distance_km
            
            # Other costs
            other_per_km = vehicle_data.get("other_operating_per_km", 0)
            operating_costs["other"] = other_per_km * distance_km
        
        operating_total = sum(operating_costs.values())
        
        # ─── Summary ──────────────────────────────────────────────
        total_cost = operating_total + fixed_total
        total_per_km = total_cost / distance_km if distance_km > 0 else 0
        
        summary = {
            "total_cost": round(total_cost, 2),
            "total_per_km": round(total_per_km, 2),
            "distance_km": distance_km,
            "energy_cost": round(operating_costs.get("energy", 0), 2),
            "energy_per_km": round(operating_costs.get("energy", 0) / distance_km if distance_km > 0 else 0, 2),
            "operating_cost_total": round(operating_total, 2),
            "fixed_cost_total": round(fixed_total, 2),
            "breakdown": {
                "fixed_per_km": round(fixed_total / distance_km if distance_km > 0 else 0, 2),
                "operating_per_km": round(operating_total / distance_km if distance_km > 0 else 0, 2)
            }
        }
        
        # ─── Environmental ────────────────────────────────────────
        environmental = {}
        if include_environmental:
            co2 = calculate_co2_emissions(
                fuel_type=fuel_type,
                fuel_consumption=fuel_consumption,
                distance_km=distance_km
            )
            environmental = {
                "co2_emissions_kg": co2.get("co2_kg", 0),
                "co2_per_km": co2.get("co2_per_km", 0),
                "fuel_type": fuel_type
            }
        
        # ─── 5-Year Projection ────────────────────────────────────
        projection = []
        if include_projection:
            for year in range(1, 6):
                age_factor = 1 + (year - 1) * 0.05
                dep_yearly = calculate_depreciation(
                    purchase_price=purchase_price,
                    age_years=year,
                    vehicle_type=vehicle_type,
                    condition=condition,
                    mileage=mileage + (year * annual_km)
                )
                projection.append({
                    "year": year,
                    "total_cost": round((total_cost / distance_km) * annual_km * age_factor, 2),
                    "cost_per_km": round((total_cost / distance_km) * age_factor, 2),
                    "vehicle_value": dep_yearly["current_value"],
                    "depreciation": dep_yearly["total_depreciation"]
                })
        
        # ─── Recommendations ──────────────────────────────────────
        recommendations = []
        if include_recommendations:
            if fuel_type in ["petrol", "diesel"]:
                recommendations.append({
                    "type": "fuel",
                    "message": "Consider hybrid or electric vehicle for lower running costs.",
                    "suggestion": "Switch to electric could save up to 60% on energy costs."
                })
            if tyre_size and operating_costs.get("tyres", 0) > 50:
                recommendations.append({
                    "type": "tyres",
                    "message": "Check tyre pressure regularly to extend tyre life.",
                    "suggestion": "Proper inflation can improve fuel efficiency by 3%."
                })
            if current_value > 0 and purchase_price > 0:
                value_retained = (current_value / purchase_price) * 100
                if value_retained < 40:
                    recommendations.append({
                        "type": "depreciation",
                        "message": f"Vehicle has retained only {value_retained:.1f}% of original value.",
                        "suggestion": "Consider selling before year 5 for better resale value."
                    })
        
        # ─── Assumptions ──────────────────────────────────────────
        assumptions = {
            "fuel_price": energy_result.get("fuel_price", 0),
            "fuel_price_source": energy_result.get("source", ""),
            "annual_mileage": annual_km,
            "depreciation_method": "Declining Balance",
            "interest_rate": interest_rate if financed else 0,
            "insurance_coverage": coverage_type,
            "vehicle_condition": condition
        }
        
        # ─── Warnings ─────────────────────────────────────────────
        warnings = []
        if purchase_price <= 0:
            warnings.append("Purchase price not provided. Using estimates.")
        if fuel_consumption <= 0:
            warnings.append("Fuel consumption not provided. Using default values.")
        if annual_km <= 0:
            warnings.append("Annual mileage not provided. Using default 20,000 km.")
        
        return RunningCostResult(
            summary=summary,
            fixed_costs={k: round(v, 2) for k, v in fixed_costs.items()},
            operating_costs={k: round(v, 2) for k, v in operating_costs.items()},
            energy=energy_result,
            environmental=environmental,
            projection=projection,
            recommendations=recommendations,
            assumptions=assumptions,
            warnings=warnings
        )
