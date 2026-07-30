# app/modules/valuation/engine.py
# Auto-D Kenya - Valuation Engine
# ================================================================
# TYPE: MODULE - Vehicle valuation calculation engine

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from app.core.config import settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class ValuationEngine:
    """
    Vehicle valuation engine.
    
    Calculates vehicle market value using:
    - Base price from market data
    - Age depreciation
    - Mileage adjustment
    - Location factor
    - Condition factor
    - Accident history
    """
    
    def __init__(self):
        self.supabase = get_supabase()
    
    def calculate_age_factor(self, year: int) -> float:
        """Calculate age depreciation factor."""
        age = datetime.now().year - year
        
        if age <= 0: return 1.0
        if age <= 1: return 0.95
        if age <= 2: return 0.90
        if age <= 3: return 0.85
        if age <= 4: return 0.80
        if age <= 5: return 0.75
        if age <= 6: return 0.70
        if age <= 7: return 0.65
        if age <= 8: return 0.60
        if age <= 10: return 0.50
        if age <= 12: return 0.40
        if age <= 15: return 0.30
        return 0.20
    
    def calculate_mileage_factor(self, mileage: float, age: int) -> float:
        """Calculate mileage adjustment factor."""
        if mileage <= 0:
            return 1.0
        
        expected = max(age * 20000, 10000)
        ratio = mileage / expected if expected > 0 else 1.0
        
        if ratio <= 0.5: return 1.05
        if ratio <= 0.75: return 1.02
        if ratio <= 1.0: return 1.00
        if ratio <= 1.25: return 0.97
        if ratio <= 1.5: return 0.93
        if ratio <= 2.0: return 0.85
        return 0.75
    
    def get_location_factor(self, location: str) -> float:
        """Get location factor."""
        factors = {
            "nairobi": 1.05, "mombasa": 1.02, "kisumu": 1.00,
            "nakuru": 1.00, "eldoret": 1.00, "thika": 1.00,
            "kiambu": 1.02, "kajiado": 1.00, "machakos": 1.00,
            "meru": 0.98, "nyeri": 0.98, "embu": 0.97,
            "malindi": 1.02, "nanyuki": 1.01, "other": 1.00
        }
        return factors.get(location.lower(), 1.00)
    
    def get_condition_factor(self, condition: str) -> float:
        """Get condition factor."""
        factors = {
            "excellent": 1.10, "very_good": 1.05, "good": 1.00,
            "fair": 0.90, "poor": 0.75
        }
        return factors.get(condition.lower(), 1.00)
    
    def get_accident_factor(self, accident_history: str) -> float:
        """Get accident history factor."""
        factors = {
            "none": 1.00, "minor": 0.92, "major": 0.80, "total_loss": 0.60
        }
        return factors.get(accident_history.lower(), 1.00)
    
    async def get_base_price(self, variant_id: str) -> float:
        """Get base price for a variant."""
        try:
            variant = self.supabase.table("vehicle_variants").select("*").eq("variant_id", variant_id).execute()
            if variant.data and variant.data[0].get("base_price"):
                return float(variant.data[0]["base_price"])
            
            market = self.supabase.table("market_prices").select("avg_price").eq("variant_id", variant_id).execute()
            if market.data and market.data[0].get("avg_price"):
                return float(market.data[0]["avg_price"])
            
            return settings.DEFAULT_BASE_PRICE
            
        except Exception as e:
            logger.error(f"Error getting base price: {str(e)}")
            return settings.DEFAULT_BASE_PRICE
    
    async def calculate(
        self,
        variant_id: str,
        year: int,
        mileage: float,
        condition: str = "good",
        accident_history: str = "none",
        location: str = "nairobi",
        variant_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Calculate vehicle valuation."""
        try:
            # Get base price
            base_price = await self.get_base_price(variant_id)
            
            # Calculate factors
            age = datetime.now().year - year
            age_factor = self.calculate_age_factor(year)
            mileage_factor = self.calculate_mileage_factor(mileage, age)
            location_factor = self.get_location_factor(location)
            condition_factor = self.get_condition_factor(condition)
            accident_factor = self.get_accident_factor(accident_history)
            
            # Combine factors
            combined = (
                age_factor * mileage_factor * location_factor *
                condition_factor * accident_factor
            )
            
            market_value = base_price * combined
            
            return {
                "variant_id": variant_id,
                "market_value": round(market_value, 2),
                "retail_value": round(market_value * 1.08, 2),
                "trade_value": round(market_value * 0.92, 2),
                "dealer_value": round(market_value * 0.95, 2),
                "confidence_score": 70.0,
                "base_price": base_price,
                "age_factor": age_factor,
                "mileage_factor": mileage_factor,
                "location_factor": location_factor,
                "condition_factor": condition_factor,
                "accident_factor": accident_factor
            }
            
        except Exception as e:
            logger.error(f"Valuation calculation error: {str(e)}")
            raise
