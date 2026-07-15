"""
Ownership Engine - Auto-D Kenya
Total Cost of Vehicle Ownership over full lifecycle
Professional engine matching frontend requirements
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class OwnershipResult:
    """Complete ownership cost result - matches frontend format"""
    total_cost: float = 0.0
    annual_cost: float = 0.0
    monthly_cost: float = 0.0
    cost_per_km: float = 0.0
    resale_value: float = 0.0
    total_depreciation: float = 0.0
    value_retained: float = 0.0
    fixed_costs: Dict[str, float] = field(default_factory=dict)
    variable_costs: Dict[str, float] = field(default_factory=dict)
    yearly_breakdown: List[Dict[str, Any]] = field(default_factory=list)
    rci: float = 0.0
    rci_label: str = "Good"
    rci_stars: str = "★★★★"
    rci_class: str = "good"
    health_score: float = 75.0
    health_label: str = "★★★★ Good"
    co2_per_km: float = 0.0
    co2_annual: float = 0.0
    trees_to_offset: float = 0.0
    recommendations: List[Dict[str, str]] = field(default_factory=list)
    
    def to_frontend_format(self) -> Dict[str, Any]:
        """Convert to frontend format for ownership-cost.html"""
        return {
            "totalCost": self.total_cost,
            "costPerMonth": self.monthly_cost,
            "costPerKm": self.cost_per_km,
            "resaleValue": self.resale_value,
            "totalDepreciation": self.total_depreciation,
            "valueRetained": self.value_retained,
            "yearlyBreakdown": self.yearly_breakdown,
            "costComponents": {
                "depreciation": self.fixed_costs.get("depreciation", 0),
                "financing": self.fixed_costs.get("interest", 0),
                "insurance": self.fixed_costs.get("insurance", 0),
                "fuel": self.variable_costs.get("fuel", 0),
                "maintenance": self.variable_costs.get("maintenance", 0),
                "tyres": self.variable_costs.get("tyres", 0),
                "licensing": self.fixed_costs.get("licensing", 0),
                "purchase": self.fixed_costs.get("purchase", 0)
            },
            "rci": self.rci,
            "rciLabel": self.rci_label,
            "rciStars": self.rci_stars,
            "rciClass": self.rci_class,
            "healthScore": self.health_score,
            "healthLabel": self.health_label,
            "co2PerKm": self.co2_per_km,
            "co2Annual": self.co2_annual,
            "treesToOffset": self.trees_to_offset,
            "recommendations": self.recommendations
        }


class OwnershipEngine:
    """
    Professional Ownership Cost Engine.
    Calculates complete cost of vehicle ownership over lifecycle.
    Aligned with Mileage & Running Cost engine.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Import running engine lazily to avoid circular imports
        self._running_engine = None
    
    @property
    def running_engine(self):
        if self._running_engine is None:
            try:
                from .running_cost_engine import RunningCostEngine
                self._running_engine = RunningCostEngine()
            except ImportError:
                self.logger.warning("⚠️ RunningCostEngine not available")
        return self._running_engine
    
    def calculate_ownership(
        self,
        purchase_price: float,
        years_owned: int,
        annual_mileage: float,
        vehicle_data: Dict[str, Any],
        include_comparison: bool = True
    ) -> OwnershipResult:
        """
        Calculate complete cost of ownership with full breakdown.
        
        Args:
            purchase_price: Initial purchase price
            years_owned: Number of years of ownership
            annual_mileage: Average annual mileage
            vehicle_data: Vehicle specifications (make, model, fuel_type, etc.)
            include_comparison: Whether to include comparison data
            
        Returns:
            OwnershipResult with full lifecycle costs
        """
        # ─── Extract vehicle data ──────────────────────────────────
        make = vehicle_data.get("make", "")
        model = vehicle_data.get("model", "")
        vehicle_type = vehicle_data.get("vehicle_type", "Car")
        condition = vehicle_data.get("condition", "Good")
        fuel_type = vehicle_data.get("fuel_type", "petrol")
        fuel_efficiency = vehicle_data.get("fuel_efficiency", vehicle_data.get("fuel", 12))
        maintenance_per_km = vehicle_data.get("maintenance_per_km", vehicle_data.get("maintenancePerKm", 5))
        service_interval = vehicle_data.get("service_interval", vehicle_data.get("serviceInterval", 10000))
        minor_cost = vehicle_data.get("minor_service_cost", vehicle_data.get("minor", 15000))
        major_cost = vehicle_data.get("major_service_cost", vehicle_data.get("major", 45000))
        tyre_cost = vehicle_data.get("tyre_cost", 20000)
        tyre_life = vehicle_data.get("tyre_life", 45000)
        insurance_rate = vehicle_data.get("insurance_rate", 0.045)
        
        # ─── Fuel prices ──────────────────────────────────────────
        fuel_prices = {
            "petrol": 214.03,
            "diesel": 222.86,
            "electric": 30.00,
            "hybrid": 150.00,
            "lpg": 120.00
        }
        fuel_price = fuel_prices.get(fuel_type, 214.03)
        
        # ─── Location multipliers ─────────────────────────────────
        locations = vehicle_data.get("driving_locations", [])
        fuel_mult, maint_mult, tyre_mult, ins_mult = self._get_location_multipliers(locations)
        
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
        
        # Depreciation calculation
        dep_result = self._calculate_depreciation(
            purchase_price=purchase_price,
            years_owned=years_owned,
            condition=condition,
            mileage=annual_mileage * years_owned
        )
        
        vehicle_value = purchase_price
        
        for year in range(1, years_owned + 1):
            # ─── Depreciation ──────────────────────────────────────
            dep_rate = 0.12 * (1 + (year - 1) * 0.08)
            depreciation = vehicle_value * min(dep_rate, 0.40)
            vehicle_value -= depreciation
            
            # ─── Financing (if applicable) ──────────────────────────
            financed = vehicle_data.get("financed", False)
            financing = 0
            if financed:
                loan_term = vehicle_data.get("loan_term", 4)
                if year <= loan_term:
                    financing = self._calculate_financing_cost(
                        purchase_price=purchase_price,
                        down_pct=vehicle_data.get("down_pct", 30),
                        interest_rate=vehicle_data.get("interest_rate", 16),
                        loan_term=loan_term
                    ) / loan_term
            
            # ─── Insurance ──────────────────────────────────────────
            insurance = max(vehicle_value, purchase_price * 0.15) * insurance_rate * ins_mult
            
            # ─── Fuel ──────────────────────────────────────────────
            litres = annual_mileage / max(fuel_efficiency, 0.1)
            fuel = litres * fuel_price * fuel_mult
            
            # ─── Maintenance ────────────────────────────────────────
            age_multiplier = 1 + (year - 1) * 0.08
            maintenance = annual_mileage * maintenance_per_km * maint_mult * age_multiplier
            
            # ─── Tyres ──────────────────────────────────────────────
            tyres = (annual_mileage / tyre_life) * tyre_cost * tyre_mult
            
            # ─── Licensing ──────────────────────────────────────────
            licensing = 5000 + (year > 1 and year * 1000 or 0)
            
            # ─── Year Total ────────────────────────────────────────
            year_total = depreciation + financing + insurance + fuel + maintenance + tyres + licensing
            total_running_cost += year_total
            
            yearly_breakdown.append({
                "year": year,
                "depreciation": round(depreciation, 2),
                "financing": round(financing, 2),
                "insurance": round(insurance, 2),
                "fuel": round(fuel, 2),
                "maintenance": round(maintenance, 2),
                "tyres": round(tyres, 2),
                "licensing": round(licensing, 2),
                "total": round(year_total, 2),
                "vehicleValue": round(max(vehicle_value, purchase_price * 0.05), 2)
            })
        
        # ─── Resale Value ─────────────────────────────────────────
        resale_value = max(vehicle_value, purchase_price * 0.05)
        total_depreciation = purchase_price - resale_value
        value_retained = (resale_value / purchase_price) * 100 if purchase_price > 0 else 0
        
        # ─── Total Ownership Cost ─────────────────────────────────
        total_cost = one_time_total + total_running_cost - resale_value
        annual_cost = total_cost / years_owned if years_owned > 0 else 0
        monthly_cost = annual_cost / 12
        total_km = annual_mileage * years_owned
        cost_per_km = total_cost / total_km if total_km > 0 else 0
        
        # ─── Fixed vs Variable ────────────────────────────────────
        fixed_costs = {
            "depreciation": total_depreciation,
            "insurance": sum(year["insurance"] for year in yearly_breakdown),
            "licensing": sum(year["licensing"] for year in yearly_breakdown),
            "interest": sum(year["financing"] for year in yearly_breakdown),
            "purchase": one_time_total
        }
        
        variable_costs = {
            "fuel": sum(year["fuel"] for year in yearly_breakdown),
            "maintenance": sum(year["maintenance"] for year in yearly_breakdown),
            "tyres": sum(year["tyres"] for year in yearly_breakdown)
        }
        
        # ─── RCI ──────────────────────────────────────────────────
        rci = cost_per_km
        rci_label, rci_stars, rci_class = self._get_rci_rating(rci)
        
        # ─── Health Score ─────────────────────────────────────────
        age = vehicle_data.get("age", years_owned)
        health_score = self._calculate_health_score(
            age=age,
            fuel_efficiency=fuel_efficiency,
            fuel_type=fuel_type,
            maintenance_per_km=maintenance_per_km
        )
        health_label = self._get_health_label(health_score)
        
        # ─── Environmental ────────────────────────────────────────
        co2_factor = self._get_co2_factor(fuel_type)
        co2_per_km = co2_factor / max(fuel_efficiency, 0.1)
        co2_annual = co2_per_km * annual_mileage
        trees_to_offset = co2_annual / 20
        
        # ─── Recommendations ──────────────────────────────────────
        recommendations = self._generate_recommendations(
            cost_per_km=cost_per_km,
            rci=rci,
            health_score=health_score,
            age=age,
            fuel_type=fuel_type,
            financed=financed if 'financed' in locals() else False,
            total_cost=total_cost,
            value_retained=value_retained,
            total_depreciation=total_depreciation,
            purchase_price=purchase_price
        )
        
        return OwnershipResult(
            total_cost=round(total_cost, 2),
            annual_cost=round(annual_cost, 2),
            monthly_cost=round(monthly_cost, 2),
            cost_per_km=round(cost_per_km, 2),
            resale_value=round(resale_value, 2),
            total_depreciation=round(total_depreciation, 2),
            value_retained=round(value_retained, 2),
            fixed_costs={k: round(v, 2) for k, v in fixed_costs.items()},
            variable_costs={k: round(v, 2) for k, v in variable_costs.items()},
            yearly_breakdown=yearly_breakdown,
            rci=round(rci, 2),
            rci_label=rci_label,
            rci_stars=rci_stars,
            rci_class=rci_class,
            health_score=round(health_score, 2),
            health_label=health_label,
            co2_per_km=round(co2_per_km, 2),
            co2_annual=round(co2_annual, 2),
            trees_to_offset=round(trees_to_offset, 2),
            recommendations=recommendations
        )
    
    def _get_location_multipliers(self, locations: List[str]) -> tuple:
        """Get location multipliers for fuel, maintenance, tyres, insurance"""
        multipliers = {
            "nairobi": {"fuel": 0.9, "maintenance": 1.1, "tyres": 1.0, "insurance": 1.0},
            "mombasa": {"fuel": 1.1, "maintenance": 1.1, "tyres": 1.1, "insurance": 1.05},
            "rural": {"fuel": 1.15, "maintenance": 1.3, "tyres": 1.3, "insurance": 1.1},
            "highway": {"fuel": 0.95, "maintenance": 1.0, "tyres": 1.0, "insurance": 0.95}
        }
        
        fuel_mult = 1.0
        maint_mult = 1.0
        tyre_mult = 1.0
        ins_mult = 1.0
        
        for loc in locations:
            if loc in multipliers:
                m = multipliers[loc]
                fuel_mult *= m.get("fuel", 1.0)
                maint_mult *= m.get("maintenance", 1.0)
                tyre_mult *= m.get("tyres", 1.0)
                ins_mult *= m.get("insurance", 1.0)
        
        return fuel_mult, maint_mult, tyre_mult, ins_mult
    
    def _calculate_depreciation(self, purchase_price: float, years_owned: int, condition: str, mileage: float) -> Dict[str, Any]:
        """Calculate depreciation over ownership period"""
        base_rates = {
            'Excellent': 0.08,
            'Good': 0.12,
            'Fair': 0.18,
            'Poor': 0.25
        }
        rate = base_rates.get(condition, 0.12)
        if mileage > 100000:
            rate += 0.05
        elif mileage > 60000:
            rate += 0.03
        elif mileage > 30000:
            rate += 0.015
        
        current_value = purchase_price
        yearly_depreciation = []
        
        for year in range(1, years_owned + 1):
            year_rate = rate * (1 + (year - 1) * 0.08)
            dep_amount = current_value * min(year_rate, 0.40)
            current_value -= dep_amount
            yearly_depreciation.append({
                "year": year,
                "value": max(current_value, purchase_price * 0.05),
                "depreciation": dep_amount,
                "rate": year_rate
            })
        
        return {
            "current_value": max(current_value, purchase_price * 0.05),
            "total_depreciation": purchase_price - max(current_value, purchase_price * 0.05),
            "value_retained": (max(current_value, purchase_price * 0.05) / purchase_price) * 100 if purchase_price > 0 else 0,
            "yearly_breakdown": yearly_depreciation
        }
    
    def _calculate_financing_cost(self, purchase_price: float, down_pct: float, interest_rate: float, loan_term: int) -> float:
        """Calculate total financing cost"""
        down_pct = float(down_pct) / 100
        interest_rate = float(interest_rate) / 100
        loan_term = int(loan_term)
        loan_balance = purchase_price * (1 - down_pct)
        
        if loan_term <= 0 or interest_rate <= 0:
            return 0
        
        monthly_rate = interest_rate / 12
        num_payments = loan_term * 12
        monthly_payment = loan_balance * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
        total_payment = monthly_payment * num_payments
        
        return total_payment - loan_balance  # Interest only
    
    def _get_rci_rating(self, rci: float) -> tuple:
        """Get RCI rating labels - matches Mileage & Running Cost"""
        if rci <= 20:
            return "Excellent", "★★★★★", "excellent"
        elif rci <= 35:
            return "Good", "★★★★", "good"
        elif rci <= 50:
            return "Average", "★★★", "average"
        elif rci <= 70:
            return "Expensive", "★★", "expensive"
        else:
            return "Very Expensive", "★", "very-expensive"
    
    def _calculate_health_score(self, age: int, fuel_efficiency: float, fuel_type: str, maintenance_per_km: float) -> float:
        """Calculate vehicle health score (0-100) - matches Mileage & Running Cost"""
        score = 100
        score -= age * 3
        ideal = 20 if fuel_type == "electric" else (6 if fuel_type == "diesel" else 8)
        if fuel_efficiency < ideal * 0.7:
            score += 5
        elif fuel_efficiency > ideal * 1.3:
            score -= 5
        if maintenance_per_km > 4:
            score -= 8
        elif maintenance_per_km > 3:
            score -= 3
        if fuel_type == "electric":
            score += 5
        return max(0, min(100, score))
    
    def _get_health_label(self, score: float) -> str:
        """Get health label based on score - matches Mileage & Running Cost"""
        if score >= 80:
            return "★★★★★ Excellent"
        elif score >= 60:
            return "★★★★ Good"
        elif score >= 40:
            return "★★★ Average"
        elif score >= 20:
            return "★★ Needs Attention"
        else:
            return "★ Critical"
    
    def _get_co2_factor(self, fuel_type: str) -> float:
        """Get CO2 emission factor by fuel type"""
        factors = {
            "petrol": 2.31,
            "diesel": 2.68,
            "hybrid": 1.80,
            "electric": 0.20,
            "lpg": 1.50
        }
        return factors.get(fuel_type, 2.31)
    
    def _generate_recommendations(self, **kwargs) -> List[Dict[str, str]]:
        """Generate AI-style recommendations - matches Mileage & Running Cost"""
        recommendations = []
        cost_per_km = kwargs.get("cost_per_km", 0)
        rci = kwargs.get("rci", 0)
        health_score = kwargs.get("health_score", 0)
        age = kwargs.get("age", 0)
        fuel_type = kwargs.get("fuel_type", "petrol")
        financed = kwargs.get("financed", False)
        total_cost = kwargs.get("total_cost", 0)
        value_retained = kwargs.get("value_retained", 0)
        total_depreciation = kwargs.get("total_depreciation", 0)
        purchase_price = kwargs.get("purchase_price", 0)
        
        if cost_per_km > 30:
            recommendations.append({
                "icon": "💰",
                "text": f"Cost per km ({cost_per_km:.2f} KES/km) is high. Consider a more fuel-efficient vehicle.",
                "type": "warning",
                "tag": "Cost"
            })
        
        if rci > 50:
            recommendations.append({
                "icon": "📊",
                "text": f"RCI ({rci:.2f}) is in the 'Expensive' range. Review your vehicle choice.",
                "type": "warning",
                "tag": "RCI"
            })
        
        if health_score < 50:
            recommendations.append({
                "icon": "🏥",
                "text": f"Vehicle health score ({health_score:.0f}/100) is low. Consider a newer or better-maintained vehicle.",
                "type": "warning",
                "tag": "Health"
            })
        
        if age > 10:
            recommendations.append({
                "icon": "📅",
                "text": f"Vehicle is {age} years old. Maintenance costs will increase significantly.",
                "type": "warning",
                "tag": "Age"
            })
        
        if value_retained < 40:
            recommendations.append({
                "icon": "📉",
                "text": f"Vehicle retains only {value_retained:.1f}% of value after {age} years. Consider a model with better resale.",
                "type": "warning",
                "tag": "Depreciation"
            })
        
        if total_depreciation > 0 and purchase_price > 0 and (total_depreciation / purchase_price) > 0.5:
            recommendations.append({
                "icon": "📉",
                "text": f"High depreciation ({((total_depreciation / purchase_price) * 100):.0f}% loss). Consider selling before year 5 for better value.",
                "type": "warning",
                "tag": "Depreciation"
            })
        
        if fuel_type == "electric":
            recommendations.append({
                "icon": "🌱",
                "text": "Great EV choice! Zero tailpipe emissions and lower running costs.",
                "type": "success",
                "tag": "Green"
            })
        elif fuel_type in ["petrol", "diesel"] and cost_per_km > 15:
            recommendations.append({
                "icon": "⚡",
                "text": "Consider switching to electric. You could save up to 60% on fuel costs.",
                "type": "info",
                "tag": "EV"
            })
        
        if financed:
            # Calculate financing percentage of total cost if possible
            financing_total = kwargs.get("financing_total", 0)
            if financing_total > 0 and total_cost > 0:
                fin_pct = (financing_total / total_cost) * 100
                if fin_pct > 15:
                    recommendations.append({
                        "icon": "🏦",
                        "text": f"Financing represents {fin_pct:.0f}% of total cost. Consider a larger down payment.",
                        "type": "info",
                        "tag": "Financing"
                    })
        
        if not recommendations:
            recommendations.append({
                "icon": "✅",
                "text": "Vehicle performing well across all metrics. Good ownership value.",
                "type": "success",
                "tag": "All Good"
            })
        
        return recommendations


# ─── API COMPATIBILITY FUNCTIONS ──────────────────────────────────

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
    try:
        purchase_price = float(purchase_price)
        years_owned = float(years_owned)
        fuel_cost = float(fuel_cost)
        maintenance_cost = float(maintenance_cost)
        insurance_cost = float(insurance_cost)
        taxes = float(taxes)
        resale_value = float(resale_value)
    except (ValueError, TypeError):
        return {"error": "Invalid input values"}
    
    if purchase_price < 0 or years_owned < 0:
        return {"error": "Invalid input values"}
    
    total_operating_cost = fuel_cost + maintenance_cost + insurance_cost + taxes
    total_cost = purchase_price + total_operating_cost - resale_value
    annual_cost = total_cost / years_owned if years_owned > 0 else 0
    
    # Calculate RCI
    total_km = 20000 * years_owned
    cost_per_km = total_cost / total_km if total_km > 0 else 0
    
    # Get RCI rating
    engine = OwnershipEngine()
    rci_label, rci_stars, rci_class = engine._get_rci_rating(cost_per_km)
    
    return {
        "purchase_price": round(purchase_price, 2),
        "years_owned": years_owned,
        "fuel_cost": round(fuel_cost, 2),
        "maintenance_cost": round(maintenance_cost, 2),
        "insurance_cost": round(insurance_cost, 2),
        "taxes": round(taxes, 2),
        "resale_value": round(resale_value, 2),
        "total_operating_cost": round(total_operating_cost, 2),
        "total_cost": round(total_cost, 2),
        "annual_cost": round(annual_cost, 2),
        "cost_per_km": round(cost_per_km, 2),
        "cost_per_month": round(annual_cost / 12, 2) if years_owned > 0 else 0,
        "rci": round(cost_per_km, 2),
        "rci_label": rci_label,
        "rci_stars": rci_stars,
        "rci_class": rci_class
    }


def calculate_ownership_from_vehicle(
    make: str,
    model: str,
    years_owned: int,
    annual_mileage: int,
    financed: bool = False,
    down_pct: float = 30,
    interest_rate: float = 16,
    loan_term: int = 4,
    driving_locations: List[str] = None,
    fuel_type: str = "petrol",
    insurance_rate: float = 4.5,
    year: int = 2020
) -> Dict[str, Any]:
    """
    Calculate ownership cost using vehicle database.
    """
    # Try to get vehicle data
    try:
        from vehicle_data import get_vehicle_data
        vehicle = get_vehicle_data(make, model)
    except ImportError:
        # Fallback vehicle data
        fallback = {
            "toyota": {"prado": {"price": 5200000, "fuel": 11, "serviceInterval": 10000, "minor": 18000, "major": 65000, "maintenancePerKm": 14}},
            "nissan": {"xtrail": {"price": 3200000, "fuel": 12, "serviceInterval": 15000, "minor": 12000, "major": 42000, "maintenancePerKm": 8}}
        }
        vehicle = fallback.get(make, {}).get(model)
    
    if not vehicle:
        return {"error": f"Vehicle '{make} {model}' not found"}
    
    # Build vehicle data
    vehicle_data = {
        "make": make,
        "model": model,
        "fuel_type": fuel_type,
        "fuel_efficiency": vehicle.get("fuel", 12),
        "maintenance_per_km": vehicle.get("maintenancePerKm", 5),
        "service_interval": vehicle.get("serviceInterval", 10000),
        "minor_service_cost": vehicle.get("minor", 15000),
        "major_service_cost": vehicle.get("major", 45000),
        "tyre_cost": 20000,
        "tyre_life": 45000,
        "insurance_rate": insurance_rate / 100,
        "driving_locations": driving_locations or [],
        "financed": financed,
        "down_pct": down_pct,
        "interest_rate": interest_rate,
        "loan_term": loan_term,
        "age": datetime.utcnow().year - year,
        "condition": "Good"
    }
    
    # Calculate using engine
    engine = OwnershipEngine()
    result = engine.calculate_ownership(
        purchase_price=vehicle.get("price", 0),
        years_owned=years_owned,
        annual_mileage=annual_mileage,
        vehicle_data=vehicle_data
    )
    
    return result.to_frontend_format()


# ─── STANDALONE TEST ─────────────────────────────────────────────

if __name__ == "__main__":
    engine = OwnershipEngine()
    
    print("=" * 60)
    print("🚗 Auto-D Kenya - Ownership Engine")
    print("=" * 60)
    
    # Test vehicle data
    test_vehicle = {
        "make": "toyota",
        "model": "prado",
        "fuel_type": "diesel",
        "fuel_efficiency": 11,
        "maintenance_per_km": 14,
        "service_interval": 10000,
        "minor_service_cost": 18000,
        "major_service_cost": 65000,
        "insurance_rate": 0.045,
        "driving_locations": ["nairobi", "highway"],
        "financed": True,
        "down_pct": 30,
        "interest_rate": 16,
        "loan_term": 4,
        "age": 3,
        "condition": "Good"
    }
    
    result = engine.calculate_ownership(
        purchase_price=5200000,
        years_owned=5,
        annual_mileage=20000,
        vehicle_data=test_vehicle
    )
    
    print("\n📊 Ownership Result:")
    print(f"Total Cost: KES {result.total_cost:,.2f}")
    print(f"Cost Per Month: KES {result.monthly_cost:,.2f}")
    print(f"Cost Per Km: KES {result.cost_per_km:,.2f}")
    print(f"Resale Value: KES {result.resale_value:,.2f}")
    print(f"Value Retained: {result.value_retained:.1f}%")
    print(f"RCI: {result.rci:.2f} ({result.rci_label})")
    print(f"Health Score: {result.health_score:.0f}/100")
    print(f"CO₂ per km: {result.co2_per_km:.2f} g/km")
    
    print("\n📅 Yearly Breakdown:")
    for year in result.yearly_breakdown:
        print(f"  Year {year['year']}: KES {year['total']:,.2f}")
    
    print("\n💡 Recommendations:")
    for rec in result.recommendations:
        print(f"  {rec['icon']} {rec['text']} ({rec['tag']})")
    
    print("\n" + "=" * 60)
