"""
Mileage Service - Auto-D Kenya
API endpoints for mileage and running cost calculations
"""

import logging
from typing import Dict, Any, Optional
from flask import jsonify, request, Blueprint
from flask_cors import cross_origin
from datetime import datetime

# ─── Import RunningCostEngine ──────────────────────────────────────
try:
    from engines.running_cost_engine import RunningCostEngine, RunningCostResult
    ENGINE_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ RunningCostEngine imported successfully")
except ImportError as e:
    ENGINE_AVAILABLE = False
    logging.getLogger(__name__).warning(f"⚠️ RunningCostEngine import failed: {e}")
    RunningCostEngine = None
    RunningCostResult = None

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
    
    def __init__(self, engine=None):
        self.engine = engine or (RunningCostEngine() if ENGINE_AVAILABLE else None)
        self.logger = logging.getLogger(__name__)
        
        if self.engine:
            self.logger.info("✅ RunningCostEngine initialized in MileageService")
        else:
            self.logger.warning("⚠️ RunningCostEngine not available - using simple calculations")
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main calculate method - called by app.py
        
        Args:
            data: Request data with variant_id, distance_km, etc.
        
        Returns:
            Dict with calculation results
        """
        try:
            # Extract parameters
            variant_id = data.get('variant_id') or data.get('id')
            distance_km = data.get('distance_km')
            
            if not variant_id:
                return {"error": "variant_id is required"}
            
            if distance_km is None:
                return {"error": "distance_km is required"}
            
            try:
                distance_km = float(distance_km)
                if distance_km <= 0:
                    return {"error": "distance_km must be greater than 0"}
            except (TypeError, ValueError):
                return {"error": "distance_km must be a number"}
            
            # Get variant data
            variant = self._get_variant(variant_id, data)
            if not variant:
                return {"error": f"Unknown variant_id: {variant_id}"}
            
            # Build vehicle data
            vehicle_data = self._build_vehicle_data(variant, data)
            
            # Build trip inputs
            trip_inputs = self._build_trip_inputs(data, variant)
            
            # Calculate using engine
            result = self.calculate_trip_cost(
                vehicle_data=vehicle_data,
                distance_km=float(distance_km),
                trip_inputs=trip_inputs
            )
            
            return result
            
        except MileageError as e:
            self.logger.warning(f"Mileage error: {e}")
            return {"error": str(e)}
        except Exception as e:
            self.logger.error(f"Calculation error: {e}", exc_info=True)
            return {"error": f"Calculation failed: {str(e)}"}
    
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
            
            # Calculate using engine if available
            if self.engine and hasattr(self.engine, 'calculate_trip_cost'):
                result = self.engine.calculate_trip_cost(
                    distance_km=distance_km,
                    vehicle_data=vehicle_data,
                    trip_inputs=trip_inputs
                )
                
                # If result is a RunningCostResult, convert to dict
                if hasattr(result, 'to_frontend_format'):
                    return result.to_frontend_format()
                elif isinstance(result, dict):
                    return result
                else:
                    return {"data": result, "success": True}
            
            # Fallback to simple calculation
            return self._calculate_simple(vehicle_data, distance_km, trip_inputs)
            
        except MileageError as e:
            self.logger.warning(f"Validation error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Calculation error: {e}", exc_info=True)
            raise
    
    def _get_variant(self, variant_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get variant data from data module or fallback"""
        try:
            # Try to import data module
            from data import find_variant
            variant = find_variant(variant_id)
            if variant:
                return variant
        except ImportError:
            self.logger.warning("data module not available, using fallback")
        
        # Fallback - use data from request
        return {
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
            "annual_km": data.get("annual_km", 20000),
            "oil_interval": data.get("oil_interval", 10000),
            "oil_cost": data.get("oil_cost", 6000),
            "minor_service_interval": data.get("minor_service_interval", 10000),
            "minor_service_cost": data.get("minor_service_cost", 15000),
            "major_service_interval": data.get("major_service_interval", 40000),
            "major_service_cost": data.get("major_service_cost", 45000),
            "expected_resale": data.get("expected_resale", 0),
            "years_remaining": data.get("years_remaining", 8),
            "loan_amount": data.get("loan_amount", 0),
            "battery_cost": data.get("battery_cost", 0),
            "battery_life": data.get("battery_life", 0),
            "condition": data.get("condition", "Good")
        }
    
    def _build_vehicle_data(self, variant: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Build vehicle data dict from variant"""
        return {
            "id": variant.get("id", data.get("variant_id")),
            "label": variant.get("label", "Unknown"),
            "fuel_type": variant.get("fuel_type", data.get("fuel_type", "petrol")),
            "fuel_consumption": float(variant.get("fuel_consumption", data.get("fuel_consumption", 8.0))),
            "initial_cost": float(variant.get("initial_cost", data.get("initial_cost", 0))),
            "current_value": float(variant.get("current_value", data.get("current_value", 0))),
            "insurance_annual": float(variant.get("insurance_annual", data.get("insurance", 60000))),
            "tax_annual": float(variant.get("tax_annual", data.get("tax", 8000))),
            "tyre_cost": float(variant.get("tyre_cost", data.get("tyre_cost", 120000))),
            "tyre_life": float(variant.get("tyre_life", data.get("tyre_life", 50000))),
            "oil_interval": float(variant.get("oil_interval", data.get("oil_interval", 10000))),
            "oil_cost": float(variant.get("oil_cost", data.get("oil_cost", 6000))),
            "minor_service_interval": float(variant.get("minor_service_interval", data.get("minor_service_interval", 10000))),
            "minor_service_cost": float(variant.get("minor_service_cost", data.get("minor_service_cost", 15000))),
            "major_service_interval": float(variant.get("major_service_interval", data.get("major_service_interval", 40000))),
            "major_service_cost": float(variant.get("major_service_cost", data.get("major_service_cost", 45000))),
            "expected_resale": float(variant.get("expected_resale", data.get("expected_resale", 0))),
            "years_remaining": float(variant.get("years_remaining", data.get("years_remaining", 8))),
            "loan_amount": float(variant.get("loan_amount", data.get("loan_amount", 0))),
            "battery_cost": float(variant.get("battery_cost", data.get("battery_cost", 0))),
            "battery_life": float(variant.get("battery_life", data.get("battery_life", 0))),
            "condition": variant.get("condition", data.get("condition", "Good")),
            "annual_km": float(variant.get("annual_km", data.get("annual_km", 20000))),
            "year": int(variant.get("year", data.get("year", 2020))),
            "distance_km": float(data.get("distance_km", 0))
        }
    
    def _build_trip_inputs(self, data: Dict[str, Any], variant: Dict[str, Any]) -> Dict[str, Any]:
        """Build trip inputs from request data"""
        return {
            "annual_km": float(data.get("annual_km", variant.get("annual_km", 20000))),
            "driving_style": data.get("driving_style", "normal"),
            "trip_type": data.get("trip_type", "mixed"),
            "usage_type": data.get("usage_type", "private"),
            "year": int(data.get("year", variant.get("year", 2020))),
            "fuel_price": float(data.get("fuel_price", 0)) if data.get("fuel_price") else None
        }
    
    def _calculate_simple(
        self,
        vehicle_data: Dict[str, Any],
        distance_km: float,
        trip_inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simple fallback calculation when engine is not available"""
        fuel_type = vehicle_data.get("fuel_type", "petrol")
        fuel_consumption = float(vehicle_data.get("fuel_consumption", 8.0))
        fuel_price = trip_inputs.get("fuel_price", 189.00)
        
        # Calculate fuel cost
        fuel_used = (distance_km / 100) * fuel_consumption
        fuel_cost = fuel_used * fuel_price
        
        # Simple fixed and operating costs
        fixed_cost = distance_km * 5.0  # Placeholder
        operating_cost = fuel_cost + distance_km * 2.0  # Placeholder
        total_cost = fixed_cost + operating_cost
        total_rate = total_cost / distance_km if distance_km > 0 else 0
        
        return {
            "success": True,
            "data": {
                "totalCost": round(total_cost, 2),
                "fixedCost": round(fixed_cost, 2),
                "operatingCost": round(operating_cost, 2),
                "totalRate": round(total_rate, 2),
                "fixedRate": round(fixed_cost / distance_km if distance_km > 0 else 0, 2),
                "operatingRate": round(operating_cost / distance_km if distance_km > 0 else 0, 2),
                "distance_km": distance_km,
                "components": {
                    "Fuel": round(fuel_cost, 2),
                    "Oil": 0,
                    "Tyres": 0,
                    "Service": 0,
                    "Repairs": 0,
                    "Insurance": 0,
                    "Depreciation": 0,
                    "Financing": 0,
                    "Fees": 0,
                    "Battery Reserve": 0
                },
                "perKmComponents": {
                    "Fuel": round(fuel_cost / distance_km if distance_km > 0 else 0, 2),
                    "Oil": 0,
                    "Tyres": 0,
                    "Service": 0,
                    "Repairs": 0,
                    "Insurance": 0,
                    "Depreciation": 0,
                    "Financing": 0,
                    "Fees": 0
                },
                "privateCost": round(total_rate, 2),
                "fleetCost": round(total_rate + 2.5, 2),
                "taxiRate": round(total_rate * 1.35, 2),
                "recommendedRate": round(total_rate * 1.20, 2),
                "deliveryPerParcel": round(total_rate * 18.75, 2),
                "initialCost": float(vehicle_data.get("initial_cost", 0)),
                "currentValue": float(vehicle_data.get("current_value", 0)),
                "rci": round(total_rate, 2),
                "rciLabel": "Good",
                "rciStars": "★★★★",
                "rciClass": "good",
                "healthScore": 75,
                "healthLabel": "★★★★ Good",
                "monthlyTotal": round(total_cost * 20000 / distance_km / 12 if distance_km > 0 else 0, 2),
                "annualTotal": round(total_cost * 20000 / distance_km if distance_km > 0 else 0, 2),
                "co2PerKm": round((fuel_consumption / 100) * 2.31, 2),
                "co2Trip": round(fuel_used * 2.31, 2),
                "co2Annual": round((fuel_used * 2.31) * (20000 / distance_km) if distance_km > 0 else 0, 2),
                "treesToOffset": 0,
                "fuelType": fuel_type,
                "fuelConsumption": fuel_consumption,
                "fuelPricePerUnit": fuel_price,
                "vehicleName": vehicle_data.get("label", "Unknown"),
                "fuelTypeDisplay": fuel_type.capitalize(),
                "recommendations": [],
                "method": "simple",
                "version": "4.0",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    
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
        
        # ─── Calculate using service ──────────────────────────
        result = service.calculate(data)
        
        if "error" in result:
            return jsonify({
                "success": False,
                "error": result["error"],
                "message": result["error"]
            }), 400
        
        # Ensure result has success flag
        if "success" not in result:
            result["success"] = True
        
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
        "engine_available": ENGINE_AVAILABLE,
        "timestamp": datetime.utcnow().isoformat()
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
    
    if "data" in result:
        data = result["data"]
        print(f"Total Cost: KES {data.get('totalCost', 0)}")
        print(f"Total Rate: KES {data.get('totalRate', 0)}/km")
        print(f"RCI: {data.get('rciLabel', 'N/A')} ({data.get('rci', 0)})")
        print(f"Health Score: {data.get('healthScore', 0)}/100")
        print("\nComponents:")
        for key, value in data.get('components', {}).items():
            print(f"  {key}: KES {value}")
        print("\nPer km:")
        for key, value in data.get('perKmComponents', {}).items():
            print(f"  {key}: KES {value}")
    else:
        print("Error:", result)
