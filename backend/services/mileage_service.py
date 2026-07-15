"""
Mileage Service - Auto-D Kenya
API endpoints for mileage and running cost calculations
"""

import logging
from typing import Dict, Any, Optional
from flask import jsonify, request, Blueprint
from flask_cors import cross_origin

from running_cost_engine import RunningCostEngine, RunningCostResult

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class MileageError(ValueError):
    """Custom exception for mileage calculation errors"""
    pass


class MileageService:
    """
    Mileage Service - Handles all mileage and running cost calculations.
    Wraps the RunningCostEngine and provides API-friendly methods.
    """
    
    def __init__(self):
        self.engine = RunningCostEngine()
        self.logger = logging.getLogger(__name__)
    
    def calculate_trip_cost(
        self,
        vehicle_data: Dict[str, Any],
        distance_km: float,
        trip_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate trip cost for a vehicle.
        
        Args:
            vehicle_data: Vehicle specifications (variant data)
            distance_km: Distance in kilometers
            trip_inputs: Optional trip parameters
        
        Returns:
            Dict formatted for API response
        """
        try:
            # Validate inputs
            self._validate_inputs(vehicle_data, distance_km)
            
            # Merge trip inputs with defaults
            trip_inputs = trip_inputs or {}
            trip_inputs.setdefault("annual_km", vehicle_data.get("annual_km", 20000))
            trip_inputs.setdefault("driving_style", "normal")
            trip_inputs.setdefault("trip_type", "mixed")
            trip_inputs.setdefault("usage_type", "private")
            trip_inputs.setdefault("year", vehicle_data.get("year", 2020))
            
            # Calculate using engine
            result = self.engine.calculate_trip_cost(
                distance_km=distance_km,
                vehicle_data=vehicle_data,
                trip_inputs=trip_inputs
            )
            
            # Convert to frontend format
            return result.to_frontend_format()
            
        except MileageError as e:
            self.logger.warning(f"Validation error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Calculation error: {e}", exc_info=True)
            raise
    
    def _validate_inputs(self, vehicle_data: Dict[str, Any], distance_km: float) -> None:
        """Validate calculation inputs"""
        if not vehicle_data:
            raise MileageError("vehicle_data is required")
        
        try:
            distance_km = float(distance_km)
        except (TypeError, ValueError):
            raise MileageError("distance_km must be a number")
        
        if distance_km <= 0:
            raise MileageError("distance_km must be greater than 0")
        
        if not vehicle_data.get("id") and not vehicle_data.get("label"):
            raise MileageError("vehicle_data must contain 'id' or 'label'")


# ─── Flask Blueprint ─────────────────────────────────────────────

mileage_bp = Blueprint('mileage', __name__, url_prefix='/api/service')
service = MileageService()


@mileage_bp.route('/mileage', methods=['POST'])
@cross_origin()
def mileage_endpoint():
    """
    POST /api/service/mileage
    Calculate mileage rate for a vehicle variant
    
    Request body:
    {
        "variant_id": "v1",           # Required - vehicle ID
        "distance_km": 100,           # Required - distance in km
        "fuel_type": "Petrol",        # Optional
        "fuel_consumption": 8,        # Optional
        "maintenance_per_km": 2,      # Optional
        "insurance": 5000,            # Optional
        "tax": 2000,                  # Optional
        "driving_style": "normal",    # Optional - eco, normal, aggressive
        "trip_type": "mixed",         # Optional - city, highway, mixed
        "usage_type": "private",      # Optional - private, commercial_passenger, commercial_freight, fleet, taxi
        "year": 2020                  # Optional - vehicle year
    }
    
    Response:
    {
        "success": true,
        "data": {
            "totalCost": 3125.00,
            "fixedCost": 1250.00,
            "operatingCost": 1875.00,
            "totalRate": 31.25,
            "fixedRate": 12.50,
            "operatingRate": 18.75,
            "distance_km": 100,
            "components": {
                "Fuel": 875.00,
                "Oil": 60.00,
                "Tyres": 240.00,
                "Service": 225.00,
                "Repairs": 80.00,
                "Insurance": 250.00,
                "Depreciation": 500.00,
                "Financing": 300.00,
                "Fees": 100.00,
                "Battery Reserve": 0
            },
            "perKmComponents": {
                "Fuel": 8.75,
                "Oil": 0.60,
                "Tyres": 2.40,
                "Service": 2.25,
                "Repairs": 0.80,
                "Insurance": 2.50,
                "Depreciation": 5.00,
                "Financing": 3.00,
                "Fees": 1.00
            },
            "yearly": {
                "year1": 28.50,
                "year2": 32.00,
                "year3": 36.00,
                "year4": 41.00,
                "year5": 47.00
            },
            "privateCost": 31.25,
            "fleetCost": 34.25,
            "taxiRate": 42.19,
            "recommendedRate": 37.50,
            "deliveryPerParcel": 585.94,
            "initialCost": 1500000,
            "currentValue": 1200000,
            "rci": 31.25,
            "rciLabel": "Good",
            "rciStars": "★★★★",
            "rciClass": "good",
            "healthScore": 85,
            "healthLabel": "★★★★ Good",
            "monthlyTotal": 5208.33,
            "annualTotal": 62500.00,
            "co2PerKm": 0.18,
            "co2Trip": 18.48,
            "co2Annual": 3696.00,
            "treesToOffset": 184.80,
            "fuelType": "petrol",
            "fuelConsumption": 12.5,
            "fuelPricePerUnit": 189.00,
            "vehicleName": "1.5L Petrol - Standard",
            "fuelTypeDisplay": "Petrol",
            "recommendations": [...],
            "method": "backend",
            "version": "4.0",
            "timestamp": "2026-07-15T10:30:00.000Z"
        }
    }
    """
    try:
        # ─── Get request data ──────────────────────────────────
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "Invalid request",
                "message": "JSON data required"
            }), 400
        
        logger.info(f"Received mileage request: {data}")
        
        # ─── Extract parameters ──────────────────────────────
        variant_id = data.get('variant_id') or data.get('id')
        distance_km = data.get('distance_km')
        
        # ─── Validate required fields ────────────────────────
        if not variant_id:
            return jsonify({
                "success": False,
                "error": "Missing parameter",
                "message": "variant_id is required"
            }), 400
        
        if distance_km is None:
            return jsonify({
                "success": False,
                "error": "Missing parameter",
                "message": "distance_km is required"
            }), 400
        
        # ─── Get variant data ──────────────────────────────────
        # Import data module to get variant
        try:
            from data import find_variant
            variant = find_variant(variant_id)
        except ImportError:
            # Fallback - try to use data from request
            variant = {
                "id": variant_id,
                "label": data.get("label", "Unknown"),
                "fuel_type": data.get("fuel_type", "petrol"),
                "fuel_consumption": data.get("fuel_consumption", 8.0),
                "initial_cost": data.get("initial_cost", 0),
                "current_value": data.get("current_value", 0),
                "insurance_annual": data.get("insurance", 60000),
                "tax_annual": data.get("tax", 8000),
                "tyre_cost": data.get("tyre_cost", 120000),
                "tyre_life": data.get("tyre_life", 50000),
                "year": data.get("year", 2020),
                "annual_km": data.get("annual_km", 20000)
            }
            logger.warning(f"Using fallback variant data: {variant}")
        
        if not variant:
            return jsonify({
                "success": False,
                "error": "Invalid variant",
                "message": f"Unknown variant_id: {variant_id}"
            }), 404
        
        # ─── Build vehicle data ──────────────────────────────
        vehicle_data = {
            "id": variant.get("id", variant_id),
            "label": variant.get("label", "Unknown"),
            "fuel_type": variant.get("fuel_type", "petrol"),
            "fuel_consumption": float(variant.get("fuel_consumption", 8.0)),
            "initial_cost": float(variant.get("initial_cost", 0)),
            "current_value": float(variant.get("current_value", 0)),
            "insurance_annual": float(variant.get("insurance_annual", 60000)),
            "tax_annual": float(variant.get("tax_annual", 8000)),
            "tyre_cost": float(variant.get("tyre_cost", 120000)),
            "tyre_life": float(variant.get("tyre_life", 50000)),
            "oil_interval": float(variant.get("oil_interval", 10000)),
            "oil_cost": float(variant.get("oil_cost", 6000)),
            "minor_service_interval": float(variant.get("minor_service_interval", 10000)),
            "minor_service_cost": float(variant.get("minor_service_cost", 15000)),
            "major_service_interval": float(variant.get("major_service_interval", 40000)),
            "major_service_cost": float(variant.get("major_service_cost", 45000)),
            "expected_resale": float(variant.get("expected_resale", 0)),
            "years_remaining": float(variant.get("years_remaining", 8)),
            "loan_amount": float(variant.get("loan_amount", 0)),
            "battery_cost": float(variant.get("battery_cost", 0)),
            "battery_life": float(variant.get("battery_life", 0)),
            "condition": variant.get("condition", "Good"),
            "distance_km": float(distance_km)
        }
        
        # ─── Build trip inputs ────────────────────────────────
        trip_inputs = {
            "annual_km": float(data.get("annual_km", vehicle_data.get("annual_km", 20000))),
            "driving_style": data.get("driving_style", "normal"),
            "trip_type": data.get("trip_type", "mixed"),
            "usage_type": data.get("usage_type", "private"),
            "year": int(data.get("year", variant.get("year", 2020))),
            "fuel_price": float(data.get("fuel_price", 0)) if data.get("fuel_price") else None
        }
        
        # ─── Calculate ─────────────────────────────────────────
        result = service.calculate_trip_cost(
            vehicle_data=vehicle_data,
            distance_km=float(distance_km),
            trip_inputs=trip_inputs
        )
        
        return jsonify(result), 200
        
    except MileageError as e:
        logger.warning(f"Mileage error: {e}")
        return jsonify({
            "success": False,
            "error": "Validation error",
            "message": str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Unexpected error in mileage endpoint: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later."
        }), 500


@mileage_bp.route('/mileage/options', methods=['GET'])
@cross_origin()
def get_mileage_options():
    """
    GET /api/service/mileage/options
    Get available vehicle categories and variants
    """
    try:
        # Import data module to get categories and variants
        try:
            from data import get_categories, get_variants
            categories = get_categories()
            variants = get_variants()
        except ImportError:
            # Fallback data
            categories = [
                {"id": "cat1", "name": "Saloon Cars - Petrol", "fuel_type": "Petrol"},
                {"id": "cat2", "name": "Saloon Cars - Diesel", "fuel_type": "Diesel"},
                {"id": "cat3", "name": "SUVs & Crossovers", "fuel_type": "Diesel"},
                {"id": "cat4", "name": "Pickups & Vans", "fuel_type": "Diesel"},
                {"id": "cat5", "name": "Electric Vehicles", "fuel_type": "Electric"},
                {"id": "cat6", "name": "Motorcycles", "fuel_type": "Petrol"},
                {"id": "cat7", "name": "LPG / Gas Vehicles", "fuel_type": "LPG"}
            ]
            variants = {}
            logger.warning("Using fallback category data")
        
        return jsonify({
            "success": True,
            "data": {
                "categories": categories,
                "variants": variants,
                "routes": [
                    {"from_city": "Nairobi", "to_city": "Mombasa", "km": 485},
                    {"from_city": "Nairobi", "to_city": "Kisumu", "km": 355},
                    {"from_city": "Nairobi", "to_city": "Nakuru", "km": 160},
                    {"from_city": "Nairobi", "to_city": "Eldoret", "km": 315},
                    {"from_city": "Nairobi", "to_city": "Malindi", "km": 500},
                    {"from_city": "Nairobi", "to_city": "Nanyuki", "km": 210}
                ]
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting options: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Failed to load options",
            "message": str(e)
        }), 500


@mileage_bp.route('/mileage/health', methods=['GET'])
@cross_origin()
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Mileage Service - Auto-D Kenya",
        "version": "4.0",
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    }), 200


# ─── Error Handlers ──────────────────────────────────────────────

@mileage_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "success": False,
        "error": "Not found",
        "message": "The requested endpoint does not exist"
    }), 404


@mileage_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500


# ─── Registration Functions ────────────────────────────────────────

def register_routes(app):
    """Register mileage routes with the Flask app"""
    app.register_blueprint(mileage_bp)
    logger.info("✅ Mileage Service routes registered at /api/service/mileage")


def init_app(app):
    """Initialize the mileage service with the Flask app"""
    from flask_cors import CORS
    
    # Enable CORS for all routes
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"]
        }
    })
    
    register_routes(app)
    logger.info("✅ Mileage Service initialized successfully")


# ─── Standalone Test ─────────────────────────────────────────────

if __name__ == "__main__":
    # Test the service
    service = MileageService()
    
    test_vehicle = {
        "id": "v1",
        "label": "1.5L Petrol - Standard",
        "fuel_type": "petrol",
        "fuel_consumption": 12.5,
        "initial_cost": 1500000,
        "current_value": 1200000,
        "insurance_annual": 60000,
        "tax_annual": 8000,
        "tyre_cost": 80000,
        "tyre_life": 50000,
        "oil_interval": 10000,
        "oil_cost": 6000,
        "minor_service_interval": 10000,
        "minor_service_cost": 15000,
        "major_service_interval": 40000,
        "major_service_cost": 45000,
        "expected_resale": 600000,
        "years_remaining": 8,
        "loan_amount": 1200000,
        "condition": "Good"
    }
    
    result = service.calculate_trip_cost(
        vehicle_data=test_vehicle,
        distance_km=150,
        trip_inputs={
            "annual_km": 20000,
            "driving_style": "normal",
            "trip_type": "mixed",
            "usage_type": "private",
            "year": 2020
        }
    )
    
    print("=" * 60)
    print("Test Result:")
    print("=" * 60)
    print(f"Total Cost: KES {result['data']['totalCost']}")
    print(f"Total Rate: KES {result['data']['totalRate']}/km")
    print(f"RCI: {result['data']['rciLabel']} ({result['data']['rci']})")
    print(f"Health Score: {result['data']['healthScore']}/100")
    print("\nComponents:")
    for key, value in result['data']['components'].items():
        print(f"  {key}: KES {value}")
    print("\nPer km:")
    for key, value in result['data']['perKmComponents'].items():
        print(f"  {key}: KES {value}")
