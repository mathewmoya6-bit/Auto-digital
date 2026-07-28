"""
Mileage Service - Business logic for mileage calculations
ALL DATA sourced from scraper and database
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

from app.repositories.vehicle_repository import VehicleRepository
from app.repositories.mileage_repository import MileageRepository
from app.repositories.fuel_repository import FuelRepository
from app.engines.mileage_rate_engine import MileageRateEngine
from app.schemas.request import MileageRateRequest
from app.schemas.response import MileageRateResponse
from app.core.database import supabase
from app.core.config import settings
from app.services.data_service import DataService

logger = logging.getLogger(__name__)


class MileageService:
    """Service for mileage rate calculations using scraper and database data"""
    
    def __init__(self):
        self.vehicle_repository = VehicleRepository()
        self.mileage_repository = MileageRepository()
        self.fuel_repository = FuelRepository()
        self.engine = MileageRateEngine()
        self.data_service = DataService()
    
    # ─── Main Calculation ──────────────────────────────────────────────
    
    def calculate_mileage_rate(self, request: MileageRateRequest) -> Optional[MileageRateResponse]:
        """Calculate mileage rate for a vehicle using scraper and database data"""
        
        # ─── Get vehicle data from database ──────────────────────────
        variant = self.vehicle_repository.get_variant_by_id(request.variant_id)
        if not variant:
            logger.error(f"Variant not found: {request.variant_id}")
            return None
        
        # ─── Get fuel price from database ────────────────────────────
        fuel_price = request.fuel_price
        if not fuel_price or fuel_price <= 0:
            fuel_type = variant.get("fuel_type", "petrol")
            fuel_data = self.data_service.get_fuel_prices(fuel_type)
            fuel_price = fuel_data.get("price", 200.00)
        
        # ─── Get market data from scraper ────────────────────────────
        market_stats = self.data_service.get_market_statistics(
            make=variant.get("make_name") or variant.get("make"),
            model=variant.get("model_name") or variant.get("model"),
            days=90
        )
        
        # ─── Get similar listings from scraper ──────────────────────
        similar_listings = self.data_service.get_market_prices(
            make=variant.get("make_name") or variant.get("make"),
            model=variant.get("model_name") or variant.get("model"),
            year_from=request.year - 2 if hasattr(request, 'year') else None,
            year_to=request.year + 2 if hasattr(request, 'year') else None,
            limit=50
        )
        
        # ─── Get location factors from database ──────────────────────
        location = request.location if hasattr(request, 'location') else "nairobi"
        location_data = self.data_service.get_location_factors(location)
        
        # ─── Get vehicle type parameters from database ──────────────
        body_type = variant.get("body_type") or variant.get("body_type_name", "sedan").lower()
        type_params = self.data_service.get_vehicle_type_parameters(body_type)
        
        # ─── Calculate mileage rate ──────────────────────────────────
        result = self.engine.calculate_mileage_rate(
            variant=variant,
            request=request,
            market_stats=market_stats,
            similar_listings=similar_listings,
            location_data=location_data,
            type_params=type_params,
            fuel_price=fuel_price
        )
        
        # ─── Save report ──────────────────────────────────────────────
        try:
            report_data = {
                "user_id": request.user_id if hasattr(request, 'user_id') else None,
                "vehicle_id": request.variant_id,
                "trip_distance": request.distance,
                "trip_type": request.trip_type,
                "driving_style": request.driving_style,
                "usage_type": request.usage_type if hasattr(request, 'usage_type') else "private",
                "location": location,
                "total_cost": result.total_running_cost if hasattr(result, 'total_running_cost') else 0,
                "cost_per_km": result.total_rate if hasattr(result, 'total_rate') else 0,
                "fuel_price": fuel_price,
                "components": {
                    "fuel": result.fuel_rate * request.distance if hasattr(result, 'fuel_rate') else 0,
                    "maintenance": result.maintenance_rate * request.distance if hasattr(result, 'maintenance_rate') else 0,
                    "tyres": result.tyre_rate * request.distance if hasattr(result, 'tyre_rate') else 0,
                    "insurance": result.insurance_rate * request.distance if hasattr(result, 'insurance_rate') else 0,
                    "depreciation": result.depreciation_rate * request.distance if hasattr(result, 'depreciation_rate') else 0,
                    "finance": result.finance_rate * request.distance if hasattr(result, 'finance_rate') else 0,
                    "misc": result.misc_rate * request.distance if hasattr(result, 'misc_rate') else 0
                },
                "market_data": {
                    "listings_available": market_stats.get("total_listings", 0),
                    "market_health": market_stats.get("market_health", "unknown"),
                    "average_price": market_stats.get("average_price", 0)
                },
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            self.mileage_repository.save_mileage_report(report_data)
            logger.info(f"Mileage report saved for user {request.user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to save mileage report: {e}")
        
        return result
    
    # ─── Report Retrieval ──────────────────────────────────────────────
    
    def get_mileage_reports(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get mileage reports for a user"""
        return self.mileage_repository.get_mileage_reports(user_id, limit)
    
    def get_mileage_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific mileage report"""
        return self.mileage_repository.get_mileage_report(report_id)
    
    def get_mileage_reports_by_date_range(
        self, 
        user_id: str, 
        start_date: str, 
        end_date: str,
        limit: int = 100
    ) -> List[Dict]:
        """Get mileage reports within a date range"""
        try:
            result = supabase.table(settings.TABLE_MILEAGE_REPORTS)\
                .select("*")\
                .eq("user_id", user_id)\
                .gte("created_at", start_date)\
                .lte("created_at", end_date)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting mileage reports by date range: {e}")
            return []
    
    def get_mileage_reports_by_vehicle(self, user_id: str, vehicle_id: str) -> List[Dict]:
        """Get mileage reports for a specific vehicle"""
        try:
            result = supabase.table(settings.TABLE_MILEAGE_REPORTS)\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("vehicle_id", vehicle_id)\
                .order("created_at", desc=True)\
                .execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting mileage reports by vehicle: {e}")
            return []
    
    # ─── Summary Statistics ────────────────────────────────────────────
    
    def get_mileage_summary(self, user_id: str) -> Dict:
        """Get summary statistics for mileage reports"""
        try:
            reports = self.mileage_repository.get_mileage_reports(user_id, 1000)
            
            if not reports:
                return {
                    "total_trips": 0,
                    "total_distance": 0,
                    "total_cost": 0,
                    "average_cost_per_km": 0,
                    "average_distance": 0,
                    "most_used_vehicle": None,
                    "last_trip": None
                }
            
            total_distance = sum(r.get("trip_distance", 0) for r in reports)
            total_cost = sum(r.get("total_cost", 0) for r in reports)
            
            # Find most used vehicle
            vehicles = {}
            for r in reports:
                vid = r.get("vehicle_id")
                if vid:
                    vehicles[vid] = vehicles.get(vid, 0) + 1
            
            most_used = max(vehicles.items(), key=lambda x: x[1]) if vehicles else None
            
            # Get most recent trip
            last_trip = reports[0] if reports else None
            
            return {
                "total_trips": len(reports),
                "total_distance": round(total_distance, 2),
                "total_cost": round(total_cost, 2),
                "average_cost_per_km": round(total_cost / total_distance, 2) if total_distance > 0 else 0,
                "average_distance": round(total_distance / len(reports), 2) if reports else 0,
                "most_used_vehicle": {
                    "vehicle_id": most_used[0] if most_used else None,
                    "trips": most_used[1] if most_used else 0
                } if most_used else None,
                "last_trip": last_trip
            }
            
        except Exception as e:
            logger.error(f"Error getting mileage summary: {e}")
            return {
                "total_trips": 0,
                "total_distance": 0,
                "total_cost": 0,
                "average_cost_per_km": 0,
                "average_distance": 0,
                "most_used_vehicle": None,
                "last_trip": None
            }
    
    # ─── Trip Planning ─────────────────────────────────────────────────
    
    def plan_trip(
        self,
        variant_id: str,
        distance: float,
        fuel_price: Optional[float] = None,
        trip_type: str = "mixed",
        driving_style: str = "normal",
        location: str = "nairobi"
    ) -> Dict:
        """Plan a trip and estimate costs using scraper data"""
        
        # Get vehicle from database
        variant = self.vehicle_repository.get_variant_by_id(variant_id)
        if not variant:
            return {"error": "Vehicle not found"}
        
        # Get fuel price from database
        if not fuel_price or fuel_price <= 0:
            fuel_type = variant.get("fuel_type", "petrol")
            fuel_data = self.data_service.get_fuel_prices(fuel_type)
            fuel_price = fuel_data.get("price", 200.00)
        
        # Get market data from scraper
        market_stats = self.data_service.get_market_statistics(
            make=variant.get("make_name") or variant.get("make"),
            model=variant.get("model_name") or variant.get("model"),
            days=90
        )
        
        # Create request
        request = MileageRateRequest(
            variant_id=variant_id,
            distance=distance,
            trip_type=trip_type,
            driving_style=driving_style,
            fuel_price=fuel_price,
            location=location
        )
        
        # Calculate
        result = self.calculate_mileage_rate(request)
        if not result:
            return {"error": "Could not calculate trip cost"}
        
        # Get fuel consumption from variant
        fuel_consumption = variant.get("fuel_consumption_combined", 8.0)
        
        # Estimate time (average speed 60 km/h)
        estimated_time = distance / 60
        estimated_time_hours = int(estimated_time)
        estimated_time_minutes = int((estimated_time - estimated_time_hours) * 60)
        
        # CO2 emissions
        fuel_litres = (distance / 100) * fuel_consumption
        co2_emissions = fuel_litres * 2.3
        
        return {
            "trip": {
                "distance": round(distance, 2),
                "trip_type": trip_type,
                "driving_style": driving_style,
                "estimated_time": f"{estimated_time_hours}h {estimated_time_minutes}m"
            },
            "cost": {
                "total": round(result.total_running_cost if hasattr(result, 'total_running_cost') else 0, 2),
                "per_km": round(result.total_rate if hasattr(result, 'total_rate') else 0, 2),
                "fuel": round(result.fuel_rate * distance if hasattr(result, 'fuel_rate') else 0, 2),
                "maintenance": round(result.maintenance_rate * distance if hasattr(result, 'maintenance_rate') else 0, 2),
                "tyres": round(result.tyre_rate * distance if hasattr(result, 'tyre_rate') else 0, 2),
                "insurance": round(result.insurance_rate * distance if hasattr(result, 'insurance_rate') else 0, 2),
                "depreciation": round(result.depreciation_rate * distance if hasattr(result, 'depreciation_rate') else 0, 2)
            },
            "fuel": {
                "consumption": round(fuel_consumption, 2),
                "litres_needed": round(fuel_litres, 2),
                "price_per_litre": fuel_price,
                "co2_emissions": round(co2_emissions, 2)
            },
            "vehicle": {
                "make": variant.get("make_name", "Unknown"),
                "model": variant.get("model_name", "Unknown"),
                "variant": variant.get("name", "Unknown"),
                "fuel_type": variant.get("fuel_type", "petrol")
            },
            "market_data": {
                "listings_available": market_stats.get("total_listings", 0),
                "market_health": market_stats.get("market_health", "unknown")
            }
        }
    
    # ─── Multi-Trip ────────────────────────────────────────────────────
    
    def calculate_multi_trip(
        self,
        variant_id: str,
        trips: List[Dict],
        fuel_price: Optional[float] = None
    ) -> Dict:
        """Calculate costs for multiple trips using scraper data"""
        results = []
        total_distance = 0
        total_cost = 0
        
        for trip in trips:
            request = MileageRateRequest(
                variant_id=variant_id,
                distance=trip.get("distance", 0),
                trip_type=trip.get("trip_type", "mixed"),
                driving_style=trip.get("driving_style", "normal"),
                fuel_price=fuel_price,
                location=trip.get("location", "nairobi")
            )
            
            result = self.calculate_mileage_rate(request)
            if result:
                results.append({
                    "distance": trip.get("distance", 0),
                    "trip_type": trip.get("trip_type", "mixed"),
                    "location": trip.get("location", "nairobi"),
                    "cost": round(result.total_running_cost if hasattr(result, 'total_running_cost') else 0, 2),
                    "cost_per_km": round(result.total_rate if hasattr(result, 'total_rate') else 0, 2)
                })
                total_distance += trip.get("distance", 0)
                total_cost += result.total_running_cost if hasattr(result, 'total_running_cost') else 0
        
        return {
            "total_trips": len(trips),
            "total_distance": round(total_distance, 2),
            "total_cost": round(total_cost, 2),
            "average_cost_per_km": round(total_cost / total_distance, 2) if total_distance > 0 else 0,
            "trips": results
        }
    
    # ─── Fuel Efficiency Tracking ─────────────────────────────────────
    
    def track_fuel_efficiency(
        self,
        user_id: str,
        vehicle_id: str,
        distance: float,
        fuel_used: float,
        cost: float
    ) -> Dict:
        """Track fuel efficiency for a trip"""
        try:
            fuel_consumption = (fuel_used / distance) * 100  # L/100km
            cost_per_km = cost / distance if distance > 0 else 0
            
            data = {
                "user_id": user_id,
                "vehicle_id": vehicle_id,
                "distance": round(distance, 2),
                "fuel_used": round(fuel_used, 2),
                "fuel_consumption": round(fuel_consumption, 2),
                "cost": round(cost, 2),
                "cost_per_km": round(cost_per_km, 2),
                "created_at": datetime.now().isoformat()
            }
            
            result = supabase.table("fuel_tracking")\
                .insert(data)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return {
                    "success": True,
                    "data": result.data[0],
                    "message": "Fuel efficiency tracked successfully"
                }
            return {"success": False, "message": "Failed to track fuel efficiency"}
            
        except Exception as e:
            logger.error(f"Error tracking fuel efficiency: {e}")
            return {"success": False, "message": str(e)}
    
    def get_fuel_efficiency_stats(self, user_id: str, vehicle_id: Optional[str] = None) -> Dict:
        """Get fuel efficiency statistics"""
        try:
            query = supabase.table("fuel_tracking")\
                .select("*")\
                .eq("user_id", user_id)
            
            if vehicle_id:
                query = query.eq("vehicle_id", vehicle_id)
            
            query = query.order("created_at", desc=True)
            
            result = query.execute()
            data = result.data or []
            
            if not data:
                return {
                    "total_trips": 0,
                    "average_consumption": 0,
                    "best_consumption": 0,
                    "worst_consumption": 0,
                    "total_distance": 0,
                    "total_cost": 0
                }
            
            consumptions = [d.get("fuel_consumption", 0) for d in data if d.get("fuel_consumption", 0) > 0]
            
            return {
                "total_trips": len(data),
                "average_consumption": round(sum(consumptions) / len(consumptions), 2) if consumptions else 0,
                "best_consumption": round(min(consumptions), 2) if consumptions else 0,
                "worst_consumption": round(max(consumptions), 2) if consumptions else 0,
                "total_distance": round(sum(d.get("distance", 0) for d in data), 2),
                "total_cost": round(sum(d.get("cost", 0) for d in data), 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting fuel efficiency stats: {e}")
            return {
                "total_trips": 0,
                "average_consumption": 0,
                "best_consumption": 0,
                "worst_consumption": 0,
                "total_distance": 0,
                "total_cost": 0
            }
    
    # ─── Route Optimization ────────────────────────────────────────────
    
    def optimize_routes(
        self,
        start_location: str,
        end_location: str,
        waypoints: Optional[List[str]] = None,
        fuel_price: Optional[float] = None,
        vehicle_type: Optional[str] = None
    ) -> Dict:
        """Optimize route for fuel efficiency using database data"""
        
        # Get fuel price from database
        if not fuel_price:
            fuel_data = self.data_service.get_fuel_prices("petrol")
            fuel_price = fuel_data.get("price", 200.00)
        
        # Get location factors
        location_data = self.data_service.get_location_factors(start_location)
        
        # Estimate distance (simplified - would use mapping API in production)
        base_distance = 100  # km
        if waypoints:
            base_distance += len(waypoints) * 20
        
        # Get fuel consumption based on vehicle type
        if vehicle_type:
            type_params = self.data_service.get_vehicle_type_parameters(vehicle_type)
            fuel_multiplier = type_params.get("fuel_multiplier", 1.0)
        else:
            fuel_multiplier = 1.0
        
        fuel_consumption = 8.0 * fuel_multiplier  # L/100km
        fuel_cost = (base_distance / 100) * fuel_consumption * fuel_price
        
        # Apply location factor
        location_factor = location_data.get("price_adjustment", 1.0)
        total_cost = fuel_cost * location_factor
        
        return {
            "route": {
                "from": start_location,
                "to": end_location,
                "waypoints": waypoints or [],
                "total_distance": round(base_distance, 2),
                "estimated_time": f"{int(base_distance / 60)}h {int((base_distance / 60 - int(base_distance / 60)) * 60)}m"
            },
            "fuel": {
                "consumption": round(fuel_consumption, 2),
                "litres_needed": round((base_distance / 100) * fuel_consumption, 2),
                "price_per_litre": fuel_price,
                "cost": round(total_cost, 2)
            },
            "location_factors": {
                "adjustment": round(location_factor, 2),
                "demand_index": location_data.get("demand_index", 1.0),
                "supply_index": location_data.get("supply_index", 1.0)
            },
            "recommendations": [
                "Maintain steady speed for better fuel economy",
                "Avoid rapid acceleration and braking",
                "Check tyre pressure before trip",
                "Plan route to avoid heavy traffic"
            ]
        }
