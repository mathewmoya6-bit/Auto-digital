"""
Mileage Service - Auto-D Kenya
API endpoints for mileage and running cost calculations
"""

import logging
from typing import Dict, Any, Optional
from flask import jsonify, request, Blueprint
from flask_cors import cross_origin
from data import find_variant

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class MileageError(ValueError):
    """Custom exception for mileage calculation errors"""
    pass


def calculate_mileage(variant_id: str, distance_km: float) -> dict:
    """
    Calculate mileage cost - aligned with frontend expectations
    
    Args:
        variant_id: Vehicle variant ID (e.g., 'v1', 'v2', etc.)
        distance_km: Distance in kilometers
    
    Returns:
        dict: Response matching frontend format with data wrapper
    
    Raises:
        MileageError: If validation fails
    """
    # ─── Validation ──────────────────────────────────────────────
    if not variant_id:
        raise MileageError("variant_id is required")
    
    try:
        distance_km = float(distance_km)
    except (TypeError, ValueError):
        raise MileageError("distance_km must be a number")
    
    if distance_km <= 0:
        raise MileageError("distance_km must be greater than 0")
    
    # ─── Get variant data ──────────────────────────────────────
    variant = find_variant(variant_id)
    if not variant:
        raise MileageError(f"Unknown variant_id: {variant_id}")
    
    logger.info(f"Calculating mileage for variant: {variant_id}, distance: {distance_km}km")
    
    # ─── Extract rates ──────────────────────────────────────────
    fixed_rate = float(variant.get("fixed_per_km", 0))
    operating_rate = float(variant.get("operating_per_km", 0))
    total_rate = float(variant.get("total_per_km", fixed_rate + operating_rate))
    
    # ─── Calculate costs ────────────────────────────────────────
    total_cost = round(total_rate * distance_km, 2)
    fixed_cost = round(fixed_rate * distance_km, 2)
    operating_cost = round(operating_rate * distance_km, 2)
    
    # ─── Components breakdown (per trip) ──────────────────────
    components = {}
    for k, v in variant.get("components", {}).items():
        try:
            components[k] = round(float(v) * distance_km, 2)
        except (TypeError, ValueError):
            components[k] = 0
    
    # ─── Yearly progression ────────────────────────────────────
    yearly = {}
    for i in range(1, 6):
        year_key = f"year{i}"
        yearly[year_key] = round(float(variant.get(year_key, total_rate)), 2)
    
    # ─── Return format matching frontend ──────────────────────
    return {
        "success": True,
        "data": {
            # Core results
            "totalCost": total_cost,
            "fixedCost": fixed_cost,
            "operatingCost": operating_cost,
            "totalRate": round(total_rate, 2),
            "fixedRate": round(fixed_rate, 2),
            "operatingRate": round(operating_rate, 2),
            
            # Vehicle info
            "variant_id": variant.get("id", variant_id),
            "label": variant.get("label", "Unknown"),
            "fuel_type": variant.get("fuel_type", "Unknown"),
            "distance_km": distance_km,
            
            # Detailed breakdown
            "components": components,
            "yearly": yearly,
            "initialCost": float(variant.get("initial_cost", 0)),
            
            # Metadata
            "method": "backend",
            "variant_data": variant  # Include for debugging/transparency
        }
    }


# ─── Flask Blueprint ─────────────────────────────────────────────

mileage_bp = Blueprint('mileage', __name__, url_prefix='/api/service')


@mileage_bp.route('/mileage', methods=['POST'])
@cross_origin()
def mileage_endpoint():
    """
    POST /api/service/mileage
    Calculate mileage rate for a vehicle variant
    
    Request body:
    {
        "variant_id": "v1",       # Required
        "distance_km": 100,       # Required
        "fuel_type": "Petrol",    # Optional (fallback)
        "fuel_consumption": 8,    # Optional (fallback)
        "maintenance_per_km": 2,  # Optional (fallback)
        "insurance": 5000,        # Optional (fallback)
        "tax": 2000               # Optional (fallback)
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
            "variant_id": "v1",
            "label": "1.5L Petrol - Standard",
            "fuel_type": "Petrol",
            "distance_km": 100,
            "components": {
                "Insurance": 250.00,
                "Depreciation": 500.00,
                ...
            },
            "yearly": {
                "year1": 28.50,
                "year2": 32.00,
                ...
            },
            "initialCost": 1500000,
            "method": "backend"
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
        # Support both 'variant_id' and 'id' for flexibility
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
        
        # ─── Call calculation function ────────────────────────
        result = calculate_mileage(variant_id, distance_km)
        
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
        from data import get_categories, get_variants
        
        return jsonify({
            "success": True,
            "data": {
                "categories": get_categories(),
                "variants": get_variants(),
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
        "version": "1.0.0",
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


# ─── Registration Function ────────────────────────────────────────

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
