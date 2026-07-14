"""
Valuation Service - Auto-D Kenya
API endpoints for vehicle valuation
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from flask import jsonify, request, Blueprint
from flask_cors import cross_origin

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ValuationService:
    """Vehicle valuation service"""
    
    def __init__(self):
        try:
            from engines.valuation_engine import ValuationEngine
            self.engine = ValuationEngine()
            logger.info("ValuationEngine initialized successfully")
        except ImportError as e:
            logger.error(f"Failed to import ValuationEngine: {e}")
            self.engine = None
        except Exception as e:
            logger.error(f"Error initializing ValuationEngine: {e}")
            self.engine = None
        
        # Vehicle depreciation rates by type
        self.DEPRECIATION_RATES = {
            "Car": {"year_1": 0.20, "year_2": 0.15, "year_3": 0.12, "year_4": 0.10, "year_5": 0.08},
            "SUV": {"year_1": 0.18, "year_2": 0.13, "year_3": 0.11, "year_4": 0.09, "year_5": 0.07},
            "Pickup": {"year_1": 0.15, "year_2": 0.12, "year_3": 0.10, "year_4": 0.08, "year_5": 0.06},
            "Minibus": {"year_1": 0.16, "year_2": 0.13, "year_3": 0.10, "year_4": 0.08, "year_5": 0.06},
            "Motorcycle": {"year_1": 0.12, "year_2": 0.10, "year_3": 0.08, "year_4": 0.06, "year_5": 0.05}
        }
        
        # Condition multipliers
        self.CONDITION_MULTIPLIERS = {
            "Excellent": 1.15,
            "Very Good": 1.05,
            "Good": 1.00,
            "Fair": 0.85,
            "Poor": 0.70
        }
        
        # Location adjustments (relative to Nairobi)
        self.LOCATION_ADJUSTMENTS = {
            "Nairobi": 1.00,
            "Mombasa": 0.95,
            "Kisumu": 0.93,
            "Nakuru": 0.94,
            "Eldoret": 0.92,
            "Malindi": 0.91,
            "Nanyuki": 0.90,
            "Other": 0.88
        }
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate vehicle valuation
        
        Expected data:
            - purchase_price: float (required)
            - age_years: float (required)
            - make: str (optional)
            - model: str (optional)
            - vehicle_type: str (optional, default: "Car")
            - condition: str (optional, default: "Good")
            - mileage: float (optional, default: 0)
            - location: str (optional, default: "Nairobi")
            - accident_history: str (optional, default: "None")
            - previous_owners: int (optional, default: 0)
        """
        try:
            logger.info(f"Calculating valuation with data: {data}")
            
            # Validate required fields
            purchase_price = data.get("purchase_price")
            age_years = data.get("age_years")
            
            if purchase_price is None:
                return {
                    "success": False,
                    "error": "purchase_price is required",
                    "message": "Please provide the vehicle's purchase price"
                }
            
            if age_years is None:
                return {
                    "success": False,
                    "error": "age_years is required",
                    "message": "Please provide the vehicle's age in years"
                }
            
            # Validate data types and values
            try:
                purchase_price = float(purchase_price)
                age_years = float(age_years)
                if purchase_price <= 0:
                    return {
                        "success": False,
                        "error": "Invalid purchase price",
                        "message": "purchase_price must be a positive number"
                    }
                if age_years < 0:
                    return {
                        "success": False,
                        "error": "Invalid age",
                        "message": "age_years cannot be negative"
                    }
            except ValueError:
                return {
                    "success": False,
                    "error": "Invalid input",
                    "message": "purchase_price and age_years must be valid numbers"
                }
            
            # Get optional parameters with defaults
            vehicle_type = data.get("vehicle_type", "Car")
            condition = data.get("condition", "Good")
            mileage = float(data.get("mileage", 0))
            location = data.get("location", "Nairobi")
            make = data.get("make", "Unknown")
            model = data.get("model", "Unknown")
            accident_history = data.get("accident_history", "None")
            previous_owners = int(data.get("previous_owners", 0))
            
            # Calculate current year
            current_year = datetime.now().year
            year = current_year - int(age_years)
            
            # If engine is available, use it
            if self.engine:
                try:
                    result = self.engine.calculate_value(
                        purchase_price=purchase_price,
                        year=year,
                        make=make,
                        model=model,
                        vehicle_type=vehicle_type,
                        condition=condition,
                        mileage=mileage,
                        location=location,
                        accident_history=accident_history,
                        previous_owners=previous_owners
                    )
                    
                    # Extract results
                    current_value = getattr(result, 'current_value', 0)
                    market_value = getattr(result, 'market_value', 0)
                    estimated_value = getattr(result, 'estimated_value', 0)
                    trade_in_value = getattr(result, 'trade_in_value', 0)
                    retail_value = getattr(result, 'retail_value', 0)
                    confidence_score = getattr(result, 'confidence_score', 0.85)
                    valuation_range = getattr(result, 'valuation_range', {})
                    recommendations = getattr(result, 'recommendations', [])
                    market_adjustments = getattr(result, 'market_adjustments', {})
                    
                    # Calculate depreciation
                    depreciation = getattr(result, 'depreciation', {})
                    total_depreciation = depreciation.get("total_depreciation", purchase_price - current_value)
                    value_retained = depreciation.get("value_retained", (current_value / purchase_price * 100) if purchase_price > 0 else 0)
                    
                except Exception as e:
                    logger.error(f"Engine valuation error: {e}")
                    # Fallback to manual calculation
                    current_value, total_depreciation, value_retained = self._manual_valuation(
                        purchase_price, age_years, vehicle_type, condition, mileage, location
                    )
                    market_value = current_value
                    estimated_value = current_value
                    trade_in_value = current_value * 0.85
                    retail_value = current_value * 1.15
                    confidence_score = 0.80
                    valuation_range = {
                        "min": current_value * 0.85,
                        "max": current_value * 1.15
                    }
                    recommendations = self._generate_recommendations(purchase_price, current_value, condition)
                    market_adjustments = {}
            else:
                # Manual calculation
                current_value, total_depreciation, value_retained = self._manual_valuation(
                    purchase_price, age_years, vehicle_type, condition, mileage, location
                )
                market_value = current_value
                estimated_value = current_value
                trade_in_value = current_value * 0.85
                retail_value = current_value * 1.15
                confidence_score = 0.80
                valuation_range = {
                    "min": round(current_value * 0.85, 2),
                    "max": round(current_value * 1.15, 2)
                }
                recommendations = self._generate_recommendations(purchase_price, current_value, condition)
                market_adjustments = {}
            
            # Format response
            return {
                "success": True,
                "data": {
                    "current_value": round(current_value, 2),
                    "market_value": round(market_value, 2),
                    "estimated_value": round(estimated_value, 2),
                    "trade_in_value": round(trade_in_value, 2),
                    "retail_value": round(retail_value, 2),
                    "total_depreciation": round(total_depreciation, 2),
                    "value_retained": round(value_retained, 2),
                    "confidence_score": round(confidence_score, 2),
                    "valuation_range": {
                        "min": round(valuation_range.get("min", current_value * 0.85), 2),
                        "max": round(valuation_range.get("max", current_value * 1.15), 2)
                    },
                    "recommendations": recommendations,
                    "market_adjustments": market_adjustments,
                    "vehicle_details": {
                        "make": make,
                        "model": model,
                        "year": year,
                        "vehicle_type": vehicle_type,
                        "condition": condition,
                        "mileage": round(mileage, 0),
                        "location": location,
                        "accident_history": accident_history,
                        "previous_owners": previous_owners,
                        "purchase_price": round(purchase_price, 2)
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Valuation calculation error: {e}", exc_info=True)
            return {
                "success": False,
                "error": "Valuation failed",
                "message": str(e)
            }
    
    def _manual_valuation(self, purchase_price: float, age_years: float, 
                         vehicle_type: str, condition: str, mileage: float, 
                         location: str) -> tuple:
        """Manual valuation calculation fallback"""
        # Get depreciation rates for vehicle type
        rates = self.DEPRECIATION_RATES.get(vehicle_type, self.DEPRECIATION_RATES["Car"])
        
        # Calculate depreciation based on age
        current_value = purchase_price
        remaining_years = age_years
        
        # Apply yearly depreciation
        year = 1
        while remaining_years > 0 and year <= 5:
            rate = rates.get(f"year_{year}", 0.08)
            current_value *= (1 - rate)
            remaining_years -= 1
            year += 1
        
        # Apply additional depreciation for years beyond 5
        if remaining_years > 0:
            current_value *= (0.92 ** remaining_years)
        
        # Apply condition adjustment
        condition_multiplier = self.CONDITION_MULTIPLIERS.get(condition, 1.0)
        current_value *= condition_multiplier
        
        # Apply mileage adjustment (standard: 15,000 km/year)
        expected_mileage = age_years * 15000
        mileage_ratio = mileage / expected_mileage if expected_mileage > 0 else 1
        if mileage_ratio > 1.5:
            current_value *= 0.90
        elif mileage_ratio > 1.2:
            current_value *= 0.95
        
        # Apply location adjustment
        location_multiplier = self.LOCATION_ADJUSTMENTS.get(location, 0.88)
        current_value *= location_multiplier
        
        # Ensure value doesn't go below 10% of purchase price
        current_value = max(current_value, purchase_price * 0.10)
        
        total_depreciation = purchase_price - current_value
        value_retained = (current_value / purchase_price * 100) if purchase_price > 0 else 0
        
        return current_value, total_depreciation, value_retained
    
    def _generate_recommendations(self, purchase_price: float, current_value: float, 
                                 condition: str) -> list:
        """Generate recommendations based on valuation"""
        recommendations = []
        
        # Value retention analysis
        value_retained = (current_value / purchase_price * 100) if purchase_price > 0 else 0
        
        if value_retained > 70:
            recommendations.append("✅ Your vehicle has excellent value retention")
        elif value_retained > 50:
            recommendations.append("📈 Your vehicle has good value retention")
        else:
            recommendations.append("📉 Consider selling before further depreciation")
        
        # Condition based recommendations
        if condition == "Excellent" or condition == "Very Good":
            recommendations.append("🏆 Your vehicle is in great condition - this positively impacts value")
        elif condition == "Fair" or condition == "Poor":
            recommendations.append("🔧 Consider maintenance to improve vehicle condition and value")
        
        # General recommendations
        if current_value < 500000:
            recommendations.append("💰 Consider keeping the vehicle long-term as depreciation is minimal")
        elif current_value < 1000000:
            recommendations.append("📊 This is a good time to consider selling if planning to upgrade")
        else:
            recommendations.append("📈 Your vehicle maintains significant value - consider proper insurance coverage")
        
        return recommendations


# Create Blueprint for valuation routes
valuation_bp = Blueprint('valuation', __name__, url_prefix='/api/valuation')


@valuation_bp.route('/calculate', methods=['POST'])
@cross_origin()
def calculate_valuation():
    """Calculate vehicle valuation endpoint"""
    service = ValuationService()
    
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "Invalid request",
                "message": "JSON data required"
            }), 400
        
        # Validate required fields
        required_fields = ["purchase_price", "age_years"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "success": False,
                "error": "Missing required fields",
                "message": f"Required fields: {', '.join(missing_fields)}"
            }), 400
        
        result = service.calculate(data)
        
        if not result.get("success"):
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Route error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


@valuation_bp.route('/options', methods=['GET'])
@cross_origin()
def get_valuation_options():
    """Get available valuation options"""
    return jsonify({
        "success": True,
        "data": {
            "vehicle_types": ["Car", "SUV", "Pickup", "Minibus", "Motorcycle"],
            "conditions": ["Excellent", "Very Good", "Good", "Fair", "Poor"],
            "locations": ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Malindi", "Nanyuki", "Other"],
            "accident_history": ["None", "Minor", "Major", "Total Loss"]
        }
    }), 200


@valuation_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Valuation Service - Auto-D Kenya",
        "version": "1.0.0"
    }), 200


# Error handlers
@valuation_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "success": False,
        "error": "Not found",
        "message": "The requested endpoint does not exist"
    }), 404


@valuation_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500


def register_routes(app):
    """Register ValuationService routes with CORS"""
    from flask_cors import CORS
    
    # Enable CORS for all routes
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    app.register_blueprint(valuation_bp)
    logger.info("Valuation Service routes registered")


def init_app(app):
    """Initialize the valuation service with the Flask app"""
    register_routes(app)
    logger.info("Valuation Service initialized successfully")
