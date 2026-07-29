"""
Valuation Service - Business logic for vehicle valuations
ALL DATA sourced from scraper and database
Production Grade - Auto-D Kenya
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging
import random
from functools import lru_cache

from app.repositories.vehicle_repository import VehicleRepository
from app.engines.valuation_engine import ValuationEngine
from app.schemas.request import ValuationRequest
from app.schemas.response import ValuationResponse
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


class ValuationService:
    """Service for vehicle valuation operations using scraper and database data"""
    
    def __init__(self):
        self.repository = VehicleRepository()
        self.engine = ValuationEngine()
        self.data_service = DataService() if DataService else None
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
    
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
        if len(self._cache) > 500:
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k]["timestamp"]
            )
            for key_to_remove in sorted_keys[:50]:
                del self._cache[key_to_remove]
    
    # ─── Vehicle Data Methods ──────────────────────────────────────
    
    @lru_cache(maxsize=128)
    def get_makes(self) -> List[Dict[str, Any]]:
        """Get all vehicle makes with caching."""
        try:
            return self.repository.get_makes()
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
        """Get vehicle variant by ID with caching."""
        try:
            return self.repository.get_variant_by_id(variant_id)
        except Exception as e:
            logger.error(f"Error getting variant {variant_id}: {e}")
            return None
    
    def search_vehicles(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for vehicles with filters."""
        try:
            return self.repository.search_vehicles(query)
        except Exception as e:
            logger.error(f"Error searching vehicles: {e}")
            return []
    
    def get_vehicle_full_specs(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """Get full vehicle specifications."""
        cache_key = f"full_specs:{variant_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            result = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("""
                    *,
                    make:make_id (id, name, country),
                    model:model_id (id, name, body_type),
                    generation:generation_id (id, code, start_year, end_year)
                """)\
                .eq("id", variant_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                self._set_cache(cache_key, result.data[0])
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting vehicle specs: {e}")
            return None
    
    # ─── Valuation Methods ──────────────────────────────────────────
    
    def calculate_valuation(self, request: ValuationRequest) -> Optional[ValuationResponse]:
        """
        Calculate vehicle valuation using scraper and database data.
        
        Args:
            request: ValuationRequest with vehicle details
            
        Returns:
            ValuationResponse or None if valuation fails
        """
        try:
            # ─── Get vehicle data from database ──────────────────────────
            variant = self.repository.get_variant_by_id(request.variant_id)
            if not variant:
                logger.error(f"Variant not found: {request.variant_id}")
                return None
            
            # ─── Get market data from scraper ────────────────────────────
            market_stats = {}
            similar_listings = []
            location_data = {}
            type_params = {}
            dep_data = {}
            
            if self.data_service:
                try:
                    make = variant.get("make_name") or variant.get("make") or "Unknown"
                    model = variant.get("model_name") or variant.get("model") or "Unknown"
                    
                    market_stats = self.data_service.get_market_statistics(
                        make=make,
                        model=model,
                        days=90
                    ) or {}
                    
                    similar_listings = self.data_service.get_market_prices(
                        make=make,
                        model=model,
                        year_from=request.year - 2,
                        year_to=request.year + 2,
                        limit=100
                    ) or []
                    
                    location_data = self.data_service.get_location_factors(request.location) or {}
                except Exception as e:
                    logger.warning(f"Error getting scraper data: {e}")
            
            # ─── Get vehicle type parameters from database ──────────────
            body_type = variant.get("body_type") or variant.get("body_type_name", "sedan")
            if body_type:
                body_type = str(body_type).lower()
            
            try:
                type_params = self.data_service.get_vehicle_type_parameters(body_type) if self.data_service else {}
            except Exception as e:
                logger.warning(f"Error getting type parameters: {e}")
                type_params = {}
            
            # ─── Get depreciation rates from database ────────────────────
            dep_class = variant.get("depreciation_class") or f"{body_type.upper()}_D" if body_type else "STANDARD"
            try:
                dep_data = self.data_service.get_depreciation_rates(dep_class) if self.data_service else {}
            except Exception as e:
                logger.warning(f"Error getting depreciation rates: {e}")
                dep_data = {}
            
            # ─── Calculate valuation ──────────────────────────────────────
            try:
                result = self.engine.calculate_valuation(
                    variant=variant,
                    year=request.year,
                    mileage=request.mileage,
                    condition=request.condition,
                    accident_history=request.accident_history,
                    previous_owners=request.previous_owners,
                    location=request.location,
                    service_history=request.service_history,
                    market_stats=market_stats,
                    similar_listings=similar_listings,
                    location_data=location_data,
                    type_params=type_params,
                    dep_data=dep_data
                )
            except Exception as e:
                logger.error(f"Valuation engine error: {e}")
                # Fallback to simple valuation
                result = self._simple_valuation(variant, request)
            
            # ─── Build response ──────────────────────────────────────────
            return ValuationResponse(
                variant_id=variant.get("id"),
                make=variant.get("make_name") or variant.get("make"),
                model=variant.get("model_name") or variant.get("model"),
                variant=variant.get("name"),
                year=request.year,
                mileage=request.mileage,
                condition=request.condition,
                trade_value=result.get("trade_value", 0),
                dealer_value=result.get("dealer_value", 0),
                retail_value=result.get("retail_value", 0),
                quick_sale=result.get("quick_sale", 0),
                insurance_value=result.get("insurance_value", 0),
                market_value=result.get("market_value", 0),
                base_value=result.get("base_value", 0),
                depreciation_rate=result.get("depreciation_rate", 0.15),
                estimated_life=result.get("estimated_life", 20),
                confidence_score=result.get("confidence_score", 70),
                recommendations=result.get("recommendations", []),
                market_adjustments=result.get("market_adjustments", {}),
                scraper_data=result.get("scraper_data", {}),
                valuation_date=datetime.now(timezone.utc).isoformat(),
                report_id=f"VAL-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            )
            
        except Exception as e:
            logger.error(f"Valuation calculation error: {e}")
            return None
    
    def _simple_valuation(self, variant: Dict, request: ValuationRequest) -> Dict:
        """
        Simple valuation fallback when engine fails.
        """
        base_value = variant.get("market_value") or variant.get("base_price") or 1000000
        
        # Age depreciation
        current_year = datetime.now(timezone.utc).year
        age = max(0, current_year - request.year)
        age_factor = max(0.3, 1.0 - (age * 0.10))  # 10% per year, min 30%
        
        # Mileage depreciation
        mileage_factor = max(0.5, 1.0 - (request.mileage / 200000))  # 200k km = 50% value
        
        # Condition factor
        condition_factors = {
            "excellent": 1.0,
            "very_good": 0.90,
            "good": 0.80,
            "fair": 0.65,
            "poor": 0.50
        }
        condition_factor = condition_factors.get(request.condition, 0.80)
        
        # Calculate value
        market_value = base_value * age_factor * mileage_factor * condition_factor
        
        return {
            "market_value": round(market_value, 2),
            "trade_value": round(market_value * 0.85, 2),
            "dealer_value": round(market_value * 0.90, 2),
            "retail_value": round(market_value * 1.05, 2),
            "quick_sale": round(market_value * 0.80, 2),
            "insurance_value": round(market_value * 1.10, 2),
            "base_value": base_value,
            "depreciation_rate": 0.15,
            "estimated_life": 20,
            "confidence_score": 60,
            "recommendations": ["Simple valuation based on base values"],
            "market_adjustments": {
                "age_factor": age_factor,
                "mileage_factor": mileage_factor,
                "condition_factor": condition_factor
            },
            "scraper_data": {}
        }
    
    def calculate_bulk_valuation(self, requests: List[ValuationRequest]) -> List[ValuationResponse]:
        """Calculate valuations for multiple vehicles."""
        results = []
        for request in requests:
            result = self.calculate_valuation(request)
            if result:
                results.append(result)
        return results
    
    # ─── Valuation History ────────────────────────────────────────────
    
    def get_valuation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get valuation history for a user."""
        try:
            result = supabase.table(settings.TABLE_VALUATION_REPORTS)\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting valuation history: {e}")
            return []
    
    def save_valuation_report(self, user_id: str, valuation: ValuationResponse) -> Optional[Dict[str, Any]]:
        """Save valuation report to database."""
        try:
            data = {
                "user_id": user_id,
                "variant_id": valuation.variant_id,
                "make": valuation.make,
                "model": valuation.model,
                "variant": valuation.variant,
                "year": valuation.year,
                "mileage": valuation.mileage,
                "condition": valuation.condition,
                "trade_value": valuation.trade_value,
                "dealer_value": valuation.dealer_value,
                "retail_value": valuation.retail_value,
                "market_value": valuation.market_value,
                "confidence_score": valuation.confidence_score,
                "report_id": valuation.report_id,
                "recommendations": valuation.recommendations,
                "scraper_data": valuation.scraper_data if hasattr(valuation, 'scraper_data') else {},
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = supabase.table(settings.TABLE_VALUATION_REPORTS)\
                .insert(data)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error saving valuation report: {e}")
            return None
    
    # ─── Market Data Methods ──────────────────────────────────────────
    
    def get_market_comparison(self, variant_id: str) -> Dict[str, Any]:
        """Get market comparison for a vehicle using scraper data."""
        try:
            variant = self.repository.get_variant_by_id(variant_id)
            if not variant:
                return {"error": "Variant not found"}
            
            make = variant.get("make_name") or variant.get("make", "Unknown")
            model = variant.get("model_name") or variant.get("model", "Unknown")
            
            # Get market data from scraper
            market_stats = {}
            similar_listings = []
            
            if self.data_service:
                try:
                    market_stats = self.data_service.get_market_statistics(
                        make=make,
                        model=model,
                        days=90
                    ) or {}
                    
                    similar_listings = self.data_service.get_market_prices(
                        make=make,
                        model=model,
                        limit=50
                    ) or []
                except Exception as e:
                    logger.warning(f"Error getting market data: {e}")
            
            # Calculate price position
            avg_price = market_stats.get("average_price", 0)
            variant_price = variant.get("market_value") or variant.get("base_price") or 0
            price_position = self._calculate_price_position(variant_price, avg_price)
            
            return {
                "vehicle": {
                    "make": variant.get("make_name") or variant.get("make"),
                    "model": variant.get("model_name") or variant.get("model"),
                    "variant": variant.get("name")
                },
                "market": {
                    "stats": market_stats,
                    "listings": similar_listings[:5] if similar_listings else []
                },
                "comparison": {
                    "price_position": price_position,
                    "market_availability": market_stats.get("market_health", "unknown"),
                    "total_listings": market_stats.get("total_listings", 0),
                    "average_price": avg_price,
                    "median_price": market_stats.get("median_price", 0),
                    "price_range": {
                        "min": market_stats.get("min_price", 0),
                        "max": market_stats.get("max_price", 0)
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting market comparison: {e}")
            return {"error": str(e)}
    
    def _calculate_price_position(self, price: float, avg_price: float) -> str:
        """Calculate price position in market."""
        if avg_price == 0 or price == 0:
            return "unknown"
        
        ratio = price / avg_price
        if ratio > 1.2:
            return "above_average"
        elif ratio < 0.8:
            return "below_average"
        else:
            return "average"
    
    # ─── Valuation Factors ────────────────────────────────────────────
    
    def get_valuation_factors(self) -> Dict[str, Any]:
        """Get valuation factors from database."""
        cache_key = "valuation_factors"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            # Get condition factors
            condition_result = supabase.table("condition_factors")\
                .select("*")\
                .execute()
            
            # Get accident factors
            accident_result = supabase.table("accident_factors")\
                .select("*")\
                .execute()
            
            # Get location factors
            location_result = supabase.table("location_factors")\
                .select("*")\
                .execute()
            
            condition_factors = {}
            if condition_result.data:
                for c in condition_result.data:
                    condition_factors[c.get("condition", "good")] = {
                        "value": c.get("factor", 0.80),
                        "description": c.get("description", "")
                    }
            
            accident_factors = {}
            if accident_result.data:
                for a in accident_result.data:
                    accident_factors[a.get("accident_type", "none")] = {
                        "value": a.get("factor", 1.0),
                        "description": a.get("description", "")
                    }
            
            location_factors = {}
            if location_result.data:
                for l in location_result.data:
                    location_factors[l.get("location", "other")] = l.get("price_adjustment", 1.0)
            
            factors = {
                "factors": {
                    "age": {"weight": 0.25, "description": "Vehicle age in years"},
                    "mileage": {"weight": 0.20, "description": "Total kilometers driven"},
                    "condition": {"weight": 0.15, "description": "Physical and mechanical condition"},
                    "market_demand": {"weight": 0.15, "description": "Current market demand"},
                    "location": {"weight": 0.10, "description": "Geographic location"},
                    "service_history": {"weight": 0.10, "description": "Maintenance records"},
                    "accident_history": {"weight": 0.05, "description": "Past accident records"}
                },
                "condition_ratings": condition_factors,
                "accident_ratings": accident_factors,
                "location_factors": location_factors,
                "data_source": "database"
            }
            
            self._set_cache(cache_key, factors)
            return factors
            
        except Exception as e:
            logger.error(f"Error getting valuation factors: {e}")
            # Fallback factors
            fallback = self._get_fallback_factors()
            return fallback
    
    def _get_fallback_factors(self) -> Dict[str, Any]:
        """Get fallback valuation factors when database fails."""
        return {
            "factors": {
                "age": {"weight": 0.25, "description": "Vehicle age in years"},
                "mileage": {"weight": 0.20, "description": "Total kilometers driven"},
                "condition": {"weight": 0.15, "description": "Physical and mechanical condition"},
                "market_demand": {"weight": 0.15, "description": "Current market demand"},
                "location": {"weight": 0.10, "description": "Geographic location"},
                "service_history": {"weight": 0.10, "description": "Maintenance records"},
                "accident_history": {"weight": 0.05, "description": "Past accident records"}
            },
            "condition_ratings": {
                "excellent": {"value": 1.0, "description": "Like new condition"},
                "very_good": {"value": 0.85, "description": "Minor wear and tear"},
                "good": {"value": 0.70, "description": "Normal wear for age"},
                "fair": {"value": 0.55, "description": "Significant wear"},
                "poor": {"value": 0.40, "description": "Major issues"}
            },
            "location_factors": {
                "nairobi": 1.05,
                "mombasa": 1.02,
                "kisumu": 1.00,
                "nakuru": 1.00,
                "eldoret": 1.00,
                "other": 0.98
            },
            "data_source": "fallback"
        }
    
    def get_market_trends(self, make: str, model: str) -> Dict[str, Any]:
        """Get market trends from scraper data."""
        try:
            market_stats = {}
            if self.data_service:
                try:
                    market_stats = self.data_service.get_market_statistics(
                        make=make,
                        model=model,
                        days=90
                    ) or {}
                except Exception as e:
                    logger.warning(f"Error getting market trends: {e}")
            
            return {
                "make": make,
                "model": model,
                "trends": {
                    "average_price": market_stats.get("average_price", 0),
                    "median_price": market_stats.get("median_price", 0),
                    "total_listings": market_stats.get("total_listings", 0),
                    "market_health": market_stats.get("market_health", "unknown"),
                    "price_range": {
                        "min": market_stats.get("min_price", 0),
                        "max": market_stats.get("max_price", 0)
                    },
                    "sources": market_stats.get("sources", {})
                },
                "data_source": "scraper"
            }
            
        except Exception as e:
            logger.error(f"Error getting market trends: {e}")
            return {
                "make": make,
                "model": model,
                "trends": {},
                "error": str(e),
                "data_source": "error"
            }
    
    # ─── Clear Cache ────────────────────────────────────────────────────
    
    def clear_cache(self):
        """Clear all caches."""
        self._cache.clear()
        self.get_makes.cache_clear()
        self.get_models_by_make.cache_clear()
        self.get_variants_by_model.cache_clear()
        self.get_variant.cache_clear()
        logger.info("Valuation service cache cleared")


# ─── Singleton ─────────────────────────────────────────────────────

_valuation_service: Optional[ValuationService] = None


def get_valuation_service() -> ValuationService:
    """Get or create ValuationService singleton."""
    global _valuation_service
    if _valuation_service is None:
        _valuation_service = ValuationService()
    return _valuation_service


# ─── Export ─────────────────────────────────────────────────────

__all__ = [
    "ValuationService",
    "get_valuation_service",
]
