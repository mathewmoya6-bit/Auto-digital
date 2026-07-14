"""
Mileage Service - Auto-D Kenya
API endpoints for mileage and running cost calculations
"""

from typing import Dict, Any, Optional
from flask import jsonify, request

from engines.running_cost_engine import RunningCostEngine


class MileageService:
    """Mileage and running cost service"""
    
    def __init__(self):
        self.engine = RunningCostEngine()
        
        # Default vehicle specifications for common selections
        self.VEHICLE_SPECS = {
            "1.6L Diesel - Standard": {
                "fuel_type": "diesel",
                "fuel_consumption": 6.5,  # L/100km
                "purchase_price": 1800000,  # KES
                "maintenance_per_km": 1.5,  # KES
                "tyre_size": "195/65R15",
                "insurance_annual": 45000,
                "tax_annual": 2400,
                "annual_km": 20000
            },
            "2.0L Petrol - Standard": {
                "fuel_type": "petrol",
                "fuel_consumption": 8.5,
                "purchase_price": 1500000,
                "maintenance_per_km": 1.8,
                "tyre_size": "205/55R16",
                "insurance_annual": 40000,
                "tax_annual": 2400,
                "annual_km": 20000
            }
            # Add more vehicle specifications as needed
        }
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate mileage cost"""
        distance_km = data.get("distance_km") or data.get("trip_distance")
        
        if not distance_km:
            return {"error": "distance_km is required"}, 400
        
        try:
            distance_km = float(distance_km)
            if distance_km <= 0:
                raise ValueError
        except ValueError:
            return {"error": "distance_km must be a positive number"}, 400
        
        # Get vehicle selection from UI
        fuel_type = data.get("fuel_type", "all")
        vehicle_category = data.get("vehicle_category", "")
        engine_class = data.get("engine_class", "1.6L Diesel - Standard")
        
        # Load vehicle specifications based on selection
        vehicle_specs = self.VEHICLE_SPECS.get(
            engine_class, 
            self.VEHICLE_SPECS["1.6L Diesel - Standard"]
        )
        
        # Allow overrides from request data
        vehicle_data = {
            "fuel_type": data.get("fuel_type", vehicle_specs["fuel_type"]),
            "fuel_consumption": data.get("fuel_consumption", vehicle_specs["fuel_consumption"]),
            "maintenance_per_km": data.get("maintenance_per_km", vehicle_specs["maintenance_per_km"]),
            "insurance_annual": data.get("insurance", vehicle_specs["insurance_annual"]),
            "tax_annual": data.get("tax", vehicle_specs["tax_annual"]),
            "annual_km": data.get("annual_km", vehicle_specs["annual_km"]),
            "purchase_price": data.get("purchase_price", vehicle_specs["purchase_price"]),
            "tyre_size": data.get("tyre_size", vehicle_specs["tyre_size"]),
            "vehicle_type": data.get("vehicle_type", "Car")
        }
        
        result = self.engine.calculate_trip_cost(
            distance_km=distance_km,
            vehicle_data=vehicle_data
        )
        
        # Calculate averages for display
        purchase_price = vehicle_data["purchase_price"]
        total_cost = result.summary["total_cost"]
        cost_per_km = result.summary["total_per_km"]
        
        # 5-year projection from engine results
        projection = result.projection if hasattr(result, 'projection') else {
            "year_1": total_cost,
            "year_2": total_cost * 1.08,
            "year_3": total_cost * 1.16,
            "year_4": total_cost * 1.25,
            "year_5": total_cost * 1.35
        }
        
        return {
            "success": True,
            "data": {
                # Summary section
                "total_cost": total_cost,
                "cost_per_km": cost_per_km,
                "distance_km": distance_km,
                
                # Cost breakdowns
                "fixed_cost_per_km": result.fixed_costs.get("total_per_km", 0),
                "operating_cost_per_km": result.operating_costs.get("total_per_km", 0),
                "fixed_cost_trip": result.fixed_costs.get("total", 0),
                "operating_cost_trip": result.operating_costs.get("total", 0),
                "total_running_cost_per_km": result.summary["total_per_km"],
                
                # Detailed cost breakdown
                "detailed_costs": {
                    "insurance": result.fixed_costs.get("insurance", 0),
                    "depreciation": result.fixed_costs.get("depreciation", 0),
                    "interest_on_capital": result.fixed_costs.get("interest", 0),
                    "fuel": result.operating_costs.get("energy", 0),
                    "servicing": result.operating_costs.get("servicing", 0),
                    "repairs_replacements": result.operating_costs.get("repairs", 0),
                    "automotive_tyres": result.operating_costs.get("tyres", 0),
                    "licences_parking": result.fixed_costs.get("tax", 0)
                },
                
                # Vehicle info
                "average_initial_cost": purchase_price,
                
                # 5-Year running cost progression
                "cost_projection": {
                    "new": projection.get("year_1", total_cost),
                    "year_2": projection.get("year_2", total_cost * 1.08),
                    "year_3": projection.get("year_3", total_cost * 1.16),
                    "year_4": projection.get("year_4", total_cost * 1.25),
                    "year_5": projection.get("year_5", total_cost * 1.35)
                },
                
                "recommendations": result.recommendations if hasattr(result, 'recommendations') else [],
                
                # Raw data for debugging
                "fixed_costs": result.fixed_costs,
                "operating_costs": result.operating_costs,
                "projection": projection
            }
        }
    
    def get_vehicle_options(self) -> Dict[str, Any]:
        """Get available vehicle options for the UI"""
        return {
            "fuel_types": ["All", "Petrol", "Diesel", "Gas/LPG", "Electric"],
            "vehicle_categories": [
                "Saloon Cars - Diesel",
                "Saloon Cars - Petrol",
                "SUV - Diesel",
                "SUV - Petrol",
                "Pickup - Diesel",
                "Minibus - Diesel"
            ],
            "engine_classes": list(self.VEHICLE_SPECS.keys()),
            "quick_routes": [
                {"name": "Nairobi → Mombasa", "distance": 485},
                {"name": "Nairobi → Kisumu", "distance": 355},
                {"name": "Nairobi → Nakuru", "distance": 160},
                {"name": "Nairobi → Eldoret", "distance": 315},
                {"name": "Nairobi → Malindi", "distance": 500},
                {"name": "Nairobi → Nanyuki", "distance": 210}
            ]
        }


# Flask route handlers (if using Flask)
def register_routes(app):
    """Register MileageService routes"""
    service = MileageService()
    
    @app.route('/api/mileage/calculate', methods=['POST'])
    def calculate_mileage():
        """Calculate mileage cost endpoint"""
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request data"}), 400
        result = service.calculate(data)
        return jsonify(result)
    
    @app.route('/api/mileage/options', methods=['GET'])
    def get_mileage_options():
        """Get available vehicle options"""
        return jsonify(service.get_vehicle_options())
