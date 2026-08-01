# app/modules/valuation/engine.py
# Auto-D Kenya - Valuation Engine
# ================================================================
# TYPE: MODULE - Vehicle valuation calculation engine

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.core.config import settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class ValuationEngine:
    """
    Vehicle valuation calculation engine.
    
    Valuation Hierarchy:
    1. Base Vehicle Price
    2. Age Depreciation (smooth curve)
    3. Mileage Adjustment
    4. Vehicle Condition
    5. Accident History
    6. Market Demand
    7. Brand Retention
    8. Location Adjustment
    9. Fuel Type
    10. Transmission
    11. Body Type
    12. Optional Features
    13. Confidence Calculation
    """

    def __init__(self):
        self.supabase = get_supabase()
        self._cache = {}

    # ─── 1. AGE DEPRECIATION ─────────────────────────────────────

    def calculate_age_factor(self, year: int) -> float:
        """
        Calculate age depreciation factor using a smooth curve.
        
        Year 1: 12%
        Year 2: 10%
        Year 3: 8%
        Year 4-7: 6% per year
        Year 8+: 4% per year
        Minimum retained value: 20%
        """
        age = datetime.now().year - year
        if age <= 0:
            return 1.0
        
        if age == 1:
            depreciation = 0.12
        elif age == 2:
            depreciation = 0.22  # 12 + 10
        elif age == 3:
            depreciation = 0.30  # 12 + 10 + 8
        elif age <= 7:
            depreciation = 0.30 + (age - 3) * 0.06
        else:
            depreciation = 0.54 + (age - 7) * 0.04
        
        # Cap at 80% depreciation (20% retained value)
        depreciation = min(depreciation, 0.80)
        
        return round(1 - depreciation, 3)

    # ─── 2. MILEAGE ADJUSTMENT ──────────────────────────────────

    def calculate_mileage_factor(self, mileage: int, age: int) -> float:
        """
        Calculate mileage adjustment factor.
        
        Expected KM = Vehicle Age × 20,000
        """
        if mileage <= 0 or age <= 0:
            return 1.0
        
        expected_mileage = age * 20000
        ratio = mileage / expected_mileage
        
        # Adjust based on deviation from expected
        if ratio < 0.50:
            factor = 1.04  # Very low mileage
        elif ratio < 0.75:
            factor = 1.02  # Below average
        elif ratio < 0.90:
            factor = 1.01  # Slightly below
        elif ratio < 1.10:
            factor = 1.00  # Normal
        elif ratio < 1.25:
            factor = 0.98  # Slightly above
        elif ratio < 1.50:
            factor = 0.94  # Above average
        elif ratio < 2.00:
            factor = 0.90  # High mileage
        else:
            factor = 0.85  # Very high mileage
        
        return round(factor, 3)

    # ─── 3. CONDITION FACTOR ─────────────────────────────────────

    def get_condition_factor(self, condition: str) -> float:
        """Get vehicle condition adjustment factor."""
        factors = {
            "excellent": 1.08,
            "very_good": 1.04,
            "good": 1.00,
            "fair": 0.92,
            "poor": 0.82
        }
        return factors.get(condition.lower(), 1.00)

    # ─── 4. ACCIDENT HISTORY FACTOR ─────────────────────────────

    def get_accident_factor(self, accident_history: str) -> float:
        """Get accident history adjustment factor."""
        factors = {
            "none": 1.00,
            "minor": 0.97,
            "moderate": 0.92,
            "major": 0.85,
            "structural": 0.70,
            "total_loss": 0.60
        }
        return factors.get(accident_history.lower(), 1.00)

    # ─── 5. MARKET DEMAND FACTOR ────────────────────────────────

    async def get_market_demand_factor(self, make: str, model: str) -> float:
        """
        Get market demand factor from database.
        Falls back to cache or default.
        """
        cache_key = f"demand_{make}_{model}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            response = self.supabase.table("vehicle_market_demand_profiles").select("*").execute()
            
            if response.data:
                # Find matching profile
                for profile in response.data:
                    if (profile.get("make", "").lower() == make.lower() and 
                        profile.get("model", "").lower() == model.lower()):
                        factor = profile.get("demand_factor", 1.0)
                        self._cache[cache_key] = factor
                        return factor
        except Exception as e:
            logger.warning(f"Market demand lookup failed: {e}")
        
        # Default demand factor based on brand popularity
        default_factors = {
            "toyota": 1.08,
            "lexus": 1.06,
            "mazda": 1.02,
            "subaru": 1.01,
            "honda": 1.04,
            "nissan": 0.99,
            "mitsubishi": 0.98,
            "volkswagen": 0.96,
            "mercedes": 0.95,
            "bmw": 0.94,
            "audi": 0.93,
            "ford": 0.92,
            "peugeot": 0.90,
            "chevrolet": 0.88,
            "land_rover": 0.85,
            "jeep": 0.84,
            "other": 0.95
        }
        
        factor = default_factors.get(make.lower(), 0.95)
        self._cache[cache_key] = factor
        return factor

    # ─── 6. BRAND RETENTION FACTOR ──────────────────────────────

    def get_brand_factor(self, make: str) -> float:
        """Get brand retention factor."""
        factors = {
            "toyota": 1.03,
            "lexus": 1.02,
            "mazda": 1.02,
            "subaru": 1.01,
            "honda": 1.02,
            "nissan": 0.99,
            "mitsubishi": 0.98,
            "volkswagen": 0.96,
            "mercedes": 0.95,
            "bmw": 0.94,
            "audi": 0.93,
            "ford": 0.92,
            "peugeot": 0.90,
            "chevrolet": 0.88,
            "land_rover": 0.85,
            "jeep": 0.84,
            "other": 0.95
        }
        return factors.get(make.lower(), 0.95)

    # ─── 7. LOCATION FACTOR ──────────────────────────────────────

    def get_location_factor(self, location: str) -> float:
        """Get location adjustment factor."""
        factors = {
            "nairobi": 1.05,
            "mombasa": 1.02,
            "kisumu": 1.00,
            "nakuru": 1.00,
            "eldoret": 1.00,
            "thika": 1.00,
            "kiambu": 1.02,
            "kajiado": 1.00,
            "machakos": 1.00,
            "meru": 0.98,
            "nyeri": 0.98,
            "embu": 0.97,
            "malindi": 1.02,
            "nanyuki": 1.01,
            "other": 1.00
        }
        return factors.get(location.lower(), 1.00)

    # ─── 8. FUEL TYPE FACTOR ─────────────────────────────────────

    def get_fuel_factor(self, fuel_type: str) -> float:
        """Get fuel type adjustment factor."""
        factors = {
            "petrol": 1.00,
            "diesel": 1.02,
            "hybrid": 1.05,
            "electric": 1.08,
            "lpg": 0.97,
            "cng": 0.96
        }
        return factors.get(fuel_type.lower(), 1.00)

    # ─── 9. TRANSMISSION FACTOR ──────────────────────────────────

    def get_transmission_factor(self, transmission: str) -> float:
        """Get transmission type adjustment factor."""
        factors = {
            "automatic": 1.02,
            "cvt": 1.01,
            "manual": 1.00,
            "semi_automatic": 1.01,
            "dual_clutch": 1.02
        }
        return factors.get(transmission.lower().replace(" ", "_"), 1.00)

    # ─── 10. BODY TYPE FACTOR ────────────────────────────────────

    def get_body_type_factor(self, body_type: str) -> float:
        """Get body type adjustment factor."""
        factors = {
            "suv": 1.03,
            "pickup": 1.05,
            "mpv": 1.01,
            "sedan": 1.00,
            "hatchback": 0.98,
            "coupe": 0.97,
            "convertible": 0.95,
            "wagon": 0.97,
            "van": 0.98,
            "truck": 1.02,
            "bus": 0.99,
            "motorcycle": 0.80
        }
        return factors.get(body_type.lower(), 1.00)

    # ─── 11. OPTIONAL FEATURES ────────────────────────────────────

    def calculate_features_bonus(self, features: Optional[List[str]] = None) -> float:
        """
        Calculate bonus for optional features.
        Maximum bonus capped at 5%.
        """
        if not features:
            return 1.00
        
        feature_bonuses = {
            "leather_seats": 0.008,
            "sunroof": 0.005,
            "navigation": 0.004,
            "alloy_wheels": 0.006,
            "safety_package": 0.010,
            "premium_sound": 0.004,
            "heated_seats": 0.004,
            "parking_sensors": 0.005,
            "reverse_camera": 0.006,
            "apple_carplay": 0.003,
            "android_auto": 0.003,
            "adaptive_cruise": 0.008,
            "lane_assist": 0.006,
            "blind_spot": 0.005,
            "premium_paint": 0.004
        }
        
        total_bonus = 0.0
        for feature in features:
            key = feature.lower().replace(" ", "_")
            total_bonus += feature_bonuses.get(key, 0.0)
        
        # Cap at 5%
        total_bonus = min(total_bonus, 0.05)
        
        return 1.00 + total_bonus

    # ─── 12. BASE PRICE ───────────────────────────────────────────

    async def get_base_price(self, variant_id: int) -> float:
        """Get base price from database with fallback."""
        default_price = getattr(settings, "DEFAULT_BASE_PRICE", 2500000.0)
        
        try:
            # Try vehicle_variants table
            response = self.supabase.table("vehicle_variants").select("*").eq("id", variant_id).execute()
            
            if response.data:
                price = response.data[0].get("base_price")
                if price:
                    return float(price)
            
            # Try market_prices table
            market = self.supabase.table("market_prices").select("avg_price").eq("variant_id", variant_id).execute()
            if market.data:
                price = market.data[0].get("avg_price")
                if price:
                    return float(price)
            
        except Exception as e:
            logger.error(f"Base price lookup failed: {e}")
        
        return float(default_price)

    # ─── 13. CONFIDENCE SCORE ─────────────────────────────────────

    def calculate_confidence_score(self, data_quality: Dict[str, bool]) -> int:
        """
        Calculate confidence score based on data quality.
        """
        weights = {
            "base_price_available": 15,
            "specifications_complete": 15,
            "market_demand_found": 10,
            "mileage_supplied": 10,
            "year_supplied": 10,
            "condition_supplied": 10,
            "location_supplied": 5,
            "comparable_pricing": 15,
            "adjustments_complete": 10
        }
        
        total_weight = sum(weights.values())
        achieved_weight = 0
        
        for key, available in data_quality.items():
            if available:
                achieved_weight += weights.get(key, 0)
        
        # Base confidence
        confidence = (achieved_weight / total_weight) * 100
        
        # Minimum confidence
        confidence = max(confidence, 30.0)
        
        return round(confidence)

    # ─── 14. VALUE RANGE ──────────────────────────────────────────

    def calculate_value_range(self, value: float, confidence: int) -> Dict[str, float]:
        """
        Calculate value range based on confidence score.
        Higher confidence = narrower range.
        """
        if confidence >= 85:
            spread = 0.05  # ±5%
        elif confidence >= 70:
            spread = 0.08  # ±8%
        elif confidence >= 50:
            spread = 0.12  # ±12%
        else:
            spread = 0.18  # ±18%
        
        return {
            "minimum": round(value * (1 - spread), 2),
            "maximum": round(value * (1 + spread), 2)
        }

    # ─── 15. AI EXPLANATION ──────────────────────────────────────

    def generate_explanation(self, factors: Dict[str, float], confidence: int) -> str:
        """
        Generate human-readable explanation of the valuation.
        """
        parts = []
        
        # Age
        age_factor = factors.get("age_factor", 1.0)
        if age_factor < 0.6:
            parts.append("significant age depreciation")
        elif age_factor < 0.8:
            parts.append("moderate age depreciation")
        elif age_factor < 0.95:
            parts.append("slight age depreciation")
        else:
            parts.append("minimal age depreciation")
        
        # Mileage
        mileage_factor = factors.get("mileage_factor", 1.0)
        if mileage_factor > 1.02:
            parts.append("below-average mileage")
        elif mileage_factor < 0.95:
            parts.append("above-average mileage")
        
        # Condition
        condition_factor = factors.get("condition_factor", 1.0)
        if condition_factor >= 1.04:
            parts.append("excellent overall condition")
        elif condition_factor >= 1.0:
            parts.append("good condition")
        elif condition_factor >= 0.92:
            parts.append("fair condition")
        else:
            parts.append("below-average condition")
        
        # Market demand
        demand_factor = factors.get("demand_factor", 1.0)
        if demand_factor >= 1.03:
            parts.append("strong market demand")
        elif demand_factor <= 0.95:
            parts.append("weaker market demand")
        
        # Brand
        brand_factor = factors.get("brand_factor", 1.0)
        if brand_factor >= 1.02:
            parts.append("strong brand value retention")
        elif brand_factor <= 0.95:
            parts.append("lower brand value retention")
        
        # Location
        location_factor = factors.get("location_factor", 1.0)
        if location_factor > 1.02:
            parts.append("premium location")
        elif location_factor < 0.98:
            parts.append("location-adjusted value")
        
        # Build explanation
        if parts:
            explanation = f"The estimated value is primarily influenced by the vehicle's {', '.join(parts)}."
        else:
            explanation = "The vehicle valuation is based on standard market factors."
        
        # Add confidence note
        if confidence >= 85:
            explanation += " High confidence in this estimate due to complete and reliable data."
        elif confidence >= 70:
            explanation += " Good confidence in this estimate."
        elif confidence >= 50:
            explanation += " Moderate confidence — more data would improve accuracy."
        else:
            explanation += " Limited data available — consider this an indicative estimate."
        
        return explanation

    # ─── MAIN CALCULATION ──────────────────────────────────────────

    async def calculate(
        self,
        variant_id: int,
        year: int,
        mileage: int,
        condition: str = "good",
        accident_history: str = "none",
        location: str = "nairobi",
        variant_data: Optional[Dict] = None,
        features: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calculate vehicle valuation using the complete hierarchy.
        """
        try:
            # ─── Get variant data ──────────────────────────────────
            if variant_data:
                make = variant_data.get("make_name", "Unknown")
                model = variant_data.get("model_name", "Unknown")
                fuel_type = variant_data.get("fuel_type_name", "petrol")
                transmission = variant_data.get("transmission_type_name", "manual")
                body_type = variant_data.get("body_type_name", "sedan")
            else:
                response = self.supabase.table("vehicle_variants").select("*").eq("id", variant_id).execute()
                if response.data:
                    data = response.data[0]
                    make = data.get("make_name", "Unknown")
                    model = data.get("model_name", "Unknown")
                    fuel_type = data.get("fuel_type_name", "petrol")
                    transmission = data.get("transmission_type_name", "manual")
                    body_type = data.get("body_type_name", "sedan")
                else:
                    make = "Unknown"
                    model = "Unknown"
                    fuel_type = "petrol"
                    transmission = "manual"
                    body_type = "sedan"
            
            age = max(0, datetime.now().year - year)
            
            # ─── 1. Get base price ─────────────────────────────────
            if variant_data and variant_data.get("base_price"):
                base_price = float(variant_data["base_price"])
            else:
                base_price = await self.get_base_price(variant_id)
            
            # ─── 2. Calculate all factors ──────────────────────────
            age_factor = self.calculate_age_factor(year)
            mileage_factor = self.calculate_mileage_factor(mileage, age)
            condition_factor = self.get_condition_factor(condition)
            accident_factor = self.get_accident_factor(accident_history)
            demand_factor = await self.get_market_demand_factor(make, model)
            brand_factor = self.get_brand_factor(make)
            location_factor = self.get_location_factor(location)
            fuel_factor = self.get_fuel_factor(fuel_type)
            transmission_factor = self.get_transmission_factor(transmission)
            body_type_factor = self.get_body_type_factor(body_type)
            features_factor = self.calculate_features_bonus(features)
            
            # ─── 3. Apply all factors sequentially ──────────────────
            estimated_value = base_price
            estimated_value *= age_factor
            estimated_value *= mileage_factor
            estimated_value *= condition_factor
            estimated_value *= accident_factor
            estimated_value *= demand_factor
            estimated_value *= brand_factor
            estimated_value *= location_factor
            estimated_value *= fuel_factor
            estimated_value *= transmission_factor
            estimated_value *= body_type_factor
            estimated_value *= features_factor
            
            # ─── 4. Calculate derived values ────────────────────────
            dealer_value = estimated_value * 0.92
            trade_value = estimated_value * 0.85
            insurance_value = estimated_value * 1.05
            private_sale_value = estimated_value * 1.10
            
            # ─── 5. Data quality for confidence ──────────────────────
            data_quality = {
                "base_price_available": base_price > 0,
                "specifications_complete": all([make != "Unknown", model != "Unknown"]),
                "market_demand_found": demand_factor != 1.0,
                "mileage_supplied": mileage > 0,
                "year_supplied": year > 1900,
                "condition_supplied": condition != "good",
                "location_supplied": location != "nairobi",
                "comparable_pricing": await self._has_comparable_pricing(variant_id),
                "adjustments_complete": True
            }
            
            confidence = self.calculate_confidence_score(data_quality)
            
            # ─── 6. Value range ──────────────────────────────────────
            value_range = self.calculate_value_range(estimated_value, confidence)
            
            # ─── 7. AI Explanation ───────────────────────────────────
            factors = {
                "age_factor": age_factor,
                "mileage_factor": mileage_factor,
                "condition_factor": condition_factor,
                "accident_factor": accident_factor,
                "demand_factor": demand_factor,
                "brand_factor": brand_factor,
                "location_factor": location_factor,
                "fuel_factor": fuel_factor,
                "transmission_factor": transmission_factor,
                "body_type_factor": body_type_factor,
                "features_factor": features_factor
            }
            explanation = self.generate_explanation(factors, confidence)
            
            # ─── 8. Build response ───────────────────────────────────
            return {
                "variant_id": variant_id,
                "currency": "KES",
                
                # Valuation results
                "market_value": round(estimated_value, 2),
                "estimated_vehicle_value": round(estimated_value, 2),
                "retail_value": round(estimated_value * 1.08, 2),
                "trade_value": round(trade_value, 2),
                "dealer_value": round(dealer_value, 2),
                "insurance_value": round(insurance_value, 2),
                "private_sale_value": round(private_sale_value, 2),
                
                # Value range
                "estimated_value_range": value_range,
                
                # Confidence
                "confidence_score": confidence,
                
                # All factors for transparency
                "base_price": base_price,
                "age_factor": age_factor,
                "mileage_factor": mileage_factor,
                "condition_factor": condition_factor,
                "accident_factor": accident_factor,
                "demand_factor": demand_factor,
                "brand_factor": brand_factor,
                "location_factor": location_factor,
                "fuel_factor": fuel_factor,
                "transmission_factor": transmission_factor,
                "body_type_factor": body_type_factor,
                "features_factor": features_factor,
                
                # Combined factor (for reference)
                "total_factor": round(
                    age_factor * mileage_factor * condition_factor * accident_factor *
                    demand_factor * brand_factor * location_factor * fuel_factor *
                    transmission_factor * body_type_factor * features_factor,
                    3
                ),
                
                # AI Explanation
                "explanation": explanation,
                
                # Data quality
                "data_quality": data_quality
            }
            
        except Exception as e:
            logger.exception(f"Valuation calculation failed: {e}")
            raise

    # ─── HELPER METHODS ────────────────────────────────────────────

    async def _has_comparable_pricing(self, variant_id: int) -> bool:
        """Check if comparable pricing data exists."""
        try:
            response = self.supabase.table("market_prices").select("count", count="exact").eq("variant_id", variant_id).execute()
            return response.count > 0 if hasattr(response, 'count') else False
        except Exception:
            return False
