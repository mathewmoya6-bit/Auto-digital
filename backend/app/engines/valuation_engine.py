"""
Valuation Engine - Core valuation calculation logic with scraper integration
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import statistics
import math

logger = logging.getLogger(__name__)


class ValuationEngine:
    """Engine for vehicle valuation calculations using scraped market data"""
    
    # ─── Real Kenyan Market Values (Fallback when no scraper data) ───
    KENYA_MARKET_VALUES = {
        "Toyota": {
            "Land Cruiser Prado": {
                "2024": {"base": 12000000, "range": [10000000, 14000000]},
                "2023": {"base": 10500000, "range": [9000000, 12000000]},
                "2022": {"base": 9000000, "range": [7500000, 10500000]},
                "2021": {"base": 8000000, "range": [6500000, 9500000]},
                "2020": {"base": 7000000, "range": [5500000, 8500000]},
                "2019": {"base": 6000000, "range": [4500000, 7500000]},
                "2018": {"base": 5000000, "range": [4000000, 6000000]},
            },
            "Land Cruiser": {
                "2024": {"base": 18000000, "range": [15000000, 21000000]},
                "2023": {"base": 16000000, "range": [13000000, 19000000]},
                "2022": {"base": 14000000, "range": [11000000, 17000000]},
            },
            "RAV4": {
                "2024": {"base": 4500000, "range": [3800000, 5200000]},
                "2023": {"base": 4000000, "range": [3300000, 4700000]},
                "2022": {"base": 3500000, "range": [2800000, 4200000]},
                "2021": {"base": 3000000, "range": [2300000, 3700000]},
            },
            "Hilux": {
                "2024": {"base": 6000000, "range": [5000000, 7000000]},
                "2023": {"base": 5500000, "range": [4500000, 6500000]},
                "2022": {"base": 5000000, "range": [4000000, 6000000]},
            },
            "Corolla": {
                "2024": {"base": 2500000, "range": [2000000, 3000000]},
                "2023": {"base": 2200000, "range": [1700000, 2700000]},
            },
            "Camry": {
                "2024": {"base": 3500000, "range": [2800000, 4200000]},
                "2023": {"base": 3000000, "range": [2300000, 3700000]},
            }
        },
        "Subaru": {
            "Forester": {
                "2024": {"base": 5000000, "range": [4200000, 5800000]},
                "2023": {"base": 4500000, "range": [3700000, 5300000]},
                "2022": {"base": 4000000, "range": [3200000, 4800000]},
            },
            "Outback": {
                "2024": {"base": 6000000, "range": [5000000, 7000000]},
                "2023": {"base": 5500000, "range": [4500000, 6500000]},
            },
            "Impreza": {
                "2024": {"base": 3000000, "range": [2500000, 3500000]},
            }
        },
        "Mercedes": {
            "GLE": {
                "2024": {"base": 14000000, "range": [12000000, 16000000]},
                "2023": {"base": 12000000, "range": [10000000, 14000000]},
            },
            "E-Class": {
                "2024": {"base": 10000000, "range": [8000000, 12000000]},
                "2023": {"base": 8500000, "range": [6500000, 10500000]},
            },
            "C-Class": {
                "2024": {"base": 7000000, "range": [6000000, 8000000]},
            }
        },
        "BMW": {
            "X5": {
                "2024": {"base": 12000000, "range": [10000000, 14000000]},
                "2023": {"base": 10000000, "range": [8000000, 12000000]},
            },
            "3 Series": {
                "2024": {"base": 7000000, "range": [6000000, 8000000]},
                "2023": {"base": 6000000, "range": [5000000, 7000000]},
            },
            "5 Series": {
                "2024": {"base": 9000000, "range": [7500000, 10500000]},
            }
        },
        "Nissan": {
            "X-Trail": {
                "2024": {"base": 4000000, "range": [3300000, 4700000]},
                "2023": {"base": 3500000, "range": [2800000, 4200000]},
            },
            "Navara": {
                "2024": {"base": 4500000, "range": [3800000, 5200000]},
            }
        },
        "Mazda": {
            "CX-5": {
                "2024": {"base": 4200000, "range": [3500000, 4900000]},
                "2023": {"base": 3800000, "range": [3100000, 4500000]},
            }
        },
        "Volkswagen": {
            "Tiguan": {
                "2024": {"base": 4500000, "range": [3800000, 5200000]},
                "2023": {"base": 4000000, "range": [3300000, 4700000]},
            },
            "Golf": {
                "2024": {"base": 3000000, "range": [2500000, 3500000]},
            }
        },
        "Ford": {
            "Ranger": {
                "2024": {"base": 5000000, "range": [4200000, 5800000]},
                "2023": {"base": 4500000, "range": [3700000, 5300000]},
            },
            "Explorer": {
                "2024": {"base": 6000000, "range": [5000000, 7000000]},
            }
        }
    }
    
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
        """Calculate vehicle valuation using scraper data"""
        
        # ─── Get make and model ──────────────────────────────────────
        make = variant.get("make_name") or variant.get("make") or "Toyota"
        model = variant.get("model_name") or variant.get("model") or variant.get("name", "")
        
        # ─── Get base value from real market data ──────────────────
        base_value = self._get_market_value(make, model, year)
        
        # ─── Override with similar listings if available ───────────
        if similar_listings and len(similar_listings) > 0:
            listing_prices = [l.get("price", 0) for l in similar_listings if l.get("price", 0) > 0]
            if listing_prices:
                avg_listing_price = statistics.mean(listing_prices)
                # Use scraped data if it's reasonable (within 50% of base)
                if avg_listing_price > base_value * 0.5:
                    base_value = avg_listing_price
                    logger.info(f"Using scraped data: {len(listing_prices)} listings, avg KES {avg_listing_price:,.2f}")
        
        # ─── Apply market adjustments from scraped data ────────────
        market_adjustment = self._get_market_adjustment(market_data)
        base_value = base_value * market_adjustment
        
        # ─── Calculate adjustments ──────────────────────────────────
        adjustments = self._calculate_adjustments(
            year=year,
            mileage=mileage,
            condition=condition,
            accident_history=accident_history,
            previous_owners=previous_owners,
            location=location,
            service_history=service_history
        )
        
        # ─── Calculate final values ────────────────────────────────
        adjusted_value = base_value * adjustments["total_factor"]
        
        # ─── Confidence score from scraper data ────────────────────
        confidence = self._calculate_confidence(
            base_value=base_value,
            similar_listings=similar_listings,
            adjustments=adjustments,
            market_data=market_data
        )
        
        # ─── Build result ──────────────────────────────────────────
        return {
            "market_value": round(adjusted_value, 2),
            "retail_value": round(adjusted_value * 1.08, 2),
            "trade_value": round(adjusted_value * 0.85, 2),
            "dealer_value": round(adjusted_value * 0.95, 2),
            "quick_sale": round(adjusted_value * 0.80, 2),
            "insurance_value": round(adjusted_value * 1.10, 2),
            "base_value": round(base_value, 2),
            "depreciation_rate": self._calculate_depreciation_rate(year),
            "estimated_life": 20,
            "confidence_score": confidence,
            "recommendations": self._generate_recommendations(adjustments, condition, market_data),
            "market_adjustments": adjustments,
            "scraper_data": {
                "listings_used": len(similar_listings) if similar_listings else 0,
                "market_average": market_data.get("metrics", {}).get("average_price", 0) if market_data else 0,
                "market_health": market_data.get("metrics", {}).get("market_health", "unknown") if market_data else "unknown"
            }
        }
    
    def _get_market_value(self, make: str, model: str, year: int) -> float:
        """Get market value from real data with improved matching"""
        
        # Clean model name for lookup
        model_clean = model.strip()
        
        # Check exact match first
        if make in self.KENYA_MARKET_VALUES:
            make_data = self.KENYA_MARKET_VALUES[make]
            
            # Try exact model match
            if model_clean in make_data:
                return self._get_value_for_year(make_data[model_clean], year)
            
            # Try partial match (model contains key or key contains model)
            for key, data in make_data.items():
                if key in model_clean or model_clean in key:
                    return self._get_value_for_year(data, year)
            
            # Try matching by first word (e.g., "Land Cruiser" matches "Land Cruiser Prado")
            model_parts = model_clean.split()
            if model_parts:
                for key in make_data.keys():
                    key_parts = key.split()
                    if key_parts and key_parts[0] == model_parts[0]:
                        return self._get_value_for_year(make_data[key], year)
        
        # Fallback based on vehicle type
        return self._estimate_from_type(model, year)
    
    def _get_value_for_year(self, model_data: Dict, year: int) -> float:
        """Get value for specific year from model data"""
        year_str = str(year)
        if year_str in model_data:
            return model_data[year_str]["base"]
        
        # Find closest year
        years = sorted([int(k) for k in model_data.keys() if k.isdigit()], reverse=True)
        for y in years:
            if y <= year:
                return model_data[str(y)]["base"]
        
        # Use newest available
        if years:
            return model_data[str(years[0])]["base"]
        
        return 3000000
    
    def _estimate_from_type(self, model: str, year: int) -> float:
        """Estimate value from vehicle type"""
        model_lower = model.lower()
        current_year = datetime.now().year
        age = current_year - year
        
        # Base values by type
        if any(x in model_lower for x in ["prado", "land cruiser", "range rover"]):
            base = 8000000
            base -= age * 400000
        elif any(x in model_lower for x in ["hilux", "ranger", "navara", "tacoma"]):
            base = 4000000
            base -= age * 200000
        elif any(x in model_lower for x in ["rav4", "cr-v", "forester", "cx-5", "tiguan"]):
            base = 3000000
            base -= age * 150000
        elif any(x in model_lower for x in ["x5", "gle", "q7", "cayenne"]):
            base = 8000000
            base -= age * 400000
        elif any(x in model_lower for x in ["e-class", "5 series", "a6"]):
            base = 6000000
            base -= age * 300000
        elif any(x in model_lower for x in ["c-class", "3 series", "a4"]):
            base = 4000000
            base -= age * 200000
        else:
            base = 2500000
            base -= age * 100000
        
        return max(base, 300000)
    
    def _get_market_adjustment(self, market_data: Optional[Dict]) -> float:
        """Get market adjustment from scraped data"""
        if not market_data:
            return 1.0
        
        metrics = market_data.get("metrics", {})
        total_listings = metrics.get("total_listings", 0)
        
        if total_listings > 100:
            return 1.03
        elif total_listings > 50:
            return 1.02
        elif total_listings > 20:
            return 1.0
        elif total_listings > 5:
            return 0.98
        else:
            return 0.95
    
    def _calculate_adjustments(
        self,
        year: int,
        mileage: float,
        condition: str,
        accident_history: str,
        previous_owners: int,
        location: str,
        service_history: bool
    ) -> Dict[str, float]:
        """Calculate all adjustments"""
        current_year = datetime.now().year
        age = max(0, current_year - year)
        
        # Age factor (older = less value)
        age_factor = max(0.5, 1 - (age * 0.025))
        
        # Mileage factor
        if mileage > 0:
            # Assume 100,000 km is high mileage
            mileage_factor = max(0.6, 1 - ((mileage - 10000) / 100000 * 0.15))
        else:
            mileage_factor = 1.0
        
        # Condition factor
        condition_factors = {
            "excellent": 1.12,
            "very_good": 1.06,
            "good": 1.00,
            "fair": 0.88,
            "poor": 0.72
        }
        condition_factor = condition_factors.get(condition.lower(), 1.0)
        
        # Accident history
        accident_factors = {
            "none": 1.00,
            "minor": 0.90,
            "major": 0.78,
            "total_loss": 0.55
        }
        accident_factor = accident_factors.get(accident_history.lower(), 1.0)
        
        # Previous owners
        owners_factor = max(0.82, 1 - (previous_owners - 1) * 0.025)
        
        # Location factor
        location_factors = {
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
        location_factor = location_factors.get(location.lower(), 1.0)
        
        # Service history
        service_factor = 1.04 if service_history else 0.97
        
        # Total factor
        total_factor = (
            age_factor *
            mileage_factor *
            condition_factor *
            accident_factor *
            owners_factor *
            location_factor *
            service_factor
        )
        
        return {
            "age_factor": round(age_factor, 3),
            "age_years": age,
            "mileage_factor": round(mileage_factor, 3),
            "condition_factor": round(condition_factor, 3),
            "accident_factor": round(accident_factor, 3),
            "owners_factor": round(owners_factor, 3),
            "location_factor": round(location_factor, 3),
            "service_factor": round(service_factor, 3),
            "total_factor": round(total_factor, 3)
        }
    
    def _calculate_depreciation_rate(self, year: int) -> float:
        """Calculate depreciation rate based on vehicle age"""
        current_year = datetime.now().year
        age = max(0, current_year - year)
        
        if age <= 1:
            return 0.08
        elif age <= 3:
            return 0.10
        elif age <= 5:
            return 0.12
        elif age <= 8:
            return 0.15
        else:
            return 0.18
    
    def _calculate_confidence(
        self,
        base_value: float,
        similar_listings: Optional[List[Dict]],
        adjustments: Dict[str, float],
        market_data: Optional[Dict]
    ) -> int:
        """Calculate confidence score based on data quality"""
        confidence = 50  # Base
        
        # ─── Confidence from scraper data ──────────────────────────
        if similar_listings and len(similar_listings) > 0:
            listings_count = len(similar_listings)
            if listings_count >= 50:
                confidence += 30
            elif listings_count >= 20:
                confidence += 25
            elif listings_count >= 10:
                confidence += 20
            elif listings_count >= 5:
                confidence += 15
            else:
                confidence += 5
        
        # ─── Confidence from market data ───────────────────────────
        if market_data:
            total_listings = market_data.get("metrics", {}).get("total_listings", 0)
            if total_listings > 100:
                confidence += 10
            elif total_listings > 50:
                confidence += 8
            elif total_listings > 20:
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
        market_data: Optional[Dict]
    ) -> List[str]:
        """Generate recommendations"""
        recommendations = []
        
        # Condition recommendations
        if adjustments.get("condition_factor", 1.0) < 0.85:
            recommendations.append("Vehicle condition is below average. Consider addressing issues to improve value.")
        
        # Mileage recommendations
        if adjustments.get("mileage_factor", 1.0) < 0.8:
            recommendations.append("High mileage detected. This may impact resale value.")
        
        # Accident recommendations
        if adjustments.get("accident_factor", 1.0) < 0.9:
            recommendations.append("Accident history is affecting value. Provide documentation for full assessment.")
        
        # Owner recommendations
        if adjustments.get("owners_factor", 1.0) < 0.9:
            recommendations.append("Multiple previous owners may affect value.")
        
        # Market recommendations
        if market_data:
            health = market_data.get("metrics", {}).get("market_health", "unknown")
            if health == "limited":
                recommendations.append("Limited market data available for this vehicle. Value may vary.")
            elif health == "fair":
                recommendations.append("Moderate market activity. Consider getting multiple quotes.")
        
        if condition.lower() in ["fair", "poor"]:
            recommendations.append("Consider professional inspection before purchase.")
        
        if not recommendations:
            recommendations.append("Vehicle appears to be in good condition with reasonable market value.")
        
        return recommendations
