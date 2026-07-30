# app/modules/valuation/service.py
# Auto-D Kenya - Valuation Service
# ================================================================
# TYPE: MODULE - Valuation business logic

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from app.modules.valuation.engine import ValuationEngine
from app.core.database import get_supabase
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class ValuationService:
    """Valuation service for business logic."""
    
    def __init__(self):
        self.engine = ValuationEngine()
        self.supabase = get_supabase()
    
    async def calculate_valuation(
        self,
        variant_id: str,
        year: int,
        mileage: float,
        condition: str = "good",
        accident_history: str = "none",
        location: str = "nairobi",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate vehicle valuation."""
        # Get variant data
        variant = self.supabase.table("vehicle_variants").select("*").eq("variant_id", variant_id).execute()
        if not variant.data:
            raise NotFoundException("Variant not found")
        
        variant_data = variant.data[0]
        
        # Calculate valuation
        result = await self.engine.calculate(
            variant_id=variant_id,
            year=year,
            mileage=mileage,
            condition=condition,
            accident_history=accident_history,
            location=location,
            variant_data=variant_data
        )
        
        # Save to history if user is authenticated
        if user_id:
            try:
                self.supabase.table("valuation_reports").insert({
                    "user_id": user_id,
                    "variant_id": variant_id,
                    "market_value": result["market_value"],
                    "retail_value": result["retail_value"],
                    "trade_value": result["trade_value"],
                    "confidence_score": result["confidence_score"],
                    "year": year,
                    "mileage": mileage,
                    "location": location,
                    "condition": condition,
                    "created_at": datetime.utcnow().isoformat()
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to save valuation history: {str(e)}")
        
        return result
    
    async def get_valuation_history(self, user_id: str) -> list:
        """Get valuation history for a user."""
        try:
            response = self.supabase.table("valuation_reports").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting valuation history: {str(e)}")
            return []
