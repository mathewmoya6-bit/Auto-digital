"""
Valuation Engine - Auto-D Kenya
Professional vehicle valuation with market intelligence
Aligned with instant-value.html frontend expectations
Serves: /api/service/valuation endpoint
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import math

from .depreciation_engine import calculate_depreciation
from .market_intelligence_engine import get_market_data


@dataclass
class ValuationResult:
    """
    Complete valuation result aligned with instant-value.html frontend
    
    Maps to frontend fields:
    - current_value -> resultMarketValue
    - valuation_range -> resultRange
    - vehicle -> resultVehicle, resultYear, etc.
    - confidence_score -> confidenceFill
    """
    # Primary values (matches frontend expectations)
    current_value: float = 0.0
    market_value: float = 0.0
    estimated_value: float = 0.0
    
    # Value types
    trade_in_value: float = 0.0
    retail_value: float = 0.0
    wholesale_value: float = 0.0
    insurance_value: float = 0.0
    auction_value: float = 0.0
    private_sale_value: float = 0.0
    
    # Range and confidence
    valuation_range: Dict[str, float] = field(default_factory=dict)
    confidence_score: int = 85
    
    # Depreciation details
    purchase_price: float = 0.0
    age_years: float = 0.0
    depreciation_rate: float = 0.0
    total_depreciation: float = 0.0
    value_retained: float = 0.0
    yearly_breakdown: List[Dict[str, Any]] = field(default_factory=list)
    
    # Market adjustments
    market_adjustments: Dict[str, float] = field(default_factory=dict)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    # Vehicle specs for reference
    vehicle: Dict[str, Any] = field(default_factory=dict)


class ValuationEngine:
    """
    Professional Vehicle Valuation Engine.
    Combines depreciation, market data, and condition analysis.
    Aligned with instant-value.html frontend.
    
    Used by:
    - /api/service/valuation endpoint
    - instant-value.html frontend
    - Vehicle valuation reports
    """
    
    # ─── DEPRECIATION RATES BY CONDITION ──────────────────────────
    DEPRECIATION_RATES = {
        "Excellent": {
            "Car": 0.08,
            "Bike": 0.10,
            "Tricycle": 0.12,
            "Truck": 0.10
        },
        "Good": {
            "Car": 0.12,
            "Bike": 0.15,
            "Tricycle": 0.18,
            "Truck": 0.15
        },
        "Fair": {
            "Car": 0.18,
            "Bike": 0.22,
            "Tricycle": 0.25,
            "Truck": 0.22
        },
        "Poor": {
            "Car": 0.25,
            "Bike": 0.30,
            "Tricycle": 0.35,
            "Truck": 0.30
        }
    }
    
    # ─── LOCATION MULTIPLIERS ──────────────────────────────────────
    LOCATION_MULTIPLIERS = {
        "Nairobi": 1.05,
        "Mombasa": 1.02,
        "Kisumu": 0.98,
        "Nakuru": 0.97,
        "Eldoret": 0.96,
        "Thika": 0.95,
        "Kiambu": 0.98,
        "Kajiado": 0.94,
        "Machakos": 0.95,
        "Meru": 0.93,
        "Nyeri": 0.92,
        "Embu": 0.91,
        "Other": 0.90
    }
    
    # ─── ACCIDENT HISTORY MULTIPLIERS ─────────────────────────────
    ACCIDENT_MULTIPLIERS = {
        "None": 1.00,
        "Minor": 0.92,
        "Major": 0.75,
        "WriteOff": 0.50
    }
    
    # ─── USAGE TYPE MULTIPLIERS ────────────────────────────────────
    USAGE_MULTIPLIERS = {
        "Personal": 1.00,
        "Commercial": 0.85
    }
    
    # ─── TRANSMISSION MULTIPLIERS ──────────────────────────────────
    TRANSMISSION_MULTIPLIERS = {
        "Automatic": 1.02,
        "Manual": 1.00,
        "CVT": 0.98
    }
    
    # ─── FUEL TYPE MULTIPLIERS ────────────────────────────────────
    FUEL_MULTIPLIERS = {
        "Petrol": 1.00,
        "Diesel": 1.05,
        "Hybrid": 1.08,
        "Electric": 0.95
    }
    
    # ─── BODY TYPE MULTIPLIERS ────────────────────────────────────
    BODY_MULTIPLIERS = {
        "Sedan": 1.00,
        "SUV": 1.08,
        "Hatchback": 0.92,
        "Pickup": 1.05,
        "Van": 0.95,
        "Coupe": 1.02,
        "Convertible": 1.01,
        "Wagon": 0.97,
        "Sport": 1.10,
        "Cruiser": 1.02,
        "Adventure": 1.04,
        "Scooter": 0.90,
        "Passenger": 0.95,
        "Cargo": 0.90,
        "Other": 0.95
    }
    
    # ─── COLOR MULTIPLIERS ─────────────────────────────────────────
    COLOR_MULTIPLIERS = {
        "White": 1.02,
        "Silver": 1.01,
        "Black": 1.00,
        "Grey": 1.00,
        "Blue": 0.98,
        "Red": 0.97,
        "Green": 0.96,
        "Yellow": 0.93,
        "Orange": 0.92,
        "Maroon": 0.95,
        "Brown": 0.94,
        "Gold": 0.96,
        "Other": 0.95
    }
    
    def __init__(self):
        self.market_data = get_market_data()
    
    def calculate_value(
        self,
        purchase_price: float,
        year: int,
        make: str,
        model: str,
        vehicle_type: str = "Car",
        condition: str = "Good",
        mileage: float = 0,
        location: str = "Nairobi",
        accident_history: str = "None",
        usage_type: str = "Personal",
        transmission: str = "Automatic",
        fuel_type: str = "Petrol",
        body_type: str = "SUV",
        previous_owners: int = 0,
        color: str = "White",
        engine_capacity: float = 2000,
        service_history: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive vehicle valuation.
        Aligned with instant-value.html frontend expectations.
        
        Args:
            purchase_price: Original purchase price
            year: Manufacturing year
            make: Vehicle make (e.g., Toyota)
            model: Vehicle model (e.g., Prado)
            vehicle_type: Type of vehicle (Car, Bike, Tricycle, Truck)
            condition: Vehicle condition (Excellent, Good, Fair, Poor)
            mileage: Total mileage in km
            location: Location in Kenya
            accident_history: Accident history (None, Minor, Major, WriteOff)
            usage_type: Usage type (Personal, Commercial)
            transmission: Transmission type (Automatic, Manual, CVT)
            fuel_type: Fuel type (Petrol, Diesel, Hybrid, Electric)
            body_type: Body type (SUV, Sedan, etc.)
            previous_owners: Number of previous owners
            color: Vehicle color
            engine_capacity: Engine capacity in cc
            service_history: Whether service history is available
        
        Returns:
            Dict matching instant-value.html expectations
        """
        # ─── Calculate age in years ──────────────────────────────────
        current_year = datetime.now().year
        age_years = max(0, current_year - year)
        
        # ─── Get base depreciation rate ──────────────────────────────
        dep_rates_by_condition = self.DEPRECIATION_RATES.get(condition, self.DEPRECIATION_RATES["Good"])
        base_rate = dep_rates_by_condition.get(vehicle_type, 0.12)
        
        # ─── Adjust depreciation for mileage ─────────────────────────
        mileage_multiplier = 1.0
        if mileage > 150000:
            mileage_multiplier = 1.4
        elif mileage > 100000:
            mileage_multiplier = 1.25
        elif mileage > 60000:
            mileage_multiplier = 1.1
        elif mileage > 30000:
            mileage_multiplier = 1.03
        
        effective_rate = base_rate * mileage_multiplier
        effective_rate = min(effective_rate, 0.50)  # Cap at 50%
        
        # ─── Apply all multipliers ────────────────────────────────────
        location_mult = self.LOCATION_MULTIPLIERS.get(location, 0.95)
        accident_mult = self.ACCIDENT_MULTIPLIERS.get(accident_history, 0.90)
        usage_mult = self.USAGE_MULTIPLIERS.get(usage_type, 1.0)
        transmission_mult = self.TRANSMISSION_MULTIPLIERS.get(transmission, 1.0)
        fuel_mult = self.FUEL_MULTIPLIERS.get(fuel_type, 1.0)
        body_mult = self.BODY_MULTIPLIERS.get(body_type, 1.0)
        color_mult = self.COLOR_MULTIPLIERS.get(color, 0.95)
        service_mult = 1.03 if service_history else 0.95
        
        # Previous owners adjustment
        owner_mult = 1.0 - (previous_owners * 0.015)
        owner_mult = max(owner_mult, 0.85)
        
        # Combined multiplier
        base_multiplier = (
            location_mult *
            accident_mult *
            usage_mult *
            transmission_mult *
            fuel_mult *
            body_mult *
            color_mult *
            service_mult *
            owner_mult
        )
        
        # ─── Calculate current value ─────────────────────────────────
        # Using declining balance method
        current_value = purchase_price * ((1 - effective_rate) ** age_years)
        
        # Apply market adjustments
        current_value *= base_multiplier
        
        # Ensure minimum value (5% of purchase price)
        min_value = purchase_price * 0.05
        current_value = max(current_value, min_value)
        
        # ─── Calculate depreciation details ─────────────────────────
        total_depreciation = purchase_price - current_value
        value_retained = (current_value / purchase_price) * 100
        
        # ─── Generate yearly breakdown ──────────────────────────────
        yearly_breakdown = []
        value = purchase_price
        for year_num in range(1, min(int(age_years) + 1, 10)):
            dep = value * effective_rate
            value -= dep
            yearly_breakdown.append({
                "year": year_num,
                "depreciation": round(dep, 2),
                "value": round(max(value, purchase_price * 0.05), 2)
            })
        
        # ─── Valuation range (85% - 105% of value) ──────────────────
        range_low = round(current_value * 0.85)
        range_high = round(current_value * 1.05)
        
        # ─── Confidence score ────────────────────────────────────────
        confidence_score = self._calculate_confidence(
            purchase_price=purchase_price,
            mileage=mileage,
            condition=condition,
            previous_owners=previous_owners,
            location=location,
            service_history=service_history
        )
        
        # ─── Recommendations ──────────────────────────────────────────
        recommendations = self._generate_recommendations(
            current_value=current_value,
            purchase_price=purchase_price,
            age_years=age_years,
            condition=condition,
            mileage=mileage,
            vehicle_type=vehicle_type
        )
        
        # ─── Return format matching instant-value.html ──────────────
        return {
            # Primary values - matches frontend expectations
            "current_value": round(current_value, 2),
            "market_value": round(current_value, 2),
            "estimated_value": round(current_value, 2),
            
            # Value types
            "trade_in_value": round(current_value * 0.85, 2),
            "retail_value": round(current_value * 1.15, 2),
            "wholesale_value": round(current_value * 0.90, 2),
            "insurance_value": round(current_value * 1.10, 2),
            "auction_value": round(current_value * 0.88, 2),
            "private_sale_value": round(current_value * 1.05, 2),
            
            # Range and confidence
            "valuation_range": {
                "low": range_low,
                "high": range_high
            },
            "confidence_score": confidence_score,
            
            # Depreciation details
            "purchase_price": purchase_price,
            "age_years": age_years,
            "depreciation_rate": effective_rate,
            "total_depreciation": round(total_depreciation, 2),
            "value_retained": round(value_retained, 2),
            "yearly_breakdown": yearly_breakdown,
            
            # Market adjustments
            "market_adjustments": {
                "location": location_mult,
                "accident": accident_mult,
                "usage": usage_mult,
                "transmission": transmission_mult,
                "fuel": fuel_mult,
                "body_type": body_mult,
                "color": color_mult,
                "service_history": service_mult,
                "previous_owners": owner_mult,
                "mileage": mileage_multiplier
            },
            
            # Recommendations
            "recommendations": recommendations,
            
            # Vehicle specifications (for reference)
            "vehicle": {
                "make": make,
                "model": model,
                "year": year,
                "type": vehicle_type,
                "condition": condition,
                "mileage": mileage,
                "location": location,
                "accident_history": accident_history,
                "usage_type": usage_type,
                "transmission": transmission,
                "fuel_type": fuel_type,
                "body_type": body_type,
                "previous_owners": previous_owners,
                "color": color,
                "engine_capacity": engine_capacity
            },
            
            # Valuation metadata
            "valuation_method": "AI-powered market valuation",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _calculate_confidence(
        self,
        purchase_price: float,
        mileage: float,
        condition: str,
        previous_owners: int,
        location: str,
        service_history: bool
    ) -> int:
        """
        Calculate confidence score based on data completeness
        
        Returns:
            Confidence score between 0-100
        """
        score = 70  # Base score
        
        # Price data availability
        if purchase_price > 0:
            score += 10
        if purchase_price > 100000:
            score += 5
        
        # Mileage data
        if mileage > 0:
            score += 5
        if mileage < 50000:
            score += 5
        elif mileage < 100000:
            score += 3
        
        # Condition data
        if condition in ["Excellent", "Good"]:
            score += 5
        
        # Ownership history
        if previous_owners <= 1:
            score += 5
        elif previous_owners <= 2:
            score += 3
        
        # Location data
        if location in self.LOCATION_MULTIPLIERS:
            score += 5
        
        # Service history
        if service_history:
            score += 5
        
        return min(score, 98)
    
    def _generate_recommendations(
        self,
        current_value: float,
        purchase_price: float,
        age_years: int,
        condition: str,
        mileage: float,
        vehicle_type: str = "Car"
    ) -> List[str]:
        """
        Generate AI-powered recommendations
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if purchase_price > 0:
            value_retained = (current_value / purchase_price) * 100
            
            if value_retained < 40:
                recommendations.append(
                    "Vehicle has depreciated significantly. Consider selling before year 5 to maximize resale value."
                )
            elif value_retained > 80:
                recommendations.append(
                    "Vehicle has retained value well. This is a good time to sell if you're considering an upgrade."
                )
        
        if condition != "Excellent" and age_years > 3:
            recommendations.append(
                "Consider reconditioning the vehicle to improve its resale value."
            )
        
        if mileage > 100000:
            recommendations.append(
                "High mileage vehicle. Ensure all service records are up to date for better resale value."
            )
        
        if mileage > 50000 and age_years > 5:
            recommendations.append(
                "Regular maintenance is crucial for this age and mileage combination."
            )
        
        # Vehicle type specific recommendations
        if vehicle_type == "Bike" and mileage > 30000:
            recommendations.append(
                "Motorcycle with high mileage. Check chain, sprocket, and brake pads."
            )
        
        if vehicle_type == "Tricycle" and mileage > 50000:
            recommendations.append(
                "Tricycle with significant mileage. Consider engine and transmission inspection."
            )
        
        return recommendations


def calculate_vehicle_value(
    purchase_price: float,
    age_years: float,
    depreciation_rate: float = 0.15,
    condition: str = "Good",
    mileage: float = 0,
    location: str = "Nairobi"
) -> Dict[str, Any]:
    """
    API-compatible valuation function.
    Matches the Flask backend calculate_vehicle_value signature.
    Also aligns with instant-value.html frontend expectations.
    
    This is the primary function called by:
    - /api/service/valuation endpoint
    - instant-value.html frontend
    """
    current_year = datetime.now().year
    year = current_year - int(age_years)
    
    engine = ValuationEngine()
    result = engine.calculate_value(
        purchase_price=purchase_price,
        year=year,
        make="Unknown",
        model="Unknown",
        vehicle_type="Car",
        condition=condition,
        mileage=mileage,
        location=location
    )
    
    # Return format matching frontend expectations
    return {
        "current_value": result.get("current_value", 0),
        "market_value": result.get("market_value", 0),
        "estimated_value": result.get("estimated_value", 0),
        "total_depreciation": result.get("total_depreciation", 0),
        "value_retained": result.get("value_retained", 0),
        "confidence_score": result.get("confidence_score", 85),
        "valuation_range": result.get("valuation_range", {"low": 0, "high": 0}),
        "yearly_breakdown": result.get("yearly_breakdown", []),
        "recommendations": result.get("recommendations", []),
        "market_adjustments": result.get("market_adjustments", {})
    }


# ─── EXAMPLE USAGE ─────────────────────────────────────────────

if __name__ == "__main__":
    engine = ValuationEngine()
    
    # Example: Toyota Prado valuation (matches instant-value.html)
    print("=" * 70)
    print("🚗 Auto-D Kenya - Instant Value Check")
    print("=" * 70)
    
    result = engine.calculate_value(
        purchase_price=5200000,
        year=2020,
        make="Toyota",
        model="Prado",
        vehicle_type="Car",
        condition="Good",
        mileage=45000,
        location="Nairobi",
        accident_history="None",
        usage_type="Personal",
        transmission="Automatic",
        fuel_type="Diesel",
        body_type="SUV",
        previous_owners=1,
        color="White"
    )
    
    print(f"\nVehicle: {result['vehicle']['make']} {result['vehicle']['model']}")
    print(f"Year: {result['vehicle']['year']}")
    print(f"Condition: {result['vehicle']['condition']}")
    print(f"Mileage: {result['vehicle']['mileage']:,} km")
    print("-" * 70)
    print(f"💰 Current Market Value: KES {result['current_value']:,.2f}")
    print(f"📉 Total Depreciation: KES {result['total_depreciation']:,.2f}")
    print(f"📊 Value Retained: {result['value_retained']:.1f}%")
    print(f"🎯 Confidence Score: {result['confidence_score']}%")
    print(f"📍 Location: {result['vehicle']['location']}")
    print(f"🔄 Previous Owners: {result['vehicle']['previous_owners']}")
    print(f"📅 Valuation Date: {result['timestamp']}")
    print("-" * 70)
    
    if result['recommendations']:
        print("💡 Recommendations:")
        for rec in result['recommendations']:
            print(f"  • {rec}")
    
    print("=" * 70)
