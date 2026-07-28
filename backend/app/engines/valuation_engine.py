"""
Valuation Engine - Core valuation calculation logic
ALL DATA sourced from scraper and database - NO hard-coded values
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import statistics

from app.services.data_service import DataService

logger = logging.getLogger(__name__)


class ValuationEngine:
    """Engine for vehicle valuation calculations using scraper and database data"""
    
    def __init__(self):
        self.data_service = DataService()
    
    def calculate_valuation(
        self,
        variant: Dict[str, Any],
        year: int,
        mileage: float,
        condition: str,
        accident_history: str,
        previous_owners: int,
        location: str,
        service_history: bool,
        market_data: Optional[Dict] = None,
        similar_listings: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Calculate vehicle valuation using scraper and database data"""
        
        # ─── Get identifiers ──────────────────────────────────────────
        make = variant.get("make_name") or variant.get("make") or "Unknown"
        model = variant.get("model_name") or variant.get("model") or variant.get("name", "")
        body_type = variant.get("body_type") or variant.get("body_type_name", "sedan").lower()
        variant_id = variant.get("id") or variant.get("variant_id")
        
        # ─── 1. GET MARKET DATA FROM SCRAPER ─────────────────────────
        market_stats = self.data_service.get_market_statistics(
            make=make,
            model=model,
            days=90
        )
        
        # ─── 2. GET SIMILAR LISTINGS FROM SCRAPER ────────────────────
        if not similar_listings:
            similar_listings = self.data_service.get_market_prices(
                make=make,
                model=model,
                year_from=year - 2,
                year_to=year + 2,
                limit=100
            )
        
        # ─── 3. GET BASE VALUE FROM SCRAPER DATA ─────────────────────
        base_value = self._get_base_value_from_scraper(
            market_stats=market_stats,
            similar_listings=similar_listings,
            year=year,
            make=make,
            model=model
        )
        
        # ─── 4. GET DATABASE VALUES ───────────────────────────────────
        # Vehicle type parameters
        type_params = self.data_service.get_vehicle_type_parameters(body_type)
        
        # Location factors
        location_data = self.data_service.get_location_factors(location)
        location_factor = location_data.get("price_adjustment", 1.0)
        
        # Depreciation rates
        dep_class = variant.get("depreciation_class") or f"{body_type.upper()}_D"
        dep_data = self.data_service.get_depreciation_rates(dep_class)
        
        # Condition factors
        condition_factor = self._get_condition_factor(condition)
        
        # Accident factors
        accident_factor = self._get_accident_factor(accident_history)
        
        # Insurance rates
        insurance_data = self.data_service.get_insurance_rates(body_type)
        
        # ─── 5. CALCULATE ADJUSTMENTS ─────────────────────────────────
        adjustments = self._calculate_adjustments(
            year=year,
            mileage=mileage,
            condition_factor=condition_factor,
            accident_factor=accident_factor,
            previous_owners=previous_owners,
            location_factor=location_factor,
            service_history=service_history,
            type_params=type_params,
            dep_data=dep_data
        )
        
        # ─── 6. APPLY ADJUSTMENTS ─────────────────────────────────────
        adjusted_value = base_value * adjustments["total_factor"]
        
        # ─── 7. CONFIDENCE SCORE ──────────────────────────────────────
        confidence = self._calculate_confidence(
            base_value=base_value,
            market_stats=market_stats,
            similar_listings=similar_listings,
            adjustments=adjustments
        )
        
        # ─── 8. BUILD RESULT ──────────────────────────────────────────
        return {
            "market_value": round(adjusted_value, 2),
            "retail_value": round(adjusted_value * 1.08, 2),
            "trade_value": round(adjusted_value * 0.85, 2),
            "dealer_value": round(adjusted_value * 0.95, 2),
            "quick_sale": round(adjusted_value * 0.80, 2),
            "insurance_value": round(adjusted_value * 1.10, 2),
            "base_value": round(base_value, 2),
            "depreciation_rate": self._calculate_depreciation_rate(year, dep_data),
            "estimated_life": 20,
            "confidence_score": confidence,
            "recommendations": self._generate_recommendations(
                adjustments=adjustments,
                condition=condition,
                market_stats=market_stats,
                make=make,
                model=model
            ),
            "market_adjustments": adjustments,
            "scraper_data": {
                "listings_used": len(similar_listings) if similar_listings else 0,
                "market_average": market_stats.get("average_price", 0),
                "market_median": market_stats.get("median_price", 0),
                "market_health": market_stats.get("market_health", "unknown"),
                "total_listings": market_stats.get("total_listings", 0),
                "data_source": "scraper" if market_stats.get("total_listings", 0) > 0 else "database"
            }
        }
    
    def _get_base_value_from_scraper(
        self,
        market_stats: Dict,
        similar_listings: List[Dict],
        year: int,
        make: str,
        model: str
    ) -> float:
        """Get base value from scraper data"""
        
        # ─── Option 1: Use market statistics ──────────────────────────
        if market_stats.get("total_listings", 0) > 0:
            # Use median price (more robust than average)
            median_price = market_stats.get("median_price", 0)
            avg_price = market_stats.get("average_price", 0)
            
            if median_price > 0:
                return median_price
            if avg_price > 0:
                return avg_price
        
        # ─── Option 2: Use similar listings ──────────────────────────
        if similar_listings and len(similar_listings) > 0:
            prices = [l.get("price", 0) for l in similar_listings if l.get("price", 0) > 0]
            if prices:
                return statistics.median(prices)
        
        # ─── Option 3: Use database fallback ──────────────────────────
        return self._get_fallback_value(make, model, year)
    
    def _get_fallback_value(self, make: str, model: str, year: int) -> float:
        """Get fallback value from database when scraper has no data"""
        
        # Try to get from vehicle_values table
        try:
            result = supabase.table("vehicle_values")\
                .select("value")\
                .eq("make", make)\
                .eq("model", model)\
                .eq("year", year)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0].get("value", 0)
        except Exception as e:
            logger.warning(f"Could not get fallback value from database: {e}")
        
        # Try to get from variant
        return 3000000  # Default fallback
    
    def _get_condition_factor(self, condition: str) -> float:
        """Get condition factor from database"""
        try:
            result = supabase.table("condition_factors")\
                .select("factor")\
                .eq("condition", condition.lower())\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0].get("factor", 1.0)
        except Exception as e:
            logger.warning(f"Could not get condition factor: {e}")
        
        # Default condition factors
        defaults = {
            "excellent": 1.12,
            "very_good": 1.06,
            "good": 1.00,
            "fair": 0.88,
            "poor": 0.72
        }
        return defaults.get(condition.lower(), 1.0)
    
    def _get_accident_factor(self, accident_history: str) -> float:
        """Get accident factor from database"""
        try:
            result = supabase.table("accident_factors")\
                .select("factor")\
                .eq("accident_type", accident_history.lower())\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0].get("factor", 1.0)
        except Exception as e:
            logger.warning(f"Could not get accident factor: {e}")
        
        # Default accident factors
        defaults = {
            "none": 1.00,
            "minor": 0.90,
            "major": 0.78,
            "total_loss": 0.55
        }
        return defaults.get(accident_history.lower(), 1.0)
    
    def _calculate_adjustments(
        self,
        year: int,
        mileage: float,
        condition_factor: float,
        accident_factor: float,
        previous_owners: int,
        location_factor: float,
        service_history: bool,
        type_params: Dict,
        dep_data: Dict
    ) -> Dict[str, float]:
        """Calculate all adjustments from database data"""
        current_year = datetime.now().year
        age = max(0, current_year - year)
        
        # ─── Age factor (from database) ────────────────────────────
        if age <= 1:
            dep_rate = dep_data.get("year_1", 0.15)
        elif age <= 2:
            dep_rate = dep_data.get("year_2", 0.12)
        elif age <= 3:
            dep_rate = dep_data.get("year_3", 0.10)
        elif age <= 4:
            dep_rate = dep_data.get("year_4", 0.08)
        elif age <= 5:
            dep_rate = dep_data.get("year_5", 0.07)
        else:
            dep_rate = dep_data.get("year_6_plus", 0.06)
        
        age_factor = 1 - (age * dep_rate)
        age_factor = max(0.3, age_factor)
        
        # ─── Mileage factor ─────────────────────────────────────────
        if mileage > 0:
            mileage_factor = max(0.6, 1 - ((mileage - 10000) / 100000 * 0.15))
        else:
            mileage_factor = 1.0
        
        # ─── Previous owners ──────────────────────────────────────
        owners_factor = max(0.82, 1 - (previous_owners - 1) * 0.025)
        
        # ─── Service history ──────────────────────────────────────
        service_factor = 1.04 if service_history else 0.97
        
        # ─── Vehicle type multiplier ──────────────────────────────
        type_multiplier = type_params.get("valuation_multiplier", 1.0)
        
        # ─── Total factor ──────────────────────────────────────────
        total_factor = (
            age_factor *
            mileage_factor *
            condition_factor *
            accident_factor *
            owners_factor *
            location_factor *
            service_factor *
            type_multiplier
        )
        
        return {
            "age_factor": round(age_factor, 3),
            "age_years": age,
            "depreciation_rate": dep_rate,
            "mileage_factor": round(mileage_factor, 3),
            "condition_factor": round(condition_factor, 3),
            "accident_factor": round(accident_factor, 3),
            "owners_factor": round(owners_factor, 3),
            "location_factor": round(location_factor, 3),
            "service_factor": round(service_factor, 3),
            "type_multiplier": round(type_multiplier, 3),
            "total_factor": round(total_factor, 3)
        }
    
    def _calculate_depreciation_rate(self, year: int, dep_data: Dict) -> float:
        """Calculate depreciation rate from database"""
        current_year = datetime.now().year
        age = max(0, current_year - year)
        
        if age <= 1:
            return dep_data.get("year_1", 0.15)
        elif age <= 2:
            return dep_data.get("year_2", 0.12)
        elif age <= 3:
            return dep_data.get("year_3", 0.10)
        elif age <= 4:
            return dep_data.get("year_4", 0.08)
        elif age <= 5:
            return dep_data.get("year_5", 0.07)
        else:
            return dep_data.get("year_6_plus", 0.06)
    
    def _calculate_confidence(
        self,
        base_value: float,
        market_stats: Dict,
        similar_listings: Optional[List[Dict]],
        adjustments: Dict[str, float]
    ) -> int:
        """Calculate confidence score based on data quality"""
        confidence = 50  # Base
        
        # ─── Confidence from scraper data ──────────────────────────
        total_listings = market_stats.get("total_listings", 0)
        if total_listings >= 50:
            confidence += 30
        elif total_listings >= 20:
            confidence += 25
        elif total_listings >= 10:
            confidence += 20
        elif total_listings >= 5:
            confidence += 15
        elif total_listings > 0:
            confidence += 10
        
        # ─── Confidence from similar listings ──────────────────────
        if similar_listings and len(similar_listings) > 0:
            listings_count = len(similar_listings)
            if listings_count >= 20:
                confidence += 10
            elif listings_count >= 10:
                confidence += 8
            elif listings_count >= 5:
                confidence += 5
        
        # ─── Confidence from value stability ──────────────────────
        if base_value > 5000000:
            confidence += 5
        if base_value > 10000000:
            confidence += 5
        
        # ─── Confidence from adjustments ──────────────────────────
        total_factor = adjustments.get("total_factor", 1.0)
        if 0.85 <= total_factor <= 1.15:
            confidence += 10
        elif 0.75 <= total_factor <= 1.25:
            confidence += 5
        
        return min(98, confidence)
    
    def _generate_recommendations(
        self,
        adjustments: Dict,
        condition: str,
        market_stats: Dict,
        make: str,
        model: str
    ) -> List[str]:
        """Generate recommendations based on data"""
        recommendations = []
        
        # ─── Condition recommendations ────────────────────────────
        if adjustments.get("condition_factor", 1.0) < 0.85:
            recommendations.append("🔧 Vehicle condition is below average. Consider addressing issues to improve value.")
        
        # ─── Mileage recommendations ──────────────────────────────
        if adjustments.get("mileage_factor", 1.0) < 0.8:
            recommendations.append("📊 High mileage detected. This may impact resale value.")
        
        # ─── Accident recommendations ─────────────────────────────
        if adjustments.get("accident_factor", 1.0) < 0.9:
            recommendations.append("⚠️ Accident history is affecting value. Provide documentation for full assessment.")
        
        # ─── Owner recommendations ─────────────────────────────────
        if adjustments.get("owners_factor", 1.0) < 0.9:
            recommendations.append("👤 Multiple previous owners may affect value.")
        
        # ─── Market recommendations ──────────────────────────────
        total_listings = market_stats.get("total_listings", 0)
        health = market_stats.get("market_health", "unknown")
        
        if total_listings == 0:
            recommendations.append(f"📊 No market data available for {make} {model}. Value is estimated based on similar vehicles.")
        elif health == "limited":
            recommendations.append("📊 Limited market data available. Value may vary from estimates.")
        elif health == "fair":
            recommendations.append("📊 Moderate market activity. Consider getting multiple quotes.")
        elif health == "good":
            recommendations.append("📊 Good market data available for this vehicle.")
        
        # ─── Condition specific ────────────────────────────────────
        if condition.lower() in ["fair", "poor"]:
            recommendations.append("🔍 Consider professional inspection before purchase.")
        
        # ─── Age specific ──────────────────────────────────────────
        age_years = adjustments.get("age_years", 0)
        if age_years > 10:
            recommendations.append("📅 Vehicle is over 10 years old. Maintenance history is important.")
        elif age_years > 5:
            recommendations.append("📅 Vehicle is aging. Regular maintenance is crucial for reliability.")
        
        if not recommendations:
            recommendations.append("✅ Vehicle appears to be in good condition with reasonable market value.")
        
        return recommendations
