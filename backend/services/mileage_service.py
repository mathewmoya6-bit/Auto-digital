"""
Mileage Service - Auto-D Kenya
API endpoints for mileage and running cost calculations
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class MileageService:
    """Mileage and running cost service"""
    
    def __init__(self):
        self.engine = None
        try:
            from engines.running_cost_engine import RunningCostEngine
            self.engine = RunningCostEngine()
            logger.info("✅ RunningCostEngine initialized successfully")
        except ImportError as e:
            logger.warning(f"⚠️ RunningCostEngine not available: {e}")
            self.engine = None
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate mileage cost
        
        Args:
            data: Request data with vehicle and trip parameters
            
        Returns:
            Dict with calculation results or error
        """
        # ─── Validate input ──────────────────────────────────────────
        distance_km = data.get("distance_km")
        if distance_km is None:
            return {"error": "distance_km is required"}
        
        try:
            distance_km = float(distance_km)
            if distance_km <= 0:
                raise ValueError
        except ValueError:
            return {"error": "distance_km must be a positive number"}
        
        # ─── Build vehicle data ──────────────────────────────────────
        vehicle_data = {
            "fuel_type": data.get("fuel_type", "petrol"),
            "fuel_consumption": data.get("fuel_consumption", 8),
            "maintenance_per_km": data.get("maintenance_per_km", 0),
            "insurance_annual": data.get("insurance", 0),
            "tax_annual": data.get("tax", 0),
            "annual_km": data.get("annual_km", 20000),
            "purchase_price": data.get("purchase_price", 0),
            "tyre_size": data.get("tyre_size", ""),
            "vehicle_type": data.get("vehicle_type", "Car")
        }
        
        # ─── Calculate using engine or fallback ──────────────────────
        if self.engine:
            try:
                result = self.engine.calculate_trip_cost(
                    distance_km=distance_km,
                    vehicle_data=vehicle_data
                )
                
                # Extract data safely
                summary = result.summary if hasattr(result, 'summary') else result.get('summary', {})
                fixed_costs = result.fixed_costs if hasattr(result, 'fixed_costs') else result.get('fixed_costs', {})
                operating_costs = result.operating_costs if hasattr(result, 'operating_costs') else result.get('operating_costs', {})
                
                return {
                    "success": True,
                    "data": {
                        "total_cost": summary.get("total_cost", 0),
                        "cost_per_km": summary.get("total_per_km", 0),
                        "fuel_cost": summary.get("energy_cost", 0),
                        "maintenance_cost": operating_costs.get("maintenance", 0),
                        "insurance_cost": fixed_costs.get("insurance", 0),
                        "tax_cost": fixed_costs.get("tax", 0) or fixed_costs.get("licensing", 0),
                        "tyre_cost": operating_costs.get("tyres", 0),
                        "depreciation_cost": fixed_costs.get("depreciation", 0),
                        "fixed_costs": fixed_costs,
                        "operating_costs": operating_costs,
                        "projection": result.projection if hasattr(result, 'projection') else result.get('projection', []),
                        "recommendations": result.recommendations if hasattr(result, 'recommendations') else result.get('recommendations', [])
                    }
                }
            except Exception as e:
                logger.error(f"Engine calculation failed: {e}")
                # Fall through to simple calculation
        
        # ─── Fallback: Simple calculation ────────────────────────────
        return self._calculate_simple(distance_km, vehicle_data)
    
    def _calculate_simple(self, distance_km: float, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simple fallback calculation when engine is not available
        """
        try:
            fuel_type = vehicle_data.get("fuel_type", "petrol")
            fuel_consumption = vehicle_data.get("fuel_consumption", 8)
            maintenance_per_km = vehicle_data.get("maintenance_per_km", 0)
            insurance_annual = vehicle_data.get("insurance_annual", 0)
            tax_annual = vehicle_data.get("tax_annual", 0)
            
            # Fuel prices (KES per litre)
            fuel_prices = {
                "petrol": 214.03,
                "diesel": 222.86,
                "electric": 30.00,
                "lpg": 120.00,
                "hybrid": 150.00,
                "cng": 100.00
            }
            fuel_price = fuel_prices.get(fuel_type, 214.03)
            
            # Calculate costs
            fuel_used = (distance_km / 100) * fuel_consumption
            fuel_cost = fuel_used * fuel_price
            maintenance_cost = distance_km * maintenance_per_km
            
            # Insurance and tax per trip
            annual_km = vehicle_data.get("annual_km", 20000)
            insurance_cost = (insurance_annual / annual_km) * distance_km if annual_km > 0 else 0
            tax_cost = (tax_annual / annual_km) * distance_km if annual_km > 0 else 0
            
            total_cost = fuel_cost + maintenance_cost + insurance_cost + tax_cost
            cost_per_km = total_cost / distance_km if distance_km > 0 else 0
            
            return {
                "success": True,
                "data": {
                    "total_cost": round(total_cost, 2),
                    "cost_per_km": round(cost_per_km, 2),
                    "fuel_cost": round(fuel_cost, 2),
                    "maintenance_cost": round(maintenance_cost, 2),
                    "insurance_cost": round(insurance_cost, 2),
                    "tax_cost": round(tax_cost, 2),
                    "tyre_cost": 0,
                    "depreciation_cost": 0,
                    "fixed_costs": {
                        "insurance": round(insurance_cost, 2),
                        "tax": round(tax_cost, 2)
                    },
                    "operating_costs": {
                        "fuel": round(fuel_cost, 2),
                        "maintenance": round(maintenance_cost, 2)
                    },
                    "projection": [],
                    "recommendations": self._get_fallback_recommendations(fuel_type, total_cost, distance_km)
                }
            }
        except Exception as e:
            logger.error(f"Simple calculation failed: {e}")
            return {"error": f"Calculation failed: {str(e)}"}
    
    def _get_fallback_recommendations(self, fuel_type: str, total_cost: float, distance_km: float) -> list:
        """Generate basic recommendations for fallback mode"""
        recommendations = []
        
        if fuel_type in ["petrol", "diesel"]:
            recommendations.append({
                "type": "fuel",
                "message": f"Your {fuel_type} trip cost is KES {total_cost:.2f}",
                "suggestion": "Consider a more fuel-efficient vehicle or alternative fuel options."
            })
        
        if distance_km > 100:
            recommendations.append({
                "type": "distance",
                "message": f"Long trip of {distance_km} km detected.",
                "suggestion": "Plan your route efficiently and consider carpooling."
            })
        
        return recommendations
