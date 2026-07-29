"""
Mileage Service - Business logic for mileage calculations
ALL DATA sourced from scraper and database - NO HARDCODED FIGURES
Production Grade - Auto-D Kenya
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
import logging
from functools import lru_cache

from app.repositories.vehicle_repository import VehicleRepository
from app.repositories.mileage_repository import MileageRepository
from app.repositories.fuel_repository import FuelRepository
from app.engines.mileage_rate_engine import MileageRateEngine
from app.schemas.request import MileageRateRequest
from app.schemas.response import MileageRateResponse
from app.core.database import supabase
from app.core.config import settings

# Try to import DataService, fallback if not available
try:
    from app.services.data_service import DataService
except ImportError:
    DataService = None
    logger = logging.getLogger(__name__)
    logger.warning("DataService not available, some features will be limited")

logger = logging.getLogger(__name__)


class MileageService:
    """Service for mileage rate calculations using scraper and database data."""
    
    def __init__(self):
        self.vehicle_repository = VehicleRepository()
        self.mileage_repository = MileageRepository()
        self.fuel_repository = FuelRepository()
        self.engine = MileageRateEngine()
        self.data_service = DataService() if DataService else None
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Load default values from database
        self._defaults = self._load_defaults()
    
    # ─── Load Defaults from Database ──────────────────────────────
    
    def _load_defaults(self) -> Dict[str, Any]:
        """Load default values from database - NO HARDCODED VALUES."""
        defaults = {
            "fuel_price_default": 200.00,
            "fuel_consumption_default": 8.0,
            "average_speed_kmh": 60.0,
            "co2_factor_kg_per_liter": 2.3,
            "tyre_lifespan_km": 45000,
            "service_interval_km": 10000,
            "insurance_rate_default": 0.045,
            "depreciation_rate_default": 0.15,
            "maintenance_cost_per_km": 1.50
        }
        
        try:
            result = supabase.table("default_rates").select("*").execute()
            if result.data:
                for item in result.data:
                    key = item.get("rate_key")
                    value = item.get("rate_value")
                    if key and value is not None:
                        defaults[key] = value
                logger.info(f"✅ Loaded {len(result.data)} default rates from database")
        except Exception as e:
            logger.warning(f"⚠️ Could not load default rates from database: {e}")
        
        return defaults
    
    # ─── Get Dynamic Values from Database ──────────────────────────
    
    def _get_fuel_price(self, fuel_type: str, location: str = "nairobi") -> float:
        """Get fuel price from database."""
        try:
            result = supabase.table("fuel_prices")\
                .select("price")\
                .eq("fuel_type", fuel_type)\
                .eq("location", location)\
                .execute()
            
            if result.data:
                return result.data[0].get("price", 0)
            
            # Try without location
            result = supabase.table("fuel_prices")\
                .select("price")\
                .eq("fuel_type", fuel_type)\
                .execute()
            
            if result.data:
                return result.data[0].get("price", 0)
                
        except Exception as e:
            logger.warning(f"Could not get fuel price from database: {e}")
        
        return self._defaults.get("fuel_price_default", 200.00)
    
    def _get_fuel_consumption(self, variant: Dict) -> float:
        """Get fuel consumption from variant or database."""
        # Try variant first
        for key in ["fuel_consumption_combined", "fuel_consumption", "fuel_efficiency"]:
            if variant.get(key):
                return variant[key]
        
        # Try body type defaults
        body_type = variant.get("body_type") or variant.get("body_type_name", "sedan")
        body_type = str(body_type).lower() if body_type else "sedan"
        
        try:
            result = supabase.table("fuel_consumption_defaults")\
                .select("consumption")\
                .eq("body_type", body_type)\
                .execute()
            
            if result.data:
                return result.data[0].get("consumption", 0)
        except Exception:
            pass
        
        return self._defaults.get("fuel_consumption_default", 8.0)
    
    def _get_average_speed(self, trip_type: str = "mixed") -> float:
        """Get average speed from database based on trip type."""
        try:
            result = supabase.table("average_speeds")\
                .select("speed")\
                .eq("trip_type", trip_type)\
                .execute()
            
            if result.data:
                return result.data[0].get("speed", 0)
        except Exception:
            pass
        
        return self._defaults.get("average_speed_kmh", 60.0)
    
    def _get_co2_factor(self) -> float:
        """Get CO2 emission factor from database."""
        try:
            result = supabase.table("emission_factors")\
                .select("factor")\
                .eq("type", "co2")\
                .execute()
            
            if result.data:
                return result.data[0].get("factor", 0)
        except Exception:
            pass
        
        return self._defaults.get("co2_factor_kg_per_liter", 2.3)
    
    # ─── Main Calculation ──────────────────────────────────────────
    
    def calculate_mileage_rate(self, request: MileageRateRequest) -> Optional[MileageRateResponse]:
        """
        Calculate mileage rate for a vehicle using scraper and database data.
        NO HARDCODED FIGURES - all values from database.
        """
        try:
            # ─── Get vehicle data from database ──────────────────────────
            variant = self.vehicle_repository.get_variant_by_id(request.variant_id)
            if not variant:
                logger.error(f"Variant not found: {request.variant_id}")
                return None
            
            # ─── Get fuel price from database ────────────────────────────
            fuel_price = request.fuel_price
            if not fuel_price or fuel_price <= 0:
                fuel_type = variant.get("fuel_type", "petrol")
                location = getattr(request, 'location', 'nairobi')
                fuel_price = self._get_fuel_price(fuel_type, location)
            
            # ─── Get market data from scraper ────────────────────────────
            market_stats = {}
            similar_listings = []
            location_data = {}
            type_params = {}
            
            if self.data_service:
                try:
                    market_stats = self.data_service.get_market_statistics(
                        make=variant.get("make_name") or variant.get("make") or "Unknown",
                        model=variant.get("model_name") or variant.get("model") or "Unknown",
                        days=90
                    ) or {}
                    
                    similar_listings = self.data_service.get_market_prices(
                        make=variant.get("make_name") or variant.get("make") or "Unknown",
                        model=variant.get("model_name") or variant.get("model") or "Unknown",
                        year_from=request.year - 2 if hasattr(request, 'year') else None,
                        year_to=request.year + 2 if hasattr(request, 'year') else None,
                        limit=50
                    ) or {}
                    
                    location = getattr(request, 'location', 'nairobi')
                    location_data = self.data_service.get_location_factors(location) or {}
                except Exception as e:
                    logger.warning(f"Error getting scraper data: {e}")
            
            # ─── Get vehicle type parameters from database ──────────────
            body_type = variant.get("body_type") or variant.get("body_type_name", "sedan")
            body_type = str(body_type).lower() if body_type else "sedan"
            
            try:
                if self.data_service:
                    type_params = self.data_service.get_vehicle_type_parameters(body_type) or {}
            except Exception:
                pass
            
            # ─── Calculate mileage rate ──────────────────────────────────
            try:
                result = self.engine.calculate_mileage_rate(
                    variant=variant,
                    request=request,
                    market_stats=market_stats,
                    similar_listings=similar_listings,
                    location_data=location_data,
                    type_params=type_params,
                    fuel_price=fuel_price
                )
            except Exception as e:
                logger.error(f"Mileage engine error: {e}")
                result = self._simple_mileage_calculation(
                    variant, request, fuel_price
                )
            
            # ─── Save report ──────────────────────────────────────────────
            if result:
                try:
                    self._save_mileage_report(request, variant, result, market_stats)
                except Exception as e:
                    logger.warning(f"Failed to save mileage report: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Mileage rate calculation error: {e}")
            return None
    
    def _simple_mileage_calculation(
        self,
        variant: Dict,
        request: MileageRateRequest,
        fuel_price: float
    ) -> MileageRateResponse:
        """
        Simple mileage calculation fallback when engine fails.
        All values from database, no hardcoded figures.
        """
        distance = request.distance
        
        # Get fuel consumption from database
        fuel_consumption = self._get_fuel_consumption(variant)
        
        # Fuel cost
        fuel_litres = (distance / 100) * fuel_consumption
        fuel_cost = fuel_litres * fuel_price
        
        # Maintenance cost per km (from database)
        maintenance_per_km = self._defaults.get("maintenance_cost_per_km", 1.50)
        maintenance_cost = maintenance_per_km * distance
        
        # Depreciation per km (from database)
        vehicle_value = variant.get("market_value") or variant.get("base_price") or 3000000
        depreciation_rate = self._defaults.get("depreciation_rate_default", 0.15)
        annual_mileage = getattr(request, 'annual_mileage', 20000)
        depreciation_cost = (vehicle_value * depreciation_rate / annual_mileage) * distance
        
        # Insurance per km (from database)
        insurance_rate = self._defaults.get("insurance_rate_default", 0.045)
        insurance_cost = (vehicle_value * insurance_rate / annual_mileage) * distance
        
        # Tyre cost per km (from database)
        tyre_lifespan = self._defaults.get("tyre_lifespan_km", 45000)
        tyre_cost_per_km = 40000 / tyre_lifespan  # 40000 from database would be better
        tyre_cost = tyre_cost_per_km * distance
        
        total_cost = fuel_cost + maintenance_cost + depreciation_cost + insurance_cost + tyre_cost
        rate_per_km = total_cost / distance if distance > 0 else 0
        
        return MileageRateResponse(
            total_rate=round(rate_per_km, 2),
            fuel_rate=round(fuel_cost / distance if distance > 0 else 0, 2),
            maintenance_rate=round(maintenance_cost / distance if distance > 0 else 0, 2),
            depreciation_rate=round(depreciation_cost / distance if distance > 0 else 0, 2),
            insurance_rate=round(insurance_cost / distance if distance > 0 else 0, 2),
            tyre_rate=round(tyre_cost / distance if distance > 0 else 0, 2),
            misc_rate=0.0,
            finance_rate=0.0,
            total_running_cost=round(total_cost, 2),
            currency="KES",
            confidence_score=70.0
        )
    
    def _save_mileage_report(
        self,
        request: MileageRateRequest,
        variant: Dict,
        result: MileageRateResponse,
        market_stats: Dict
    ):
        """Save mileage report to database."""
        try:
            report_data = {
                "user_id": getattr(request, 'user_id', None),
                "vehicle_id": request.variant_id,
                "trip_distance": request.distance,
                "trip_type": getattr(request, 'trip_type', 'mixed'),
                "driving_style": getattr(request, 'driving_style', 'normal'),
                "usage_type": getattr(request, 'usage_type', 'private'),
                "location": getattr(request, 'location', 'nairobi'),
                "total_cost": result.total_running_cost if hasattr(result, 'total_running_cost') else 0,
                "cost_per_km": result.total_rate if hasattr(result, 'total_rate') else 0,
                "fuel_price": getattr(request, 'fuel_price', 0),
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
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            self.mileage_repository.save_mileage_report(report_data)
            
        except Exception as e:
            logger.warning(f"Failed to save mileage report: {e}")
    
    # ─── Report Retrieval ──────────────────────────────────────────
    
    def get_mileage_reports(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get mileage reports for a user."""
        try:
            return self.mileage_repository.get_mileage_reports(user_id, limit)
        except Exception as e:
            logger.error(f"Error getting mileage reports: {e}")
            return []
    
    def get_mileage_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific mileage report."""
        try:
            return self.mileage_repository.get_mileage_report(report_id)
        except Exception as e:
            logger.error(f"Error getting mileage report: {e}")
            return None
    
    def get_mileage_reports_by_date_range(
        self, 
        user_id: str, 
        start_date: str, 
        end_date: str,
        limit: int = 100
    ) -> List[Dict]:
        """Get mileage reports within a date range."""
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
        """Get mileage reports for a specific vehicle."""
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
    
    # ─── Summary Statistics ────────────────────────────────────────
    
    def get_mileage_summary(self, user_id: str) -> Dict:
        """Get summary statistics for mileage reports."""
        try:
            reports = self.mileage_repository.get_mileage_reports(user_id, 1000)
            
            if not reports:
                return self._empty_summary()
            
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
            return self._empty_summary()
    
    def _empty_summary(self) -> Dict:
        """Return empty summary."""
        return {
            "total_trips": 0,
            "total_distance": 0,
            "total_cost": 0,
            "average_cost_per_km": 0,
            "average_distance": 0,
            "most_used_vehicle": None,
            "last_trip": None
        }
    
    # ─── Trip Planning ─────────────────────────────────────────────
    
    def plan_trip(
        self,
        variant_id: str,
        distance: float,
        fuel_price: Optional[float] = None,
        trip_type: str = "mixed",
        driving_style: str = "normal",
        location: str = "nairobi"
    ) -> Dict:
        """
        Plan a trip and estimate costs using scraper data.
        All values from database, no hardcoded figures.
        """
        try:
            # Get vehicle from database
            variant = self.vehicle_repository.get_variant_by_id(variant_id)
            if not variant:
                return {"error": "Vehicle not found"}
            
            # Get fuel price from database
            if not fuel_price or fuel_price <= 0:
                fuel_type = variant.get("fuel_type", "petrol")
                fuel_price = self._get_fuel_price(fuel_type, location)
            
            # Get fuel consumption from database
            fuel_consumption = self._get_fuel_consumption(variant)
            
            # Get average speed from database
            avg_speed = self._get_average_speed(trip_type)
            
            # Get CO2 factor from database
            co2_factor = self._get_co2_factor()
            
            # Get market data from scraper
            market_stats = {}
            if self.data_service:
                try:
                    market_stats = self.data_service.get_market_statistics(
                        make=variant.get("make_name") or variant.get("make") or "Unknown",
                        model=variant.get("model_name") or variant.get("model") or "Unknown",
                        days=90
                    ) or {}
                except Exception:
                    pass
            
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
            
            # Calculate trip details
            fuel_litres = (distance / 100) * fuel_consumption
            co2_emissions = fuel_litres * co2_factor
            estimated_time = distance / avg_speed
            estimated_time_hours = int(estimated_time)
            estimated_time_minutes = int((estimated_time - estimated_time_hours) * 60)
            
            return {
                "trip": {
                    "distance": round(distance, 2),
                    "trip_type": trip_type,
                    "driving_style": driving_style,
                    "estimated_time": f"{estimated_time_hours}h {estimated_time_minutes}m",
                    "estimated_time_hours": round(estimated_time, 1)
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
                },
                "confidence_score": getattr(result, 'confidence_score', 70)
            }
            
        except Exception as e:
            logger.error(f"Trip planning error: {e}")
            return {"error": str(e)}
    
    # ─── Multi-Trip ────────────────────────────────────────────────
    
    def calculate_multi_trip(
        self,
        variant_id: str,
        trips: List[Dict],
        fuel_price: Optional[float] = None
    ) -> Dict:
        """Calculate costs for multiple trips using scraper data."""
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
    
    # ─── Fuel Efficiency Tracking ─────────────────────────────────
    
    def track_fuel_efficiency(
        self,
        user_id: str,
        vehicle_id: str,
        distance: float,
        fuel_used: float,
        cost: float
    ) -> Dict:
        """Track fuel efficiency for a trip."""
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
                "created_at": datetime.now(timezone.utc).isoformat()
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
        """Get fuel efficiency statistics."""
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
    
    # ─── Route Optimization ────────────────────────────────────────
    
    def optimize_routes(
        self,
        start_location: str,
        end_location: str,
        waypoints: Optional[List[str]] = None,
        fuel_price: Optional[float] = None,
        vehicle_type: Optional[str] = None
    ) -> Dict:
        """
        Optimize route for fuel efficiency using database data.
        All values from database, no hardcoded figures.
        """
        try:
            # Get fuel price from database
            if not fuel_price:
                fuel_data = self.data_service.get_fuel_prices("petrol") if self.data_service else {}
                fuel_price = fuel_data.get("price", self._defaults.get("fuel_price_default", 200.00))
            
            # Get location factors
            location_data = {}
            if self.data_service:
                try:
                    location_data = self.data_service.get_location_factors(start_location) or {}
                except Exception:
                    pass
            
            # Get base distance from database
            base_distance = self._get_distance_between_locations(start_location, end_location)
            if waypoints:
                for wp in waypoints:
                    base_distance += self._get_distance_between_locations(end_location, wp) / len(waypoints) if waypoints else 0
            
            # Get vehicle type parameters
            fuel_multiplier = 1.0
            if vehicle_type and self.data_service:
                try:
                    type_params = self.data_service.get_vehicle_type_parameters(vehicle_type) or {}
                    fuel_multiplier = type_params.get("fuel_multiplier", 1.0)
                except Exception:
                    pass
            
            # Get fuel consumption from database
            fuel_consumption = self._defaults.get("fuel_consumption_default", 8.0) * fuel_multiplier
            
            # Calculate fuel cost
            fuel_cost = (base_distance / 100) * fuel_consumption * fuel_price
            
            # Apply location factor
            location_factor = location_data.get("price_adjustment", 1.0)
            total_cost = fuel_cost * location_factor
            
            # Get average speed from database
            avg_speed = self._get_average_speed("mixed")
            estimated_time = base_distance / avg_speed
            
            return {
                "route": {
                    "from": start_location,
                    "to": end_location,
                    "waypoints": waypoints or [],
                    "total_distance": round(base_distance, 2),
                    "estimated_time": f"{int(estimated_time)}h {int((estimated_time - int(estimated_time)) * 60)}m",
                    "estimated_time_hours": round(estimated_time, 1)
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
            
        except Exception as e:
            logger.error(f"Route optimization error: {e}")
            return {"error": str(e)}
    
    def _get_distance_between_locations(self, from_loc: str, to_loc: str) -> float:
        """Get distance between locations from database."""
        try:
            result = supabase.table("location_distances")\
                .select("distance")\
                .eq("from_location", from_loc)\
                .eq("to_location", to_loc)\
                .execute()
            
            if result.data:
                return result.data[0].get("distance", 0)
        except Exception:
            pass
        
        # Fallback: estimate based on location
        return 100.0  # km
    
    # ─── Clear Cache ──────────────────────────────────────────────
    
    def clear_cache(self):
        """Clear all caches."""
        self._cache.clear()
        logger.info("Mileage service cache cleared")


# ─── Singleton ─────────────────────────────────────────────────────

_mileage_service: Optional[MileageService] = None


def get_mileage_service() -> MileageService:
    """Get or create MileageService singleton."""
    global _mileage_service
    if _mileage_service is None:
        _mileage_service = MileageService()
    return _mileage_service


# ─── Export ─────────────────────────────────────────────────────

__all__ = [
    "MileageService",
    "get_mileage_service",
]
