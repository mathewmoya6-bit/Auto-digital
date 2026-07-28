"""
Valuation Service - Business logic for vehicle valuations
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
from app.services.market_service import MarketService

logger = logging.getLogger(__name__)


class ValuationService:
    """Service for vehicle valuation operations"""
    
    def __init__(self):
        self.repository = VehicleRepository()
        self.engine = ValuationEngine()
        self.market_service = MarketService()
    
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
        """Calculate vehicle valuation"""
        # Get vehicle data
        variant = self.repository.get_variant_by_id(request.variant_id)
        if not variant:
            logger.error(f"Variant not found: {request.variant_id}")
            return None
        
        # Get market data for adjustments
        market_data = self.market_service.get_market_insights(
            make=variant.get("make_name"),
            model=variant.get("model_name"),
            days=90
        )
        
        # Calculate valuation
        result = self.engine.calculate_valuation(
            variant=variant,
            year=request.year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            previous_owners=request.previous_owners,
            location=request.location,
            service_history=request.service_history,
            market_data=market_data
        )
        
        # Build response
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
        """Get market comparison for a vehicle"""
        variant = self.repository.get_variant_by_id(variant_id)
        if not variant:
            return {"error": "Variant not found"}
        
        market_data = self.market_service.get_market_insights(
            make=variant.get("make_name"),
            model=variant.get("model_name"),
            days=90
        )
        
        return {
            "vehicle": {
                "make": variant.get("make_name"),
                "model": variant.get("model_name"),
                "variant": variant.get("name")
            },
            "market": market_data,
            "comparison": {
                "price_position": self._calculate_price_position(
                    variant.get("base_price", 0),
                    market_data
                ),
                "market_availability": self._calculate_availability(market_data),
                "trend": self._calculate_trend(market_data)
            }
        }
    
    def _calculate_price_position(self, price: float, market_data: Dict) -> str:
        """Calculate price position in market"""
        avg_price = market_data.get("metrics", {}).get("average_price", 0)
        if avg_price == 0:
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
        total = market_data.get("metrics", {}).get("total_listings", 0)
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
        """Get valuation factors and their weights"""
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
            }
        }
