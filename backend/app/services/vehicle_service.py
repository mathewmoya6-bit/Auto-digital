"""
Vehicle Service - Business logic for vehicle operations
Production Grade - Auto-D Kenya
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.database import supabase
from app.core.config import settings
from app.models.vehicle import VehicleMake, VehicleModel, VehicleVariant
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.response import VehicleDetailResponse

logger = logging.getLogger(__name__)


class VehicleService:
    """Service for vehicle operations with caching and performance optimizations"""
    
    def __init__(self):
        self.repository = VehicleRepository()
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    # ─── Cache Helpers ──────────────────────────────────────────────
    
    def _get_cache_key(self, method: str, *args, **kwargs) -> str:
        """Generate cache key for method call."""
        key_parts = [method]
        key_parts.extend(str(a) for a in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        return ":".join(key_parts)
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if valid."""
        if key in self._cache:
            entry = self._cache[key]
            if (datetime.now(timezone.utc) - entry["timestamp"]).total_seconds() < self._cache_ttl:
                return entry["value"]
            else:
                del self._cache[key]
        return None
    
    def _set_cache(self, key: str, value: Any):
        """Set cached value."""
        self._cache[key] = {
            "value": value,
            "timestamp": datetime.now(timezone.utc)
        }
        # Limit cache size
        if len(self._cache) > 1000:
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k]["timestamp"]
            )
            for key_to_remove in sorted_keys[:100]:
                del self._cache[key_to_remove]
    
    def _clear_cache(self, prefix: Optional[str] = None):
        """Clear cache, optionally by prefix."""
        if prefix:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()
    
    # ─── Basic CRUD Operations ──────────────────────────────────────
    
    @lru_cache(maxsize=128)
    def get_makes(self) -> List[Dict[str, Any]]:
        """Get all vehicle makes with caching."""
        try:
            return self.repository.get_all_makes()
        except Exception as e:
            logger.error(f"Error getting makes: {e}")
            return []
    
    @lru_cache(maxsize=256)
    def get_models_by_make(self, make_id: str) -> List[Dict[str, Any]]:
        """Get models by make ID with caching."""
        try:
            return self.repository.get_models_by_make(make_id)
        except Exception as e:
            logger.error(f"Error getting models for make {make_id}: {e}")
            return []
    
    @lru_cache(maxsize=512)
    def get_variants_by_model(self, model_id: str) -> List[Dict[str, Any]]:
        """Get variants by model ID with caching."""
        try:
            return self.repository.get_variants_by_model(model_id)
        except Exception as e:
            logger.error(f"Error getting variants for model {model_id}: {e}")
            return []
    
    @lru_cache(maxsize=1024)
    def get_variant(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """Get variant by ID with caching."""
        try:
            return self.repository.get_variant_by_id(variant_id)
        except Exception as e:
            logger.error(f"Error getting variant {variant_id}: {e}")
            return None
    
    def get_vehicle_details(self, variant_id: str) -> Optional[VehicleDetailResponse]:
        """Get complete vehicle details with all specifications."""
        try:
            variant = self.get_variant(variant_id)
            if not variant:
                return None
            
            # Get make and model information (with caching)
            make = None
            model = None
            
            if variant.get("make_id"):
                make = self.repository.get_make_by_id(variant["make_id"])
            if variant.get("model_id"):
                model = self.repository.get_model_by_id(variant["model_id"])
            
            return VehicleDetailResponse(
                variant_id=variant["id"],
                make=make["name"] if make else None,
                model=model["name"] if model else None,
                variant=variant.get("name"),
                year=variant.get("year"),
                engine_cc=variant.get("engine_cc"),
                fuel_type=variant.get("fuel_type"),
                transmission=variant.get("transmission"),
                fuel_consumption=variant.get("fuel_consumption"),
                insurance_group=variant.get("insurance_group"),
                service_interval=variant.get("service_interval"),
                tyre_size=variant.get("tyre_size"),
                market_value=variant.get("market_value"),
                depreciation_class=variant.get("depreciation_class"),
                tyre_cost=variant.get("tyre_cost"),
                service_cost=variant.get("service_cost")
            )
        except Exception as e:
            logger.error(f"Error getting vehicle details for {variant_id}: {e}")
            return None
    
    # ─── Extended Vehicle Methods ──────────────────────────────────
    
    def get_vehicle_full_specs(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """Get full vehicle specifications with relationships."""
        cache_key = f"full_specs:{variant_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            result = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("""
                    *,
                    make:make_id (id, name, country, logo_url),
                    model:model_id (id, name, body_type, body_style),
                    generation:generation_id (id, code, start_year, end_year, generation_name)
                """)\
                .eq("id", variant_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                self._set_cache(cache_key, result.data[0])
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting vehicle full specs: {e}")
            return None
    
    def search_vehicles(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for vehicles with filters."""
        try:
            search_query = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("""
                    *,
                    make:make_id (id, name),
                    model:model_id (id, name)
                """)
            
            # Apply filters
            if query.get("make"):
                search_query = search_query.ilike("make_name", f"%{query['make']}%")
            if query.get("model"):
                search_query = search_query.ilike("model_name", f"%{query['model']}%")
            if query.get("year_from"):
                search_query = search_query.gte("year", query["year_from"])
            if query.get("year_to"):
                search_query = search_query.lte("year", query["year_to"])
            if query.get("fuel_type"):
                search_query = search_query.eq("fuel_type", query["fuel_type"])
            if query.get("transmission"):
                search_query = search_query.eq("transmission", query["transmission"])
            if query.get("min_price"):
                search_query = search_query.gte("market_value", query["min_price"])
            if query.get("max_price"):
                search_query = search_query.lte("market_value", query["max_price"])
            
            # Apply sorting
            if query.get("sort_by"):
                order = "ascending" if query.get("sort_order", "asc") == "asc" else "descending"
                search_query = search_query.order(query["sort_by"], ascending=(order == "ascending"))
            else:
                search_query = search_query.order("market_value", ascending=True)
            
            # Apply limit
            if query.get("limit"):
                search_query = search_query.limit(query["limit"])
            
            result = search_query.execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error searching vehicles: {e}")
            return []
    
    def get_vehicles_by_make(self, make: str) -> List[Dict[str, Any]]:
        """Get all vehicles by make name."""
        cache_key = f"vehicles_by_make:{make.lower()}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            result = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("""
                    *,
                    make:make_id (id, name),
                    model:model_id (id, name)
                """)\
                .ilike("make_name", f"%{make}%")\
                .order("name", ascending=True)\
                .execute()
            
            data = result.data or []
            self._set_cache(cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Error getting vehicles by make: {e}")
            return []
    
    def get_vehicles_by_model(self, model: str) -> List[Dict[str, Any]]:
        """Get all vehicles by model name."""
        cache_key = f"vehicles_by_model:{model.lower()}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            result = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("""
                    *,
                    make:make_id (id, name),
                    model:model_id (id, name)
                """)\
                .ilike("model_name", f"%{model}%")\
                .order("name", ascending=True)\
                .execute()
            
            data = result.data or []
            self._set_cache(cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Error getting vehicles by model: {e}")
            return []
    
    def get_vehicles_by_year(self, year: int) -> List[Dict[str, Any]]:
        """Get all vehicles by year."""
        cache_key = f"vehicles_by_year:{year}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            result = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("""
                    *,
                    make:make_id (id, name),
                    model:model_id (id, name)
                """)\
                .eq("year", year)\
                .order("name", ascending=True)\
                .execute()
            
            data = result.data or []
            self._set_cache(cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Error getting vehicles by year: {e}")
            return []
    
    def get_vehicles_by_fuel_type(self, fuel_type: str) -> List[Dict[str, Any]]:
        """Get all vehicles by fuel type."""
        cache_key = f"vehicles_by_fuel:{fuel_type.lower()}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            result = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("""
                    *,
                    make:make_id (id, name),
                    model:model_id (id, name)
                """)\
                .eq("fuel_type", fuel_type)\
                .order("name", ascending=True)\
                .execute()
            
            data = result.data or []
            self._set_cache(cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Error getting vehicles by fuel type: {e}")
            return []
    
    def get_vehicles_by_price_range(self, min_price: float, max_price: float) -> List[Dict[str, Any]]:
        """Get all vehicles within a price range."""
        try:
            result = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("""
                    *,
                    make:make_id (id, name),
                    model:model_id (id, name)
                """)\
                .gte("market_value", min_price)\
                .lte("market_value", max_price)\
                .order("market_value", ascending=True)\
                .execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting vehicles by price range: {e}")
            return []
    
    # ─── Advanced Search ───────────────────────────────────────────
    
    def advanced_search(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Advanced vehicle search with pagination."""
        try:
            query = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("""
                    *,
                    make:make_id (id, name, country),
                    model:model_id (id, name, body_type)
                """)
            
            # Apply all filters
            if filters.get("make_id"):
                query = query.eq("make_id", filters["make_id"])
            if filters.get("model_id"):
                query = query.eq("model_id", filters["model_id"])
            if filters.get("year_from"):
                query = query.gte("year", filters["year_from"])
            if filters.get("year_to"):
                query = query.lte("year", filters["year_to"])
            if filters.get("fuel_type"):
                query = query.eq("fuel_type", filters["fuel_type"])
            if filters.get("transmission"):
                query = query.eq("transmission", filters["transmission"])
            if filters.get("min_price"):
                query = query.gte("market_value", filters["min_price"])
            if filters.get("max_price"):
                query = query.lte("market_value", filters["max_price"])
            if filters.get("body_type"):
                query = query.ilike("body_type", f"%{filters['body_type']}%")
            if filters.get("search_term"):
                search = filters["search_term"]
                query = query.or_(
                    f"name.ilike.%{search}%,variant_name.ilike.%{search}%,make_name.ilike.%{search}%,model_name.ilike.%{search}%"
                )
            
            # Get total count
            count_query = query.clone()
            count_result = count_query.select("count", count="exact").execute()
            total = count_result.count if hasattr(count_result, 'count') else 0
            
            # Apply pagination
            if filters.get("limit"):
                query = query.limit(filters["limit"])
            if filters.get("offset"):
                query = query.offset(filters["offset"])
            
            # Apply sorting
            sort_by = filters.get("sort_by", "market_value")
            sort_order = "ascending" if filters.get("sort_order", "asc") == "asc" else "descending"
            query = query.order(sort_by, ascending=(sort_order == "ascending"))
            
            result = query.execute()
            
            return {
                "items": result.data or [],
                "total": total,
                "limit": filters.get("limit", 20),
                "offset": filters.get("offset", 0)
            }
            
        except Exception as e:
            logger.error(f"Error in advanced search: {e}")
            return {
                "items": [],
                "total": 0,
                "limit": filters.get("limit", 20),
                "offset": filters.get("offset", 0)
            }
    
    # ─── Popular & Featured ────────────────────────────────────────
    
    def get_popular_vehicles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular vehicles."""
        cache_key = f"popular_vehicles:{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            result = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("""
                    *,
                    make:make_id (id, name),
                    model:model_id (id, name)
                """)\
                .order("popularity", ascending=False)\
                .limit(limit)\
                .execute()
            
            data = result.data or []
            self._set_cache(cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Error getting popular vehicles: {e}")
            return []
    
    def get_featured_vehicles(self, limit: int = 6) -> List[Dict[str, Any]]:
        """Get featured vehicles."""
        cache_key = f"featured_vehicles:{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            result = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("""
                    *,
                    make:make_id (id, name),
                    model:model_id (id, name)
                """)\
                .eq("is_featured", True)\
                .order("market_value", ascending=True)\
                .limit(limit)\
                .execute()
            
            data = result.data or []
            self._set_cache(cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Error getting featured vehicles: {e}")
            return []
    
    def get_new_arrivals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get newest vehicle arrivals."""
        cache_key = f"new_arrivals:{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            result = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("""
                    *,
                    make:make_id (id, name),
                    model:model_id (id, name)
                """)\
                .order("created_at", ascending=False)\
                .limit(limit)\
                .execute()
            
            data = result.data or []
            self._set_cache(cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Error getting new arrivals: {e}")
            return []
    
    # ─── Vehicle Statistics ────────────────────────────────────────
    
    def get_vehicle_stats(self) -> Dict[str, Any]:
        """Get vehicle statistics."""
        cache_key = "vehicle_stats"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            total = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("count", count="exact")\
                .execute()
            
            makes = supabase.table(settings.TABLE_VEHICLE_MAKES)\
                .select("count", count="exact")\
                .execute()
            
            models = supabase.table(settings.TABLE_VEHICLE_MODELS)\
                .select("count", count="exact")\
                .execute()
            
            # Fuel type distribution
            fuel_result = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("fuel_type", count="exact")\
                .execute()
            
            fuel_counts = {}
            if fuel_result.data:
                for item in fuel_result.data:
                    fuel_type = item.get("fuel_type") or "unknown"
                    fuel_counts[fuel_type] = fuel_counts.get(fuel_type, 0) + 1
            
            stats = {
                "total_vehicles": total.count or 0,
                "total_makes": makes.count or 0,
                "total_models": models.count or 0,
                "fuel_distribution": fuel_counts,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            self._set_cache(cache_key, stats)
            return stats
            
        except Exception as e:
            logger.error(f"Error getting vehicle stats: {e}")
            return {
                "total_vehicles": 0,
                "total_makes": 0,
                "total_models": 0,
                "fuel_distribution": {},
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
    
    # ─── User Vehicle Management ───────────────────────────────────
    
    def get_user_vehicles(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all vehicles for a user."""
        try:
            result = supabase.table("vehicles")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", ascending=False)\
                .execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting user vehicles: {e}")
            return []
    
    def add_user_vehicle(self, user_id: str, vehicle_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a vehicle to user's garage."""
        try:
            data = {
                "user_id": user_id,
                "plate": vehicle_data.get("plate", "").upper().strip(),
                "make_model": vehicle_data.get("make_model", "").strip(),
                "vin": vehicle_data.get("vin", "").strip().upper() if vehicle_data.get("vin") else None,
                "year": vehicle_data.get("year"),
                "mileage": vehicle_data.get("mileage", 0),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Validate required fields
            if not data["plate"] or not data["make_model"]:
                logger.warning("Missing required fields for user vehicle")
                return None
            
            result = supabase.table("vehicles")\
                .insert(data)\
                .execute()
            
            if result.data and len(result.data) > 0:
                self._clear_cache(f"user_vehicles:{user_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error adding user vehicle: {e}")
            return None
    
    def update_user_vehicle(self, vehicle_id: str, user_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a user's vehicle."""
        try:
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Clean up fields
            if "plate" in data:
                data["plate"] = data["plate"].upper().strip()
            if "vin" in data and data.get("vin"):
                data["vin"] = data["vin"].upper().strip()
            
            result = supabase.table("vehicles")\
                .update(data)\
                .eq("id", vehicle_id)\
                .eq("user_id", user_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                self._clear_cache(f"user_vehicles:{user_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating user vehicle: {e}")
            return None
    
    def delete_user_vehicle(self, vehicle_id: str, user_id: str) -> bool:
        """Delete a user's vehicle."""
        try:
            result = supabase.table("vehicles")\
                .delete()\
                .eq("id", vehicle_id)\
                .eq("user_id", user_id)\
                .execute()
            
            if len(result.data or []) > 0:
                self._clear_cache(f"user_vehicles:{user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting user vehicle: {e}")
            return False
    
    # ─── Clear Cache Methods ──────────────────────────────────────
    
    def clear_vehicle_cache(self):
        """Clear all vehicle caches."""
        self._clear_cache()
        # Clear lru_cache functions
        self.get_makes.cache_clear()
        self.get_models_by_make.cache_clear()
        self.get_variants_by_model.cache_clear()
        self.get_variant.cache_clear()
        logger.info("Vehicle cache cleared")

# ─── Singleton ─────────────────────────────────────────────────────
_vehicle_service: Optional[VehicleService] = None


def get_vehicle_service() -> VehicleService:
    """Get or create VehicleService singleton."""
    global _vehicle_service
    if _vehicle_service is None:
        _vehicle_service = VehicleService()
    return _vehicle_service
