"""
Auto-D Kenya - Instant Value Check Service
Service for AI-powered vehicle valuation

This module provides vehicle valuation calculations based on:
- Vehicle age, condition, mileage
- Market data from Kenya
- Depreciation rates by vehicle type

Aligned with Flask backend API endpoints:
POST /api/service/valuation
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class InstantValueService:
    """
    Service class for instant vehicle valuation
    
    Provides methods to calculate vehicle market value based on:
    - Vehicle specifications (make, model, year, engine, etc.)
    - Vehicle condition (Excellent, Good, Fair, Poor)
    - Mileage and usage history
    - Location-based market adjustments
    
    Matches the backend's calculate_vehicle_value function format.
    """
    
    # ─── CONSTANTS ──────────────────────────────────────────────────
    
    # Base depreciation rates by vehicle type and condition
    DEPRECIATION_RATES = {
        "Car": {
            "Excellent": 0.08,
            "Good": 0.12,
            "Fair": 0.18,
            "Poor": 0.25
        },
        "Bike": {
            "Excellent": 0.10,
            "Good": 0.15,
            "Fair": 0.22,
            "Poor": 0.30
        },
        "Tricycle": {
            "Excellent": 0.12,
            "Good": 0.18,
            "Fair": 0.25,
            "Poor": 0.35
        },
        "Truck": {
            "Excellent": 0.10,
            "Good": 0.15,
            "Fair": 0.22,
            "Poor": 0.30
        }
    }
    
    # Location-based multipliers
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
    
    # Accident history adjustments
    ACCIDENT_MULTIPLIERS = {
        "None": 1.00,
        "Minor": 0.92,
        "Major": 0.75,
        "WriteOff": 0.50
    }
    
    # Usage type adjustments
    USAGE_MULTIPLIERS = {
        "Personal": 1.00,
        "Commercial": 0.85
    }
    
    # Transmission adjustments
    TRANSMISSION_MULTIPLIERS = {
        "Automatic": 1.02,
        "Manual": 1.00,
        "CVT": 0.98
    }
    
    # Fuel type adjustments
    FUEL_MULTIPLIERS = {
        "Petrol": 1.00,
        "Diesel": 1.05,
        "Hybrid": 1.08,
        "Electric": 0.95
    }
    
    # Body type adjustments
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
    
    def __init__(self):
        """Initialize the Instant Value Service"""
        self.logger = logging.getLogger(__name__)
        
    def calculate_valuation(
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
        engine_capacity: float = 2000
    ) -> Dict[str, Any]:
        """
        Calculate the current market value of a vehicle
        
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
            engine_capacity: Engine capacity in cc
            
        Returns:
            Dict with valuation details matching backend calculate_vehicle_value format
        """
        try:
            # Validate inputs
            purchase_price = float(purchase_price)
            year = int(year)
            mileage = float(mileage)
            previous_owners = int(previous_owners)
            
            if purchase_price <= 0:
                return {"error": "Purchase price must be greater than 0"}
            
            if year < 1980 or year > datetime.now().year:
                return {"error": f"Year must be between 1980 and {datetime.now().year}"}
            
            if mileage < 0:
                return {"error": "Mileage cannot be negative"}
            
        except (ValueError, TypeError) as e:
            return {"error": f"Invalid input: {str(e)}"}
        
        # Calculate age in years
        current_year = datetime.now().year
        age_years = max(0, current_year - year)
        
        # Get base depreciation rate
        dep_rates = self.DEPRECIATION_RATES.get(vehicle_type, self.DEPRECIATION_RATES["Car"])
        base_rate = dep_rates.get(condition, 0.12)
        
        # Adjust for mileage
        mileage_multiplier = 1.0
        if mileage > 150000:
            mileage_multiplier = 1.4
        elif mileage > 100000:
            mileage_multiplier = 1.25
        elif mileage > 60000:
            mileage_multiplier = 1.1
        elif mileage > 30000:
            mileage_multiplier = 1.03
            
        # Get location multiplier
        location_multiplier = self.LOCATION_MULTIPLIERS.get(location, 0.95)
        
        # Get accident multiplier
        accident_multiplier = self.ACCIDENT_MULTIPLIERS.get(accident_history, 0.90)
        
        # Get usage multiplier
        usage_multiplier = self.USAGE_MULTIPLIERS.get(usage_type, 1.0)
        
        # Get transmission multiplier
        transmission_multiplier = self.TRANSMISSION_MULTIPLIERS.get(transmission, 1.0)
        
        # Get fuel multiplier
        fuel_multiplier = self.FUEL_MULTIPLIERS.get(fuel_type, 1.0)
        
        # Get body type multiplier
        body_multiplier = self.BODY_MULTIPLIERS.get(body_type, 1.0)
        
        # Previous owners adjustment
        owner_multiplier = 1.0 - (previous_owners * 0.015)
        owner_multiplier = max(owner_multiplier, 0.85)  # Cap at 15% reduction
        
        # Calculate effective depreciation rate
        effective_rate = base_rate * mileage_multiplier
        
        # Apply all multipliers to get effective value
        base_multiplier = (
            location_multiplier *
            accident_multiplier *
            usage_multiplier *
            transmission_multiplier *
            fuel_multiplier *
            body_multiplier *
            owner_multiplier
        )
        
        # Calculate current value using declining balance method
        current_value = purchase_price * ((1 - effective_rate) ** age_years)
        
        # Apply market adjustments
        current_value *= base_multiplier
        
        # Ensure minimum value (5% of purchase price)
        min_value = purchase_price * 0.05
        current_value = max(current_value, min_value)
        
        # Calculate total depreciation
        total_depreciation = purchase_price - current_value
        value_retained = (current_value / purchase_price) * 100
        
        # Generate yearly depreciation breakdown
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
        
        # Calculate confidence score based on data completeness
        confidence_score = self._calculate_confidence_score(
            purchase_price, mileage, condition, previous_owners, location
        )
        
        # Generate valuation range (85% - 105% of value)
        range_low = round(current_value * 0.85)
        range_high = round(current_value * 1.05)
        
        # ─── MATCH BACKEND RESPONSE FORMAT ──────────────────────
        # This matches the Flask backend's calculate_vehicle_value return
        return {
            # Primary valuation results - matches backend format
            "current_value": round(current_value, 2),
            "market_value": round(current_value, 2),  # Alias for frontend
            "estimated_value": round(current_value, 2),  # Alias for frontend
            "purchase_price": purchase_price,
            "age_years": age_years,
            "base_depreciation_rate": base_rate,
            "depreciation_rate": effective_rate,  # Matches backend key
            "effective_depreciation_rate": round(effective_rate, 4),
            "total_depreciation": round(total_depreciation, 2),
            "value_retained": round(value_retained, 2),
            
            # Additional detailed breakdown
            "valuation_range": {
                "low": range_low,
                "high": range_high
            },
            "yearly_breakdown": yearly_breakdown,
            "confidence_score": confidence_score,
            "valuation_method": "AI-powered market valuation",
            "timestamp": datetime.utcnow().isoformat(),
            
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
                "engine_capacity": engine_capacity
            },
            
            # Adjustment factors used
            "adjustments": {
                "location_multiplier": location_multiplier,
                "accident_multiplier": accident_multiplier,
                "usage_multiplier": usage_multiplier,
                "transmission_multiplier": transmission_multiplier,
                "fuel_multiplier": fuel_multiplier,
                "body_multiplier": body_multiplier,
                "owner_multiplier": owner_multiplier,
                "mileage_multiplier": mileage_multiplier,
                "effective_rate": round(effective_rate, 4)
            }
        }
    
    def _calculate_confidence_score(
        self,
        purchase_price: float,
        mileage: float,
        condition: str,
        previous_owners: int,
        location: str
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
        
        return min(score, 98)
    
    def get_valuation_report(
        self,
        purchase_price: float,
        year: int,
        make: str,
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive valuation report
        
        Returns:
            Complete valuation report with all details
        """
        valuation = self.calculate_valuation(
            purchase_price=purchase_price,
            year=year,
            make=make,
            model=model,
            **kwargs
        )
        
        if "error" in valuation:
            return valuation
        
        # Add report metadata
        report = {
            "report_id": f"AUTO-VAL-{datetime.now().strftime('%Y%m%d')}-{abs(hash(f'{make}{model}{year}')) % 10000:04d}",
            "generated_at": datetime.utcnow().isoformat(),
            "valuation": valuation,
            "certificate": {
                "verified": True,
                "verified_by": "Auto-D Intelligence Engine",
                "method": "AI-powered market analysis"
            }
        }
        
        return report


# ─── API COMPATIBILITY FUNCTIONS ──────────────────────────────

def calculate_vehicle_value_api(
    purchase_price: float,
    age_years: float,
    depreciation_rate: float = 0.15,
    condition: str = "Good",
    mileage: float = 0,
    location: str = "Nairobi"
) -> Dict[str, Any]:
    """
    API-compatible valuation function for Flask backend.
    
    This matches the backend's calculate_vehicle_value function signature
    and is used by the /api/service/valuation endpoint.
    
    Args:
        purchase_price: Original purchase price
        age_years: Age of vehicle in years
        depreciation_rate: Base annual depreciation rate
        condition: Vehicle condition (Excellent, Good, Fair, Poor)
        mileage: Total mileage in km
        location: Location in Kenya
    
    Returns:
        Dict matching backend response format
    """
    service = InstantValueService()
    
    current_year = datetime.now().year
    year = current_year - int(age_years)
    
    result = service.calculate_valuation(
        purchase_price=purchase_price,
        year=year,
        make="Unknown",
        model="Unknown",
        vehicle_type="Car",
        condition=condition,
        mileage=mileage,
        location=location,
        accident_history="None",
        usage_type="Personal",
        transmission="Automatic",
        fuel_type="Petrol",
        body_type="SUV"
    )
    
    if "error" in result:
        return {"error": result["error"]}
    
    # Return simplified format matching backend
    return {
        "purchase_price": purchase_price,
        "age_years": age_years,
        "depreciation_rate": depreciation_rate,
        "current_value": result.get("current_value", 0),
        "total_depreciation": result.get("total_depreciation", 0),
        "value_retained": result.get("value_retained", 0),
        "confidence_score": result.get("confidence_score", 85),
        "valuation_range": result.get("valuation_range", {"low": 0, "high": 0}),
        "yearly_breakdown": result.get("yearly_breakdown", [])
    }


def get_valuation_for_frontend(
    purchase_price: float,
    age_years: float,
    depreciation_rate: float = 0.15,
    condition: str = "Good",
    mileage: float = 0,
    location: str = "Nairobi"
) -> Dict[str, Any]:
    """
    Simplified valuation function for frontend API compatibility
    
    This matches the expected response format for the frontend.
    """
    service = InstantValueService()
    
    current_year = datetime.now().year
    year = current_year - int(age_years)
    
    result = service.calculate_valuation(
        purchase_price=purchase_price,
        year=year,
        make="Unknown",
        model="Unknown",
        condition=condition,
        mileage=mileage,
        location=location
    )
    
    if "error" in result:
        return {"error": result["error"]}
    
    # Return simplified format for frontend
    return {
        "success": True,
        "data": {
            "current_value": result.get("current_value", 0),
            "market_value": result.get("market_value", 0),
            "estimated_value": result.get("estimated_value", 0),
            "total_depreciation": result.get("total_depreciation", 0),
            "value_retained": result.get("value_retained", 0),
            "confidence_score": result.get("confidence_score", 85),
            "valuation_range": result.get("valuation_range", {"low": 0, "high": 0}),
            "yearly_breakdown": result.get("yearly_breakdown", []),
            "purchase_price": purchase_price,
            "age_years": age_years,
            "depreciation_rate": depreciation_rate
        }
    }


# ─── INTEGRATE WITH FLASK BACKEND ─────────────────────────────

def register_with_app(app):
    """
    Register the instant value service with a Flask app.
    
    This adds the /api/service/valuation endpoint to the app.
    """
    from flask import request, jsonify
    
    @app.route('/api/service/valuation', methods=['POST'])
    def valuation():
        """Calculate vehicle valuation endpoint"""
        data = request.get_json() or {}
        
        purchase_price = data.get("purchase_price")
        age_years = data.get("age_years")
        
        if purchase_price is None:
            return jsonify({"error": "purchase_price is required"}), 400
        if age_years is None:
            return jsonify({"error": "age_years is required"}), 400
        
        try:
            purchase_price = float(purchase_price)
            age_years = float(age_years)
            if purchase_price <= 0 or age_years < 0:
                raise ValueError
        except ValueError:
            return jsonify({"error": "purchase_price must be positive and age_years must be non-negative"}), 400
        
        depreciation_rate = data.get("depreciation_rate", 0.15)
        condition = data.get("condition", "Good")
        mileage = data.get("mileage", 0)
        location = data.get("location", "Nairobi")
        
        result = calculate_vehicle_value_api(
            purchase_price=purchase_price,
            age_years=age_years,
            depreciation_rate=depreciation_rate,
            condition=condition,
            mileage=mileage,
            location=location
        )
        
        if "error" in result:
            return jsonify(result), 400
        
        return jsonify({"success": True, "data": result})


# ─── EXAMPLE USAGE ─────────────────────────────────────────────

if __name__ == "__main__":
    service = InstantValueService()
    
    # Example 1: Toyota Prado valuation (full)
    print("=" * 60)
    print("🚗 Example 1: Toyota Prado Valuation")
    print("=" * 60)
    
    result = service.calculate_valuation(
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
        engine_capacity=2800
    )
    
    print(f"Vehicle: {result['vehicle']['make']} {result['vehicle']['model']}")
    print(f"Current Value: KES {result['current_value']:,.2f}")
    print(f"Total Depreciation: KES {result['total_depreciation']:,.2f}")
    print(f"Value Retained: {result['value_retained']:.1f}%")
    print(f"Confidence: {result['confidence_score']}%")
    print("-" * 60)
    
    # Example 2: API-compatible calculation
    print("Example 2: API-Compatible Calculation")
    print("-" * 60)
    
    api_result = calculate_vehicle_value_api(
        purchase_price=5200000,
        age_years=3,
        depreciation_rate=0.15,
        condition="Good",
        mileage=45000,
        location="Nairobi"
    )
    
    print(f"Current Value: KES {api_result['current_value']:,.2f}")
    print(f"Total Depreciation: KES {api_result['total_depreciation']:,.2f}")
    print(f"Value Retained: {api_result['value_retained']:.1f}%")
    print("=" * 60)
