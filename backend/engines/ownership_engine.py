"""
Ownership Engine - Auto-D Kenya
Total Cost of Vehicle Ownership over full lifecycle
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .running_cost_engine import RunningCostEngine
from .depreciation_engine import calculate_depreciation
from .finance_engine import calculate_loan_amortization
from .insurance_engine import estimate_insurance


@dataclass
class OwnershipResult:
    """Complete ownership cost result"""
    total_cost: float = 0.0
    annual_cost: float = 0.0
    monthly_cost: float = 0.0
    cost_per_km: float = 0.0
    fixed_costs: Dict[str, float] = field(default_factory=dict)
    variable_costs: Dict[str, float] = field(default_factory=dict)
    yearly_breakdown: List[Dict[str, Any]] = field(default_factory=list)
    comparison: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class OwnershipEngine:
    """
    Professional Ownership Cost Engine.
    Calculates complete cost of vehicle ownership over lifecycle.
    """
    
    def __init__(self):
        self.running_engine = RunningCostEngine()
    
    def calculate_ownership(
        self,
        purchase_price: float,
        years_owned: int,
        annual_mileage: float,
        vehicle_data: Dict[str, Any],
        include_comparison: bool = True
    ) -> OwnershipResult:
        """
        Calculate complete cost of ownership.
        
        Returns:
            OwnershipResult with full lifecycle costs
        """
        make = vehicle_data.get("make", "")
        model = vehicle_data.get("model", "")
        vehicle_type = vehicle_data.get("vehicle_type", "Car")
        condition = vehicle_data.get("condition", "Good")
        fuel_type = vehicle_data.get("fuel_type", "petrol")
        
        # ─── One-time Costs ──────────────────────────────────────
        one_time_costs = {
            "purchase": purchase_price,
            "registration": vehicle_data.get("registration_cost", 5000),
            "inspection": vehicle_data.get("inspection_cost", 2000),
            "delivery": vehicle_data.get("delivery_cost", 0),
            "accessories": vehicle_data.get("accessories_cost", 0)
        }
        one_time_total = sum(one_time_costs.values())
        
        # ─── Running Costs per Year ──────────────────────────────
        yearly_breakdown = []
        total_running_cost = 0
        
        for year in range(1, years_owned + 1):
            # Vehicle data for this year
            year_data = vehicle_data.copy()
            year_data["years_owned"] = year
            year_data["annual_km"] = annual_mileage
            
            # Calculate running cost for this year
            result = self.running_engine.calculate_trip_cost(
                distance_km=annual_mileage,
                vehicle_data=year_data
            )
            
            year_total = result.summary.get("total_cost", 0) / result.summary.get("distance_km", 1) * annual_mileage
            
            yearly_breakdown.append({
                "year": year,
                "total_cost": year_total,
                "depreciation": result.fixed_costs.get("depreciation", 0) / result.summary.get("distance_km", 1) * annual_mileage,
                "fuel": result.operating_costs.get("energy", 0) / result.summary.get("distance_km", 1) * annual_mileage,
                "insurance": result.fixed_costs.get("insurance", 0) / result.summary.get("distance_km", 1) * annual_mileage,
                "maintenance": result.operating_costs.get("maintenance", 0) / result.summary.get("distance_km", 1) * annual_mileage,
                "tyres": result.operating_costs.get("tyres", 0) / result.summary.get("distance_km", 1) * annual_mileage,
                "repairs": result.operating_costs.get("repairs", 0) / result.summary.get("distance_km", 1) * annual_mileage,
                "licensing": result.fixed_costs.get("licensing", 0) / result.summary.get("distance_km", 1) * annual_mileage,
                "interest": result.fixed_costs.get("interest", 0) / result.summary.get("distance_km", 1) * annual_mileage
            })
            
            total_running_cost += year_total
        
        # ─── Resale Value ─────────────────────────────────────────
        dep_result = calculate_depreciation(
            purchase_price=purchase_price,
            age_years=years_owned,
            vehicle_type=vehicle_type,
            condition=condition,
            mileage=annual_mileage * years_owned
        )
        resale_value = dep_result["current_value"]
        
        # ─── Total Ownership Cost ─────────────────────────────────
        total_cost = one_time_total + total_running_cost - resale_value
        annual_cost = total_cost / years_owned if years_owned > 0 else 0
        monthly_cost = annual_cost / 12
        total_km = annual_mileage * years_owned
        cost_per_km = total_cost / total_km if total_km > 0 else 0
        
        # ─── Fixed vs Variable ────────────────────────────────────
        fixed_costs = {
            "depreciation": purchase_price - resale_value,
            "insurance": sum(year["insurance"] for year in yearly_breakdown),
            "licensing": sum(year["licensing"] for year in yearly_breakdown),
            "interest": sum(year["interest"] for year in yearly_breakdown),
            "one_time": one_time_total
        }
        
        variable_costs = {
            "fuel": sum(year["fuel"] for year in yearly_breakdown),
            "maintenance": sum(year["maintenance"] for year in yearly_breakdown),
            "tyres": sum(year["tyres"] for year in yearly_breakdown),
            "repairs": sum(year["repairs"] for year in yearly_breakdown)
        }
        
        # ─── Comparison ───────────────────────────────────────────
        comparison = {}
        if include_comparison:
            comparison = {
                "total_cost": total_cost,
                "cost_per_km": cost_per_km,
                "annual_cost": annual_cost,
                "resale_value": resale_value,
                "value_retained": (resale_value / purchase_price) * 100 if purchase_price > 0 else 0
            }
        
        # ─── Recommendations ──────────────────────────────────────
        recommendations = []
        
        # Fuel cost vs total
        fuel_total = sum(year["fuel"] for year in yearly_breakdown)
        if fuel_total / total_cost > 0.30:
            recommendations.append(
                f"Fuel cost is {fuel_total/total_cost*100:.1f}% of total. Consider a more fuel-efficient vehicle."
            )
        
        # Depreciation
        if purchase_price > 0:
            dep_percent = ((purchase_price - resale_value) / purchase_price) * 100
            if dep_percent > 50:
                recommendations.append(
                    f"Vehicle depreciates {dep_percent:.1f}% over {years_owned} years. Consider selling earlier for better value."
                )
        
        return OwnershipResult(
            total_cost=round(total_cost, 2),
            annual_cost=round(annual_cost, 2),
            monthly_cost=round(monthly_cost, 2),
            cost_per_km=round(cost_per_km, 2),
            fixed_costs={k: round(v, 2) for k, v in fixed_costs.items()},
            variable_costs={k: round(v, 2) for k, v in variable_costs.items()},
            yearly_breakdown=yearly_breakdown,
            comparison=comparison,
            recommendations=recommendations
        )


def calculate_ownership_cost(
    purchase_price: float,
    years_owned: int,
    fuel_cost: float,
    maintenance_cost: float,
    insurance_cost: float,
    taxes: float,
    resale_value: float = 0
) -> Dict[str, Any]:
    """
    Simplified ownership cost calculation (API compatibility).
    Matches Flask backend signature.
    """
    # Convert to vehicle_data format
    vehicle_data = {
        "purchase_price": purchase_price,
        "years_owned": years_owned,
        "annual_km": 20000,
        "fuel_cost_annual": fuel_cost,
        "maintenance_annual": maintenance_cost,
        "insurance_annual": insurance_cost,
        "tax_annual": taxes
    }
    
    engine = OwnershipEngine()
    result = engine.calculate_ownership(
        purchase_price=purchase_price,
        years_owned=years_owned,
        annual_mileage=20000,
        vehicle_data=vehicle_data,
        include_comparison=False
    )
    
    return {
        "total_cost": result.total_cost,
        "annual_cost": result.annual_cost,
        "cost_per_km": result.cost_per_km,
        "fixed_costs": result.fixed_costs,
        "variable_costs": result.variable_costs,
        "yearly_breakdown": result.yearly_breakdown,
        "recommendations": result.recommendations
    }
