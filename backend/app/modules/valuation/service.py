# app/modules/valuation/service.py
# Auto-D Kenya - Valuation Service
# ================================================================
# TYPE: MODULE - Valuation business logic

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import secrets

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
        variant_id: int,
        year: int,
        mileage: int,
        condition: str = "good",
        accident_history: str = "none",
        location: str = "nairobi",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate vehicle valuation.
        
        Args:
            variant_id: Vehicle variant ID (integer from vehicle_variants.id)
            year: Vehicle year of manufacture
            mileage: Odometer reading in km
            condition: Vehicle condition (excellent, good, fair, poor)
            accident_history: Accident history (none, minor, major, total_loss)
            location: Vehicle location (city/county)
            user_id: Optional user ID for saving history
            
        Returns:
            Dict[str, Any]: Complete valuation report with metadata
        """
        # Validate variant_id
        if not variant_id or variant_id <= 0:
            raise NotFoundException("Valid variant ID required")
        
        # Normalize condition
        condition = condition.lower() if condition else "good"
        allowed_conditions = ["excellent", "very_good", "good", "fair", "poor"]
        if condition not in allowed_conditions:
            logger.warning(f"Unknown condition '{condition}', defaulting to 'good'")
            condition = "good"
        
        # Normalize location
        location = location.lower() if location else "nairobi"
        
        # Get variant data
        try:
            variant_response = self.supabase.table("vehicle_variants").select("*").eq("id", variant_id).execute()
            
            if not variant_response.data:
                raise NotFoundException(f"Variant with ID {variant_id} not found")
            
            variant_data = variant_response.data[0]
            logger.info(f"Found variant: {variant_data.get('name', 'Unknown')} (ID: {variant_id})")
            
        except Exception as e:
            logger.error(f"Error fetching variant {variant_id}: {str(e)}")
            raise NotFoundException(f"Failed to fetch variant: {str(e)}")
        
        # Calculate valuation
        try:
            result = await self.engine.calculate(
                variant_id=variant_id,
                year=year,
                mileage=mileage,
                condition=condition,
                accident_history=accident_history,
                location=location,
                variant_data=variant_data
            )
        except Exception as e:
            logger.error(f"Valuation engine error: {str(e)}")
            raise
        
        # Safely get values with fallbacks
        market_value = result.get("market_value", 0)
        retail_value = result.get("retail_value", 0)
        trade_value = result.get("trade_value", 0)
        confidence_score = result.get("confidence_score", 50)
        adjustments = result.get("adjustments", {})
        
        # Ensure we have at least some value
        if market_value == 0 and retail_value == 0 and trade_value == 0:
            logger.warning(f"Valuation returned all zeros for variant {variant_id}")
            fallback_value = self._estimate_fallback_value(variant_data, year, mileage)
            market_value = fallback_value
            retail_value = fallback_value * 1.08
            trade_value = fallback_value * 0.85
            confidence_score = 30
        
        # Generate report number
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_suffix = secrets.token_hex(4).upper()
        report_number = f"AUTO-VAL-{timestamp}-{random_suffix}"
        
        # ─── BUILD COMPLETE RESPONSE ──────────────────────────────────
        
        # 1. Report Metadata
        report = {
            "title": "AUTO-D Vehicle Valuation Report",
            "report_number": report_number,
            "generated_at": datetime.utcnow().isoformat(),
            "status": "Completed",
            "version": "1.0"
        }
        
        # 2. Vehicle Information
        vehicle = {
            "variant_id": variant_id,
            "variant_name": variant_data.get("name", "Unknown"),
            "make": variant_data.get("make_name", "Unknown"),
            "model": variant_data.get("model_name", "Unknown"),
            "year": year,
            "mileage": mileage,
            "condition": condition.title(),
            "location": location.title(),
            "fuel_type": variant_data.get("fuel_type_name", "Unknown"),
            "transmission": variant_data.get("transmission_type_name", "Unknown"),
            "engine_size_cc": variant_data.get("engine_size_cc", 0),
            "body_type": variant_data.get("body_type_name", "Unknown")
        }
        
        # 3. Valuation Results
        estimated_value_range = {
            "minimum": round(market_value * 0.95, 2),
            "maximum": round(market_value * 1.05, 2)
        }
        
        valuation = {
            "estimated_vehicle_value": round(market_value, 2),
            "retail_value": round(retail_value, 2),
            "trade_value": round(trade_value, 2),
            "dealer_value": round(result.get("dealer_value", retail_value * 0.95), 2),
            "currency": "KES",
            "confidence_score": confidence_score,
            "estimated_value_range": estimated_value_range
        }
        
        # 4. Analysis
        valuation_methodology = [
            "Vehicle age ({})".format(year),
            "Mileage ({:,} km)".format(mileage),
            "Vehicle condition ({})".format(condition.title()),
            "Vehicle specifications",
            "Location ({})".format(location.title()),
            "Depreciation model",
            "Market comparables analysis"
        ]
        
        analysis = {
            "valuation_methodology": valuation_methodology,
            "adjustments": adjustments,
            "engine_version": "AUTO-D AI Valuation Engine v1.2"
        }
        
        # 5. Disclaimer
        disclaimer = (
            "This valuation is generated using the AUTO-D vehicle valuation model. "
            "It represents an indicative estimate based on vehicle specifications, "
            "age, mileage, condition, depreciation modelling and regional factors. "
            "It should not be interpreted as the current market asking price, "
            "dealer retail price, trade-in value or guaranteed selling price. "
            "Actual transaction values may vary depending on inspection results, "
            "ownership history, maintenance records and prevailing market conditions."
        )
        
        # ─── BUILD FINAL RESPONSE ─────────────────────────────────────
        safe_result = {
            "report": report,
            "vehicle": vehicle,
            "valuation": valuation,
            "analysis": analysis,
            "disclaimer": disclaimer
        }
        
        # Save to history if user is authenticated
        if user_id:
            try:
                history_data = {
                    "user_id": user_id,
                    "variant_id": variant_id,
                    "market_value": market_value,
                    "retail_value": retail_value,
                    "trade_value": trade_value,
                    "confidence_score": confidence_score,
                    "report_number": report_number,
                    "year": year,
                    "mileage": mileage,
                    "location": location,
                    "condition": condition,
                    "accident_history": accident_history,
                    "created_at": datetime.utcnow().isoformat()
                }
                
                # Handle potential missing columns gracefully
                try:
                    self.supabase.table("valuation_reports").insert(history_data).execute()
                    logger.info(f"Valuation history saved for user {user_id}")
                except Exception as e:
                    # Try without optional columns if they don't exist
                    if "accident_history" in str(e) or "location" in str(e) or "report_number" in str(e):
                        safe_history = {k: v for k, v in history_data.items() 
                                      if k not in ["accident_history", "location", "report_number"]}
                        self.supabase.table("valuation_reports").insert(safe_history).execute()
                        logger.info(f"Valuation history saved (without optional fields) for user {user_id}")
                    else:
                        raise
                        
            except Exception as e:
                logger.warning(f"Failed to save valuation history: {str(e)}")
        
        logger.info(f"Valuation report {report_number} generated for variant {variant_id}")
        return safe_result
    
    def _estimate_fallback_value(self, variant_data: Dict[str, Any], year: int, mileage: int) -> float:
        """
        Estimate a fallback value when the engine returns zeros.
        
        Args:
            variant_data: Variant data from database
            year: Vehicle year
            mileage: Odometer reading
            
        Returns:
            float: Estimated value
        """
        try:
            # Get base price from variant or use default
            base_price = variant_data.get("base_price") or variant_data.get("price") or variant_data.get("market_value") or 2500000
            
            # Calculate age depreciation
            current_year = datetime.now().year
            age = max(0, current_year - year)
            
            # Depreciation rates by age (Kenya market)
            if age <= 1:
                dep_rate = 0.10
            elif age <= 3:
                dep_rate = 0.20 + (age - 1) * 0.05
            elif age <= 5:
                dep_rate = 0.35 + (age - 3) * 0.04
            elif age <= 8:
                dep_rate = 0.50 + (age - 5) * 0.03
            else:
                dep_rate = 0.70 + min(age - 8, 5) * 0.02
            
            # Cap depreciation
            dep_rate = min(dep_rate, 0.85)
            
            # Apply depreciation
            value = base_price * (1 - dep_rate)
            
            # Mileage adjustment (if mileage is very high)
            if mileage > 50000:
                mileage_penalty = min((mileage - 50000) / 50000 * 0.05, 0.20)
                value = value * (1 - mileage_penalty)
            
            # Ensure minimum value (15% of base)
            value = max(value, base_price * 0.15)
            
            logger.info(f"Fallback value calculation: base={base_price}, age={age}, dep_rate={dep_rate}, value={value}")
            return round(value, 2)
            
        except Exception as e:
            logger.warning(f"Fallback value calculation failed: {str(e)}")
            return 2500000.0
    
    async def get_valuation_history(self, user_id: str) -> list:
        """
        Get valuation history for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            list: List of valuation reports
        """
        try:
            response = self.supabase.table("valuation_reports").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting valuation history: {str(e)}")
            return []
    
    async def get_valuation_by_id(self, report_id: int, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific valuation report by ID.
        
        Args:
            report_id: Report ID
            user_id: User ID for authorization
            
        Returns:
            Optional[Dict[str, Any]]: Valuation report or None
        """
        try:
            response = self.supabase.table("valuation_reports").select("*").eq("id", report_id).eq("user_id", user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting valuation {report_id}: {str(e)}")
            return None
    
    async def get_valuation_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get valuation statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict[str, Any]: Statistics
        """
        try:
            history = await self.get_valuation_history(user_id)
            
            if not history:
                return {
                    "total_valuations": 0,
                    "average_value": 0,
                    "highest_value": 0,
                    "lowest_value": 0,
                    "last_valuation": None
                }
            
            values = [h.get("market_value", 0) for h in history if h.get("market_value", 0) > 0]
            
            return {
                "total_valuations": len(history),
                "average_value": sum(values) / len(values) if values else 0,
                "highest_value": max(values) if values else 0,
                "lowest_value": min(values) if values else 0,
                "last_valuation": history[0].get("created_at") if history else None
            }
            
        except Exception as e:
            logger.error(f"Error getting valuation stats: {str(e)}")
            return {
                "total_valuations": 0,
                "average_value": 0,
                "highest_value": 0,
                "lowest_value": 0,
                "last_valuation": None
            }


# ─── RESPONSE SCHEMA FOR REFERENCE ──────────────────────────────────

"""
VALUATION RESPONSE STRUCTURE:

{
    "report": {
        "title": "AUTO-D Vehicle Valuation Report",
        "report_number": "AUTO-VAL-20260101120000-ABCD",
        "generated_at": "2026-01-01T12:00:00.000Z",
        "status": "Completed",
        "version": "1.0"
    },
    
    "vehicle": {
        "variant_id": 123,
        "variant_name": "Prado VX",
        "make": "Toyota",
        "model": "Land Cruiser Prado",
        "year": 2020,
        "mileage": 50000,
        "condition": "Good",
        "location": "Nairobi",
        "fuel_type": "Petrol",
        "transmission": "Automatic",
        "engine_size_cc": 4000,
        "body_type": "SUV"
    },
    
    "valuation": {
        "estimated_vehicle_value": 5250000.00,
        "retail_value": 5670000.00,
        "trade_value": 4462500.00,
        "dealer_value": 5386500.00,
        "currency": "KES",
        "confidence_score": 85,
        "estimated_value_range": {
            "minimum": 4987500.00,
            "maximum": 5512500.00
        }
    },
    
    "analysis": {
        "valuation_methodology": [
            "Vehicle age (2020)",
            "Mileage (50,000 km)",
            "Vehicle condition (Good)",
            "Vehicle specifications",
            "Location (Nairobi)",
            "Depreciation model",
            "Market comparables analysis"
        ],
        "adjustments": {
            "age": 0.95,
            "mileage": 0.98,
            "condition": 1.05,
            "location": 1.02
        },
        "engine_version": "AUTO-D AI Valuation Engine v1.2"
    },
    
    "disclaimer": "This valuation is generated using the AUTO-D vehicle valuation model. It represents an indicative estimate based on vehicle specifications, age, mileage, condition, depreciation modelling and regional factors. It should not be interpreted as the current market asking price, dealer retail price, trade-in value or guaranteed selling price. Actual transaction values may vary depending on inspection results, ownership history, maintenance records and prevailing market conditions."
}
"""
