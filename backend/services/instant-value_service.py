"""
Valuation Service - Auto-D Kenya
API endpoints for vehicle valuation
"""

from typing import Dict, Any
from engines.valuation_engine import ValuationEngine


class ValuationService:
    """Vehicle valuation service"""
    
    def __init__(self):
        self.engine = ValuationEngine()
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate vehicle valuation"""
        purchase_price = data.get("purchase_price")
        age_years = data.get("age_years")
        
        if purchase_price is None:
            return {"error": "purchase_price is required"}, 400
        if age_years is None:
            return {"error": "age_years is required"}, 400
        
        try:
            purchase_price = float(purchase_price)
            age_years = float(age_years)
            if purchase_price <= 0 or age_years < 0:
                raise ValueError
        except ValueError:
            return {"error": "purchase_price must be positive and age_years must be non-negative"}, 400
        
        current_year = 2026  # or datetime.now().year
        year = current_year - int(age_years)
        
        result = self.engine.calculate_value(
            purchase_price=purchase_price,
            year=year,
            make=data.get("make", "Unknown"),
            model=data.get("model", "Unknown"),
            vehicle_type=data.get("vehicle_type", "Car"),
            condition=data.get("condition", "Good"),
            mileage=data.get("mileage", 0),
            location=data.get("location", "Nairobi"),
            accident_history=data.get("accident_history", "None"),
            previous_owners=data.get("previous_owners", 0)
        )
        
        return {
            "success": True,
            "data": {
                "current_value": result.current_value,
                "market_value": result.market_value,
                "estimated_value": result.estimated_value,
                "trade_in_value": result.trade_in_value,
                "retail_value": result.retail_value,
                "total_depreciation": result.depreciation.get("total_depreciation", 0),
                "value_retained": result.depreciation.get("value_retained", 0),
                "confidence_score": result.confidence_score,
                "valuation_range": result.valuation_range,
                "recommendations": result.recommendations,
                "market_adjustments": result.market_adjustments
            }
        }
