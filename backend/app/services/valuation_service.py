"""
Valuation Service - Business logic for vehicle valuations
ALL DATA sourced from scraper and database
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import random

from app.repositories.vehicle_repository import VehicleRepository
from app.engines.valuation_engine import ValuationEngine
from app.schemas.request import ValuationRequest
from app.schemas.response import ValuationResponse
from app.core.database import supabase
from app.core.config import settings
from app.services.data_service import DataService

logger = logging.getLogger(__name__)


class ValuationService:
    """Service for vehicle valuation operations using scraper and database data"""
    
    def __init__(self):
        self.repository = VehicleRepository()
        self.engine = ValuationEngine()
        self.data_service = DataService()
    
    # ─── Vehicle Data Methods ──────────────────────────────────────────
    
    def get_makes(self) -> List[Dict[str, Any]]:
        """Get all vehicle makes"""
        return self.repository.get_makes()
    
    def get_models_by_make(self, make_id: str) -> List[Dict[str, Any]]:
        """Get models by make ID"""
        return self.repository.get_models_by_make(make_id)
    
    def get_variants_by_model(self, model_id: str) -> List[Dict[str, Any]]:
        """Get variants by model ID"""
        return self.repository.get_variants_by_model(model_id)
    
    def get_variant(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """Get vehicle variant by ID"""
        return self.repository.get_variant_by_id(variant_id)
    
    def search_vehicles(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for vehicles with filters"""
        return self.repository.search_vehicles(query)
    
    def get_vehicle_full_specs(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """Get full vehicle specifications"""
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
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting vehicle specs: {e}")
            return None
    
    # ─── Valuation Methods ────────────────────────────────────────────
    
    def calculate_valuation(self, request: ValuationRequest) -> Optional[ValuationResponse]:
        """Calculate vehicle valuation using scraper and database data"""
        
        # ─── Get vehicle data from database ──────────────────────────
        variant = self.repository.get_variant_by_id(request.variant_id)
        if not variant:
            logger.error(f"Variant not found: {request.variant_id}")
            return None
        
        # ─── Get market data from scraper ────────────────────────────
        make = variant.get("make_name") or variant.get("make")
        model = variant.get("model_name") or variant.get("model")
        
        market_stats = self.data_service.get_market_statistics(
            make=make,
            model=model,
            days=90
        )
        
        # ─── Get similar listings from scraper ──────────────────────
        similar_listings = self.data_service.get_market_prices(
            make=make,
            model=model,
            year_from=request.year - 2,
            year_to=request.year + 2,
            limit=100
        )
        
        # ─── Get location factors from database ──────────────────────
        location_data = self.data_service.get_location_factors(request.location)
        
        # ─── Get vehicle type parameters from database ──────────────
        body_type = variant.get("body_type") or variant.get("body_type_name", "sedan").lower()
        type_params = self.data_service.get_vehicle_type_parameters(body_type)
        
        # ─── Get depreciation rates from database ────────────────────
        dep_class = variant.get("depreciation_class") or f"{body_type.upper()}_D"
        dep_data = self.data_service.get_depreciation_rates(dep_class)
        
        # ─── Calculate valuation ──────────────────────────────────────
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
        
        # ─── Build response ──────────────────────────────────────────
        return ValuationResponse(
            variant_id=variant.get("id"),
            make=variant.get("make_name"),
            model=variant.get("model_name"),
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
            valuation_date=datetime.now().isoformat(),
            report_id=f"VAL-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        )
    
    def calculate_bulk_valuation(self, requests: List[ValuationRequest]) -> List[ValuationResponse]:
        """Calculate valuations for multiple vehicles"""
        results = []
        for request in requests:
            result = self.calculate_valuation(request)
            if result:
                results.append(result)
        return results
    
    # ─── Valuation History ────────────────────────────────────────────
    
    def get_valuation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get valuation history for a user"""
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
        """Save valuation report to database"""
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
                "created_at": datetime.now().isoformat()
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
        """Get market comparison for a vehicle using scraper data"""
        variant = self.repository.get_variant_by_id(variant_id)
        if not variant:
            return {"error": "Variant not found"}
        
        make = variant.get("make_name") or variant.get("make")
        model = variant.get("model_name") or variant.get("model")
        
        # Get market data from scraper
        market_stats = self.data_service.get_market_statistics(
            make=make,
            model=model,
            days=90
        )
        
        # Get similar listings
        similar_listings = self.data_service.get_market_prices(
            make=make,
            model=model,
            limit=50
        )
        
        # Calculate price position
        avg_price = market_stats.get("average_price", 0)
        variant_price = variant.get("market_value") or variant.get("base_price") or 0
        price_position = self._calculate_price_position(variant_price, avg_price)
        
        return {
            "vehicle": {
                "make": variant.get("make_name"),
                "model": variant.get("model_name"),
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
    
    def _calculate_price_position(self, price: float, avg_price: float) -> str:
        """Calculate price position in market"""
        if avg_price == 0 or price == 0:
            return "unknown"
        
        ratio = price / avg_price
        if ratio > 1.2:
            return "above_average"
        elif ratio < 0.8:
            return "below_average"
        else:
            return "average"
    
    def _calculate_availability(self, market_data: Dict) -> str:
        """Calculate market availability"""
        total = market_data.get("total_listings", 0)
        if total > 50:
            return "high"
        elif total > 20:
            return "medium"
        elif total > 5:
            return "low"
        else:
            return "very_low"
    
    def _calculate_trend(self, market_data: Dict) -> str:
        """Calculate market trend"""
        insights = market_data.get("insights", [])
        for insight in insights:
            if "up" in insight.lower() and "prices" in insight.lower():
                return "increasing"
            elif "down" in insight.lower() and "prices" in insight.lower():
                return "decreasing"
        return "stable"
    
    # ─── Helper Methods ──────────────────────────────────────────────
    
    def estimate_price_from_image(self, image_data: str) -> Dict[str, Any]:
        """Estimate vehicle price from image (mock implementation)"""
        # This would connect to AI/ML service in production
        return {
            "estimated_price": random.randint(500000, 5000000),
            "confidence": random.randint(40, 80),
            "make": "Unknown",
            "model": "Unknown",
            "year": random.randint(2010, 2024)
        }
    
    def get_valuation_factors(self) -> Dict[str, Any]:
        """Get valuation factors from database"""
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
                    condition_factors[c["condition"]] = {
                        "value": c["factor"],
                        "description": c.get("description", "")
                    }
            
            accident_factors = {}
            if accident_result.data:
                for a in accident_result.data:
                    accident_factors[a["accident_type"]] = {
                        "value": a["factor"],
                        "description": a.get("description", "")
                    }
            
            location_factors = {}
            if location_result.data:
                for l in location_result.data:
                    location_factors[l["location"]] = l["price_adjustment"]
            
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
                "condition_ratings": condition_factors,
                "accident_ratings": accident_factors,
                "location_factors": location_factors,
                "data_source": "database"
            }
            
        except Exception as e:
            logger.error(f"Error getting valuation factors: {e}")
            # Fallback factors
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
        """Get market trends from scraper data"""
        market_stats = self.data_service.get_market_statistics(
            make=make,
            model=model,
            days=90
        )
        
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
