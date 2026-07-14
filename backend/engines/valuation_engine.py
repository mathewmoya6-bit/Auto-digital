"""
Valuation Engine - Auto-D Kenya
Professional vehicle valuation with market intelligence
Aligned with instant-value.html frontend expectations
Serves: /api/valuation/calculate endpoint
"""

import logging
import math
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


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
    
    # Metadata
    valuation_method: str = "AI-powered market valuation"
    timestamp: str = ""


class DepreciationEngine:
    """Depreciation calculation engine"""
    
    @staticmethod
    def calculate_depreciation(
        purchase_price: float,
        age_years: float,
        rate: float = 0.15,
        method: str = "declining_balance"
    ) -> Dict[str, Any]:
        """
        Calculate depreciation using various methods
        
        Args:
            purchase_price: Original purchase price
            age_years: Age in years
            rate: Annual depreciation rate
            method: 'declining_balance', 'straight_line', or 'double_declining'
        
        Returns:
            Dictionary with depreciation details
        """
        if method == "straight_line":
            annual_depreciation = purchase_price * rate
            total_depreciation = annual_depreciation * age_years
            current_value = max(purchase_price - total_depreciation, 0)
        elif method == "double_declining":
            rate = rate * 2
            current_value = purchase_price * ((1 - rate) ** age_years)
            total_depreciation = purchase_price - current_value
        else:  # declining_balance (default)
            current_value = purchase_price * ((1 - rate) ** age_years)
            total_depreciation = purchase_price - current_value
        
        # Ensure minimum value
        min_value = purchase_price * 0.05
        current_value = max(current_value, min_value)
        
        return {
            "current_value": current_value,
            "total_depreciation": max(total_depreciation, 0),
            "value_retained": (current_value / purchase_price * 100) if purchase_price > 0 else 0,
            "depreciation_rate": rate
        }


class MarketIntelligenceEngine:
    """Market intelligence for vehicle valuation"""
    
    def __init__(self):
        self.market_data = {}
        self._load_market_data()
    
    def _load_market_data(self):
        """Load market data from various sources"""
        try:
            # Try to load from JSON file if exists
            try:
                with open('market_data.json', 'r') as f:
                    self.market_data = json.load(f)
            except FileNotFoundError:
                logger.warning("Market data file not found, using defaults")
                self.market_data = {}
        except Exception as e:
            logger.error(f"Error loading market data: {e}")
            self.market_data = {}
    
    def get_market_adjustments(
        self,
        make: str,
        model: str,
        year: int,
        location: str,
        vehicle_type: str
    ) -> Dict[str, float]:
        """Get market-based adjustments"""
        adjustments = {
            "location_multiplier": 1.0,
            "demand_multiplier": 1.0,
            "seasonal_multiplier": 1.0,
            "market_trend": 1.0
        }
        
        # Location adjustments
        location_multipliers = {
            "Nairobi": 1.05,
            "Mombasa": 1.02,
            "Kisumu": 0.98,
            "Nakuru": 0.97,
            "Eldoret": 0.96,
            "Thika": 0.95,
            "Kiambu": 0.98,
            "Other": 0.90
        }
        adjustments["location_multiplier"] = location_multipliers.get(location, 0.95)
        
        # Popular models demand multiplier
        popular_models = {
            "Toyota Prado": 1.15,
            "Toyota Hilux": 1.12,
            "Toyota Land Cruiser": 1.20,
            "Subaru Forester": 1.08,
            "Nissan X-Trail": 1.05,
            "Isuzu D-Max": 1.10
        }
        model_key = f"{make} {model}"
        adjustments["demand_multiplier"] = popular_models.get(model_key, 1.0)
        
        return adjustments


class ValuationEngine:
    """
    Professional Vehicle Valuation Engine.
    Combines depreciation, market data, and condition analysis.
    Aligned with instant-value.html frontend.
    
    Used by:
    - /api/valuation/calculate endpoint
    - instant-value.html frontend
    - Vehicle valuation reports
    """
    
    # ─── DEPRECIATION RATES BY CONDITION ──────────────────────────
    DEPRECIATION_RATES = {
        "Excellent": {
            "Car": 0.08,
            "Bike": 0.10,
            "Tricycle": 0.12,
            "Truck": 0.10,
            "SUV": 0.09,
            "Pickup": 0.10,
            "Minibus": 0.11
        },
        "Very Good": {
            "Car": 0.10,
            "Bike": 0.12,
            "Tricycle": 0.14,
            "Truck": 0.12,
            "SUV": 0.11,
            "Pickup": 0.12,
            "Minibus": 0.13
        },
        "Good": {
            "Car": 0.12,
            "Bike": 0.15,
            "Tricycle": 0.18,
            "Truck": 0.15,
            "SUV": 0.13,
            "Pickup": 0.14,
            "Minibus": 0.15
        },
        "Fair": {
            "Car": 0.18,
            "Bike": 0.22,
            "Tricycle": 0.25,
            "Truck": 0.22,
            "SUV": 0.19,
            "Pickup": 0.20,
            "Minibus": 0.21
        },
        "Poor": {
            "Car": 0.25,
            "Bike": 0.30,
            "Tricycle": 0.35,
            "Truck": 0.30,
            "SUV": 0.26,
            "Pickup": 0.27,
            "Minibus": 0.28
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
        "Malindi": 0.91,
        "Nanyuki": 0.90,
        "Other": 0.90
    }
    
    # ─── ACCIDENT HISTORY MULTIPLIERS ─────────────────────────────
    ACCIDENT_MULTIPLIERS = {
        "None": 1.00,
        "Minor": 0.92,
        "Major": 0.75,
        "WriteOff": 0.50,
        "Total Loss": 0.50
    }
    
    # ─── USAGE TYPE MULTIPLIERS ────────────────────────────────────
    USAGE_MULTIPLIERS = {
        "Personal": 1.00,
        "Commercial": 0.85,
        "Fleet": 0.80,
        "Rental": 0.75
    }
    
    # ─── TRANSMISSION MULTIPLIERS ──────────────────────────────────
    TRANSMISSION_MULTIPLIERS = {
        "Automatic": 1.02,
        "Manual": 1.00,
        "CVT": 0.98,
        "Semi-Automatic": 1.01
    }
    
    # ─── FUEL TYPE MULTIPLIERS ────────────────────────────────────
    FUEL_MULTIPLIERS = {
        "Petrol": 1.00,
        "Diesel": 1.05,
        "Hybrid": 1.08,
        "Electric": 0.95,
        "Gas/LPG": 0.92
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
        "Saloon": 1.00,
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
        self.market_intelligence = MarketIntelligenceEngine()
        self.depreciation_engine = DepreciationEngine()
    
    def calculate_value(
        self,
        purchase_price: float,
        year: int,
        make: str = "Unknown",
        model: str = "Unknown",
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
            purchase_price: Original purchase price in KES
            year: Manufacturing year
            make: Vehicle make (e.g., Toyota)
            model: Vehicle model (e.g., Prado)
            vehicle_type: Type of vehicle (Car, Bike, Tricycle, Truck, SUV, Pickup, Minibus)
            condition: Vehicle condition (Excellent, Very Good, Good, Fair, Poor)
            mileage: Total mileage in km
            location: Location in Kenya
            accident_history: Accident history (None, Minor, Major, WriteOff, Total Loss)
            usage_type: Usage type (Personal, Commercial, Fleet, Rental)
            transmission: Transmission type (Automatic, Manual, CVT, Semi-Automatic)
            fuel_type: Fuel type (Petrol, Diesel, Hybrid, Electric, Gas/LPG)
            body_type: Body type (SUV, Sedan, Pickup, etc.)
            previous_owners: Number of previous owners
            color: Vehicle color
            engine_capacity: Engine capacity in cc
            service_history: Whether service history is available
        
        Returns:
            Dict matching instant-value.html expectations
        """
        try:
            logger.info(f"Calculating valuation for {make} {model} ({year})")
            
            # ─── Validate inputs ──────────────────────────────────────
            if purchase_price <= 0:
                raise ValueError("purchase_price must be positive")
            
            if year < 1900 or year > datetime.now().year + 1:
                raise ValueError(f"Invalid year: {year}")
            
            # ─── Calculate age in years ──────────────────────────────
            current_year = datetime.now().year
            age_years = max(0.5, float(current_year - year))
            
            # ─── Get base depreciation rate ──────────────────────────
            dep_rates_by_condition = self.DEPRECIATION_RATES.get(condition, self.DEPRECIATION_RATES["Good"])
            base_rate = dep_rates_by_condition.get(vehicle_type, 0.12)
            
            # ─── Adjust depreciation for mileage ─────────────────────
            mileage_multiplier = self._get_mileage_multiplier(mileage, age_years)
            effective_rate = min(base_rate * mileage_multiplier, 0.50)
            
            # ─── Get all multipliers ──────────────────────────────────
            multipliers = self._get_all_multipliers(
                location=location,
                accident_history=accident_history,
                usage_type=usage_type,
                transmission=transmission,
                fuel_type=fuel_type,
                body_type=body_type,
                color=color,
                service_history=service_history,
                previous_owners=previous_owners,
                mileage=age_years
            )
            
            # ─── Calculate current value ─────────────────────────────
            depreciation_result = self.depreciation_engine.calculate_depreciation(
                purchase_price=purchase_price,
                age_years=age_years,
                rate=effective_rate,
                method="declining_balance"
            )
            
            current_value = depreciation_result["current_value"]
            
            # Apply all multipliers
            for multiplier in multipliers.values():
                current_value *= multiplier
            
            # Ensure minimum value (5% of purchase price)
            min_value = purchase_price * 0.05
            current_value = max(current_value, min_value)
            
            # ─── Calculate depreciation details ─────────────────────
            total_depreciation = purchase_price - current_value
            value_retained = (current_value / purchase_price * 100) if purchase_price > 0 else 0
            
            # ─── Generate yearly breakdown ──────────────────────────
            yearly_breakdown = self._generate_yearly_breakdown(
                purchase_price, effective_rate, age_years
            )
            
            # ─── Valuation range ─────────────────────────────────────
            range_low = round(current_value * 0.85, 2)
            range_high = round(current_value * 1.15, 2)
            
            # ─── Confidence score ────────────────────────────────────
            confidence_score = self._calculate_confidence(
                purchase_price=purchase_price,
                mileage=mileage,
                condition=condition,
                previous_owners=previous_owners,
                location=location,
                service_history=service_history
            )
            
            # ─── Market adjustments ──────────────────────────────────
            market_adjustments = self.market_intelligence.get_market_adjustments(
                make=make,
                model=model,
                year=year,
                location=location,
                vehicle_type=vehicle_type
            )
            
            # ─── Recommendations ────────────────────────────────────
            recommendations = self._generate_recommendations(
                current_value=current_value,
                purchase_price=purchase_price,
                age_years=age_years,
                condition=condition,
                mileage=mileage,
                vehicle_type=vehicle_type
            )
            
            # ─── Return format matching instant-value.html ──────────
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
                    "min": range_low,
                    "max": range_high,
                    "low": range_low,
                    "high": range_high
                },
                "confidence_score": confidence_score,
                
                # Depreciation details
                "purchase_price": purchase_price,
                "age_years": round(age_years, 1),
                "depreciation_rate": round(effective_rate, 4),
                "total_depreciation": round(total_depreciation, 2),
                "value_retained": round(value_retained, 2),
                "yearly_breakdown": yearly_breakdown,
                
                # Market adjustments
                "market_adjustments": {
                    "location": multipliers.get("location", 1.0),
                    "accident": multipliers.get("accident", 1.0),
                    "usage": multipliers.get("usage", 1.0),
                    "transmission": multipliers.get("transmission", 1.0),
                    "fuel": multipliers.get("fuel", 1.0),
                    "body_type": multipliers.get("body_type", 1.0),
                    "color": multipliers.get("color", 1.0),
                    "service_history": multipliers.get("service_history", 1.0),
                    "previous_owners": multipliers.get("previous_owners", 1.0),
                    "mileage": mileage_multiplier,
                    **market_adjustments
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
                    "engine_capacity": engine_capacity,
                    "service_history": service_history
                },
                
                # Valuation metadata
                "valuation_method": "AI-powered market valuation",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Valuation calculation error: {e}", exc_info=True)
            raise
    
    def _get_mileage_multiplier(self, mileage: float, age_years: float) -> float:
        """Calculate mileage multiplier based on usage"""
        if mileage == 0:
            return 1.0
        
        annual_mileage = mileage / age_years if age_years > 0 else 0
        
        if annual_mileage > 30000:
            return 1.5
        elif annual_mileage > 20000:
            return 1.3
        elif annual_mileage > 15000:
            return 1.15
        elif annual_mileage > 10000:
            return 1.05
        elif annual_mileage > 5000:
            return 1.0
        else:
            return 0.95
    
    def _get_all_multipliers(
        self,
        location: str,
        accident_history: str,
        usage_type: str,
        transmission: str,
        fuel_type: str,
        body_type: str,
        color: str,
        service_history: bool,
        previous_owners: int,
        mileage: float
    ) -> Dict[str, float]:
        """Get all multipliers in one place"""
        return {
            "location": self.LOCATION_MULTIPLIERS.get(location, 0.95),
            "accident": self.ACCIDENT_MULTIPLIERS.get(accident_history, 0.90),
            "usage": self.USAGE_MULTIPLIERS.get(usage_type, 1.0),
            "transmission": self.TRANSMISSION_MULTIPLIERS.get(transmission, 1.0),
            "fuel": self.FUEL_MULTIPLIERS.get(fuel_type, 1.0),
            "body_type": self.BODY_MULTIPLIERS.get(body_type, 1.0),
            "color": self.COLOR_MULTIPLIERS.get(color, 0.95),
            "service_history": 1.03 if service_history else 0.95,
            "previous_owners": max(1.0 - (previous_owners * 0.015), 0.85)
        }
    
    def _generate_yearly_breakdown(
        self,
        purchase_price: float,
        rate: float,
        age_years: float
    ) -> List[Dict[str, Any]]:
        """Generate yearly depreciation breakdown"""
        breakdown = []
        value = purchase_price
        
        max_years = min(int(age_years) + 1, 10)
        
        for year_num in range(1, max_years + 1):
            if year_num <= age_years:
                dep = value * rate
                value -= dep
            else:
                dep = 0
            
            breakdown.append({
                "year": year_num,
                "depreciation": round(dep, 2),
                "value": round(max(value, purchase_price * 0.05), 2),
                "percentage": round((1 - (value / purchase_price)) * 100, 2) if purchase_price > 0 else 0
            })
            
            if value <= purchase_price * 0.05:
                break
        
        return breakdown
    
    def _calculate_confidence(
        self,
        purchase_price: float,
        mileage: float,
        condition: str,
        previous_owners: int,
        location: str,
        service_history: bool
    ) -> int:
        """Calculate confidence score based on data completeness"""
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
        if condition in ["Excellent", "Very Good"]:
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
        age_years: float,
        condition: str,
        mileage: float,
        vehicle_type: str
    ) -> List[str]:
        """Generate AI-powered recommendations"""
        recommendations = []
        
        # Value retention analysis
        if purchase_price > 0:
            value_retained = (current_value / purchase_price) * 100
            
            if value_retained < 40 and age_years < 5:
                recommendations.append(
                    "⚠️ Vehicle has depreciated significantly for its age. Consider selling before 5 years to maximize resale value."
                )
            elif value_retained > 80 and age_years > 3:
                recommendations.append(
                    "✅ Vehicle has retained value well above average. This is an excellent time to sell if considering an upgrade."
                )
            elif 60 <= value_retained <= 80:
                recommendations.append(
                    "📊 Vehicle value retention is average. Regular maintenance will help maintain its value."
                )
        
        # Age-based recommendations
        if age_years > 10:
            recommendations.append(
                "🔧 Vehicle is over 10 years old. Focus on reliability rather than resale value."
            )
        elif 5 < age_years <= 10:
            recommendations.append(
                "🛠️ Vehicle is entering mid-life. Consider major service items like timing belt and suspension."
            )
        
        # Condition-based recommendations
        if condition == "Excellent" or condition == "Very Good":
            recommendations.append(
                "🌟 Vehicle is in excellent condition - this significantly boosts resale value."
            )
        elif condition == "Fair":
            recommendations.append(
                "🔄 Consider addressing cosmetic and mechanical issues to improve resale value."
            )
        elif condition == "Poor":
            recommendations.append(
                "🔴 Vehicle requires significant attention. Consider selling as-is or investing in restoration."
            )
        
        # Mileage-based recommendations
        if mileage > 150000:
            recommendations.append(
                "📏 High mileage vehicle. Ensure comprehensive service records are available."
            )
        elif mileage > 100000:
            recommendations.append(
                "📏 Moderate mileage. Regular maintenance is crucial for value retention."
            )
        
        # Vehicle type specific
        if vehicle_type == "Bike" and mileage > 30000:
            recommendations.append(
                "🏍️ Motorcycle with high mileage. Check chain, sprocket, and brake pads for wear."
            )
        elif vehicle_type == "Tricycle" and mileage > 50000:
            recommendations.append(
                "🛺 Tricycle with significant mileage. Consider engine and transmission inspection."
            )
        elif vehicle_type in ["SUV", "Pickup"] and mileage > 80000:
            recommendations.append(
                "🚜 4x4 vehicle with significant mileage. Check 4WD system and suspension components."
            )
        
        return recommendations


# ─── API COMPATIBLE FUNCTIONS ──────────────────────────────────

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
    - /api/valuation/calculate endpoint
    - instant-value.html frontend
    """
    try:
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
            "success": True,
            "data": {
                "current_value": result.get("current_value", 0),
                "market_value": result.get("market_value", 0),
                "estimated_value": result.get("estimated_value", 0),
                "trade_in_value": result.get("trade_in_value", 0),
                "retail_value": result.get("retail_value", 0),
                "total_depreciation": result.get("total_depreciation", 0),
                "value_retained": result.get("value_retained", 0),
                "confidence_score": result.get("confidence_score", 85),
                "valuation_range": result.get("valuation_range", {"min": 0, "max": 0}),
                "yearly_breakdown": result.get("yearly_breakdown", []),
                "recommendations": result.get("recommendations", []),
                "market_adjustments": result.get("market_adjustments", {})
            }
        }
    except Exception as e:
        logger.error(f"Valuation calculation error: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Valuation failed",
            "message": str(e)
        }


def get_market_data() -> Dict[str, Any]:
    """Get market data for vehicle valuation"""
    return {
        "popular_models": [
            "Toyota Prado",
            "Toyota Hilux",
            "Toyota Land Cruiser",
            "Subaru Forester",
            "Nissan X-Trail",
            "Isuzu D-Max"
        ],
        "market_trends": {
            "SUV": "high_demand",
            "Pickup": "high_demand",
            "Sedan": "moderate",
            "Hatchback": "moderate"
        }
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
        vehicle_type="SUV",
        condition="Good",
        mileage=45000,
        location="Nairobi",
        accident_history="None",
        usage_type="Personal",
        transmission="Automatic",
        fuel_type="Diesel",
        body_type="SUV",
        previous_owners=1,
        color="White",
        service_history=True
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
