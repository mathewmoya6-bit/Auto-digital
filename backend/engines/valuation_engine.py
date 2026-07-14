"""
Valuation Engine - Auto-D Kenya
Professional vehicle valuation with market intelligence
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from .depreciation_engine import calculate_depreciation
from .market_intelligence_engine import get_market_data


@dataclass
class ValuationResult:
    """Complete valuation result"""
    current_value: float = 0.0
    market_value: float = 0.0
    estimated_value: float = 0.0
    trade_in_value: float = 0.0
    retail_value: float = 0.0
    wholesale_value: float = 0.0
    insurance_value: float = 0.0
    auction_value: float = 0.0
    private_sale_value: float = 0.0
    valuation_range: Dict[str, float] = field(default_factory=dict)
    confidence_score: int = 85
    depreciation: Dict[str, Any] = field(default_factory=dict)
    market_adjustments: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class ValuationEngine:
    """
    Professional Vehicle Valuation Engine.
    Combines depreciation, market data, and condition analysis.
    """
    
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
        previous_owners: int = 0,
        modifications: List[str] = None,
        service_history: bool = True,
        color: str = "White"
    ) -> ValuationResult:
        """
        Calculate comprehensive vehicle valuation.
        
        Returns:
            ValuationResult with all value types
        """
        age_years = max(0, datetime.now().year - year)
        
        # ─── Base Depreciation ────────────────────────────────────
        dep_result = calculate_depreciation(
            purchase_price=purchase_price,
            age_years=age_years,
            vehicle_type=vehicle_type,
            condition=condition,
            mileage=mileage
        )
        
        base_value = dep_result["current_value"]
        
        # ─── Market Adjustments ────────────────────────────────────
        market_adjustments = {}
        
        # Location adjustment
        location_multipliers = {
            "Nairobi": 1.05,
            "Mombasa": 1.02,
            "Kisumu": 0.98,
            "Nakuru": 0.97,
            "Eldoret": 0.96,
            "Other": 0.90
        }
        location_mult = location_multipliers.get(location, 0.95)
        market_adjustments["location"] = location_mult
        
        # Accident history adjustment
        accident_multipliers = {
            "None": 1.00,
            "Minor": 0.92,
            "Major": 0.75,
            "WriteOff": 0.50
        }
        accident_mult = accident_multipliers.get(accident_history, 0.90)
        market_adjustments["accident"] = accident_mult
        
        # Previous owners adjustment
        owner_mult = 1.0 - (previous_owners * 0.015)
        owner_mult = max(owner_mult, 0.85)
        market_adjustments["owners"] = owner_mult
        
        # Color adjustment
        color_multipliers = {
            "White": 1.02,
            "Silver": 1.01,
            "Black": 1.00,
            "Grey": 1.00,
            "Blue": 0.98,
            "Red": 0.97,
            "Green": 0.96,
            "Yellow": 0.93,
            "Orange": 0.92,
            "Other": 0.95
        }
        color_mult = color_multipliers.get(color, 0.95)
        market_adjustments["color"] = color_mult
        
        # Service history adjustment
        service_mult = 1.03 if service_history else 0.95
        market_adjustments["service_history"] = service_mult
        
        # Condition adjustment
        condition_multipliers = {
            "Excellent": 1.08,
            "Good": 1.00,
            "Fair": 0.90,
            "Poor": 0.80
        }
        cond_mult = condition_multipliers.get(condition, 1.0)
        market_adjustments["condition"] = cond_mult
        
        # Market demand adjustment (simplified)
        demand_mult = self.market_data.get("demand_multiplier", {}).get(
            f"{make}_{model}", 1.0
        )
        market_adjustments["demand"] = demand_mult
        
        # ─── Calculate Values ─────────────────────────────────────
        adjusted_value = base_value * (
            location_mult *
            accident_mult *
            owner_mult *
            color_mult *
            service_mult *
            cond_mult *
            demand_mult
        )
        
        # Minimum value (5% of purchase price)
        min_value = purchase_price * 0.05
        adjusted_value = max(adjusted_value, min_value)
        
        # Different value types
        trade_in_value = adjusted_value * 0.85  # 85% of market
        wholesale_value = adjusted_value * 0.90  # 90% of market
        retail_value = adjusted_value * 1.15  # 115% of market
        private_sale_value = adjusted_value * 1.05  # 105% of market
        insurance_value = adjusted_value * 1.10  # 110% of market
        auction_value = adjusted_value * 0.88  # 88% of market
        
        # Valuation range
        valuation_range = {
            "low": round(adjusted_value * 0.85),
            "high": round(adjusted_value * 1.05)
        }
        
        # Confidence score
        confidence_score = self._calculate_confidence(
            purchase_price=purchase_price,
            mileage=mileage,
            condition=condition,
            previous_owners=previous_owners,
            location=location,
            service_history=service_history
        )
        
        # Recommendations
        recommendations = self._generate_recommendations(
            adjusted_value=adjusted_value,
            purchase_price=purchase_price,
            age_years=age_years,
            condition=condition,
            mileage=mileage
        )
        
        return ValuationResult(
            current_value=round(adjusted_value, 2),
            market_value=round(adjusted_value, 2),
            estimated_value=round(adjusted_value, 2),
            trade_in_value=round(trade_in_value, 2),
            retail_value=round(retail_value, 2),
            wholesale_value=round(wholesale_value, 2),
            insurance_value=round(insurance_value, 2),
            auction_value=round(auction_value, 2),
            private_sale_value=round(private_sale_value, 2),
            valuation_range=valuation_range,
            confidence_score=confidence_score,
            depreciation=dep_result,
            market_adjustments=market_adjustments,
            recommendations=recommendations
        )
    
    def _calculate_confidence(
        self,
        purchase_price: float,
        mileage: float,
        condition: str,
        previous_owners: int,
        location: str,
        service_history: bool
    ) -> int:
        """Calculate confidence score"""
        score = 70
        
        if purchase_price > 0:
            score += 10
        if purchase_price > 100000:
            score += 5
        
        if mileage > 0:
            score += 5
        if mileage < 50000:
            score += 5
        elif mileage < 100000:
            score += 3
        
        if condition in ["Excellent", "Good"]:
            score += 5
        
        if previous_owners <= 1:
            score += 5
        
        if service_history:
            score += 5
        
        if location in ["Nairobi", "Mombasa"]:
            score += 5
        
        return min(score, 98)
    
    def _generate_recommendations(
        self,
        adjusted_value: float,
        purchase_price: float,
        age_years: int,
        condition: str,
        mileage: float
    ) -> List[str]:
        """Generate valuation recommendations"""
        recommendations = []
        
        value_retained = (adjusted_value / purchase_price) * 100 if purchase_price > 0 else 0
        
        if value_retained < 40:
            recommendations.append(
                "Vehicle has depreciated significantly. Consider selling before year 5."
            )
        elif value_retained > 80:
            recommendations.append(
                "Vehicle has retained value well. Good time to sell if considering upgrade."
            )
        
        if condition != "Excellent" and age_years > 3:
            recommendations.append(
                "Consider reconditioning to improve resale value."
            )
        
        if mileage > 100000:
            recommendations.append(
                "High mileage vehicle. Ensure service records are up to date."
            )
        
        return recommendations


def calculate_vehicle_value(
    purchase_price: float,
    age_years: float,
    depreciation_rate: float = 0.15,
    condition: str = "Good",
    mileage: float = 0
) -> Dict[str, Any]:
    """
    API-compatible valuation function (simplified).
    Matches the Flask backend calculate_vehicle_value signature.
    """
    current_year = datetime.now().year
    year = current_year - int(age_years)
    
    engine = ValuationEngine()
    result = engine.calculate_value(
        purchase_price=purchase_price,
        year=year,
        make="Unknown",
        model="Unknown",
        condition=condition,
        mileage=mileage
    )
    
    return {
        "current_value": result.current_value,
        "market_value": result.market_value,
        "estimated_value": result.estimated_value,
        "total_depreciation": result.depreciation.get("total_depreciation", 0),
        "value_retained": result.depreciation.get("value_retained", 0),
        "confidence_score": result.confidence_score,
        "valuation_range": result.valuation_range,
        "recommendations": result.recommendations,
        "market_adjustments": result.market_adjustments
    }
