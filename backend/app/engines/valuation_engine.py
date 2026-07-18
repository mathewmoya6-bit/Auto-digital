# backend/app/engines/valuation_engine.py
"""
Valuation Engine - Vehicle valuation calculations
Calculates market value, trade-in value, retail value, and more
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ValuationEngine:
    """Engine for calculating vehicle valuations with market adjustments"""
    
    def __init__(self):
        # Depreciation rates by class (annual)
        self.depreciation_rates = {
            "SUV_A": 0.08,
            "SUV_B": 0.10,
            "SUV_C": 0.13,
            "SUV_D": 0.16,
            "SEDAN_A": 0.07,
            "SEDAN_B": 0.09,
            "SEDAN_C": 0.12,
            "SEDAN_D": 0.15,
            "PICKUP_A": 0.09,
            "PICKUP_B": 0.11,
            "PICKUP_C": 0.14,
            "LUXURY_A": 0.15,
            "LUXURY_B": 0.20,
            "LUXURY_C": 0.25,
            "MOTORCYCLE_A": 0.10,
            "MOTORCYCLE_B": 0.13,
            "MOTORCYCLE_C": 0.16,
            "TRICYCLE_A": 0.11,
            "TRICYCLE_B": 0.14,
            "TRICYCLE_C": 0.17,
            "DEFAULT": 0.12
        }
        
        # Condition multipliers
        self.condition_multipliers = {
            "excellent": 1.12,
            "very_good": 1.06,
            "good": 1.00,
            "fair": 0.85,
            "poor": 0.70
        }
        
        # Accident history penalties
        self.accident_penalties = {
            "none": 0.00,
            "minor": 0.05,
            "major": 0.15,
            "total_loss": 0.30
        }
        
        # Location adjustments (regional price differences)
        self.location_multipliers = {
            "nairobi": 1.05,
            "mombasa": 0.98,
            "kisumu": 0.95,
            "nakuru": 0.97,
            "eldoret": 0.96,
            "thika": 1.00,
            "kiambu": 1.02,
            "kajiado": 0.98,
            "machakos": 0.97,
            "meru": 0.95,
            "nyeri": 0.96,
            "embu": 0.94,
            "malindi": 0.97,
            "nanyuki": 0.98,
            "other": 0.95
        }
        
        # Fuel type adjustments
        self.fuel_adjustments = {
            "petrol": 1.00,
            "diesel": 1.05,
            "hybrid": 1.08,
            "electric": 1.10,
            "lpg": 0.95,
            "cng": 0.93
        }
        
        # Transmission adjustments
        self.transmission_adjustments = {
            "automatic": 1.00,
            "manual": 0.95,
            "cvt": 0.97,
            "dsg": 1.02,
            "dct": 1.02
        }
        
        # Body type adjustments
        self.body_type_adjustments = {
            "sedan": 1.00,
            "suv": 1.08,
            "pickup": 1.05,
            "hatchback": 0.95,
            "coupe": 0.98,
            "convertible": 0.97,
            "wagon": 0.99,
            "van": 0.96,
            "truck": 0.94,
            "motorcycle": 0.85,
            "tricycle": 0.80
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
        service_history: bool = True,
        modifications: List[str] = None,
        custom_adjustments: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive vehicle valuation
        
        Args:
            variant: Vehicle variant data from database
            year: Year of manufacture
            mileage: Current odometer reading in km
            condition: Vehicle condition rating
            accident_history: Accident history status
            previous_owners: Number of previous owners
            location: Vehicle location/county
            service_history: Whether service history is available
            modifications: List of modifications (optional)
            custom_adjustments: Custom value adjustments (optional)
        
        Returns:
            Dict with comprehensive valuation results
        """
        try:
            # Extract base data
            base_value = variant.get("market_value", 0)
            depreciation_class = variant.get("depreciation_class", "DEFAULT")
            fuel_type = variant.get("fuel_type", "petrol").lower()
            transmission = variant.get("transmission", "automatic").lower()
            body_type = variant.get("body_type", "sedan").lower()
            
            # Calculate age
            current_year = datetime.now().year
            age = current_year - year
            age = max(0, age)  # Ensure non-negative
            
            # 1. Base depreciation
            annual_rate = self.depreciation_rates.get(depreciation_class, 0.12)
            age_factor = self._calculate_age_factor(age, annual_rate)
            
            # 2. Mileage adjustment
            mileage_factor = self._calculate_mileage_factor(mileage, age)
            
            # 3. Condition adjustment
            condition_factor = self.condition_multipliers.get(condition.lower(), 1.00)
            
            # 4. Accident history penalty
            accident_penalty = self.accident_penalties.get(accident_history.lower(), 0.00)
            
            # 5. Previous owners penalty
            owners_penalty = self._calculate_owners_penalty(previous_owners)
            
            # 6. Location adjustment
            location_factor = self.location_multipliers.get(location.lower(), 0.95)
            
            # 7. Service history bonus
            service_bonus = 1.03 if service_history else 0.97
            
            # 8. Fuel type adjustment
            fuel_factor = self.fuel_adjustments.get(fuel_type, 1.00)
            
            # 9. Transmission adjustment
            transmission_factor = self.transmission_adjustments.get(transmission, 1.00)
            
            # 10. Body type adjustment
            body_factor = self.body_type_adjustments.get(body_type, 1.00)
            
            # 11. Modifications adjustment (if any)
            modifications_factor = self._calculate_modifications_factor(modifications or [])
            
            # Calculate base adjusted value
            adjusted_value = (
                base_value * 
                age_factor * 
                mileage_factor * 
                condition_factor * 
                location_factor * 
                fuel_factor * 
                transmission_factor * 
                body_factor * 
                modifications_factor *
                service_bonus
            )
            
            # Apply penalties
            adjusted_value *= (1 - accident_penalty)
            adjusted_value *= (1 - owners_penalty)
            
            # Apply custom adjustments
            if custom_adjustments:
                for key, value in custom_adjustments.items():
                    adjusted_value *= (1 + value / 100)
            
            # Ensure value doesn't go below 10% of base
            adjusted_value = max(adjusted_value, base_value * 0.10)
            
            # Calculate different valuation types
            valuations = self._calculate_valuation_tiers(adjusted_value, base_value, age)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                adjusted_value, base_value, age, mileage, condition, accident_history
            )
            
            # Calculate confidence score
            confidence = self._calculate_confidence(
                age, mileage, condition, service_history, previous_owners
            )
            
            # Calculate market adjustments
            market_adjustments = {
                "age": round((age_factor - 1) * 100, 1),
                "mileage": round((mileage_factor - 1) * 100, 1),
                "condition": round((condition_factor - 1) * 100, 1),
                "location": round((location_factor - 1) * 100, 1),
                "owners": round(-owners_penalty * 100, 1),
                "accident": round(-accident_penalty * 100, 1),
                "fuel": round((fuel_factor - 1) * 100, 1),
                "transmission": round((transmission_factor - 1) * 100, 1),
                "body_type": round((body_factor - 1) * 100, 1)
            }
            
            # Remove zero adjustments
            market_adjustments = {k: v for k, v in market_adjustments.items() if abs(v) > 0.5}
            
            return {
                "trade_value": round(valuations["trade"], 2),
                "dealer_value": round(valuations["dealer"], 2),
                "retail_value": round(valuations["retail"], 2),
                "quick_sale": round(valuations["quick_sale"], 2),
                "insurance_value": round(valuations["insurance"], 2),
                "market_value": round(adjusted_value, 2),
                "base_value": round(base_value, 2),
                "depreciation_rate": round((1 - age_factor) * 100, 1),
                "estimated_life": max(1, 20 - age),
                "confidence_score": round(confidence, 1),
                "recommendations": recommendations,
                "market_adjustments": market_adjustments,
                "valuation_date": datetime.now().isoformat(),
                "age_years": age,
                "value_retained": round((adjusted_value / base_value) * 100, 1) if base_value > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error in valuation calculation: {e}")
            raise
    
    def _calculate_age_factor(self, age: int, annual_rate: float) -> float:
        """
        Calculate age-based depreciation factor
        
        Args:
            age: Vehicle age in years
            annual_rate: Annual depreciation rate
        
        Returns:
            Age factor (0.10 - 1.00)
        """
        if age <= 0:
            return 1.00
        
        # Exponential depreciation with diminishing returns
        factor = (1 - annual_rate) ** age
        
        # Apply a floor
        return max(factor, 0.10)
    
    def _calculate_mileage_factor(self, mileage: float, age: int) -> float:
        """
        Calculate mileage adjustment factor
        
        Args:
            mileage: Current odometer reading
            age: Vehicle age in years
        
        Returns:
            Mileage factor (0.60 - 1.10)
        """
        if mileage <= 0:
            return 1.00
        
        # Expected annual mileage (20,000 km/year is average)
        expected_mileage = max(age * 20000, 20000)
        
        # Calculate ratio
        ratio = mileage / expected_mileage
        
        # Apply graduated adjustment
        if ratio <= 0.5:
            return 1.10  # Very low mileage - premium
        elif ratio <= 0.8:
            return 1.05  # Below average - slight bonus
        elif ratio <= 1.0:
            return 1.02  # Slightly below average
        elif ratio <= 1.2:
            return 1.00  # Average
        elif ratio <= 1.5:
            return 0.95  # Slightly above average
        elif ratio <= 2.0:
            return 0.85  # Above average
        elif ratio <= 3.0:
            return 0.75  # Well above average
        else:
            return 0.60  # Extremely high mileage
    
    def _calculate_owners_penalty(self, previous_owners: int) -> float:
        """
        Calculate penalty for multiple previous owners
        
        Args:
            previous_owners: Number of previous owners
        
        Returns:
            Penalty factor (0.00 - 0.20)
        """
        if previous_owners <= 0:
            return 0.00
        elif previous_owners == 1:
            return 0.02
        elif previous_owners == 2:
            return 0.05
        elif previous_owners == 3:
            return 0.08
        elif previous_owners == 4:
            return 0.12
        else:
            return 0.15
    
    def _calculate_modifications_factor(self, modifications: List[str]) -> float:
        """
        Calculate factor for vehicle modifications
        
        Args:
            modifications: List of modification types
        
        Returns:
            Modifications factor
        """
        if not modifications:
            return 1.00
        
        # Different modifications have different impacts
        modification_impacts = {
            "engine_tune": 1.05,
            "suspension": 1.02,
            "wheels": 1.01,
            "body_kit": 0.98,
            "audio_system": 1.01,
            "performance_exhaust": 1.03,
            "turbo": 1.04,
            "lift_kit": 0.97,
            "custom_paint": 1.02,
            "interior_upgrade": 1.03
        }
        
        # Average the impacts
        total_impact = 1.0
        count = 0
        for mod in modifications:
            mod_lower = mod.lower()
            impact = modification_impacts.get(mod_lower, 1.00)
            total_impact += (impact - 1.00)
            count += 1
        
        if count > 0:
            # Cap the impact
            total_impact = min(total_impact, 1.15)
            total_impact = max(total_impact, 0.85)
        
        return total_impact
    
    def _calculate_valuation_tiers(self, market_value: float, base_value: float, age: int) -> Dict[str, float]:
        """
        Calculate different valuation tiers
        
        Args:
            market_value: Adjusted market value
            base_value: Base market value
            age: Vehicle age in years
        
        Returns:
            Dictionary with different valuation tiers
        """
        # Trade-in value (wholesale to dealer)
        trade_factor = 0.85
        if age > 10:
            trade_factor = 0.80
        elif age > 7:
            trade_factor = 0.82
        
        # Dealer value (what dealer would sell for)
        dealer_factor = 1.10
        if age > 10:
            dealer_factor = 1.05
        
        # Retail value (private sale)
        retail_factor = 1.20
        
        # Quick sale (urgent sale)
        quick_sale_factor = 0.80
        
        # Insurance value (replacement cost)
        insurance_factor = 1.25
        
        # Age adjustments
        if age > 15:
            insurance_factor = 1.10
        
        return {
            "trade": market_value * trade_factor,
            "dealer": market_value * dealer_factor,
            "retail": market_value * retail_factor,
            "quick_sale": market_value * quick_sale_factor,
            "insurance": market_value * insurance_factor
        }
    
    def _generate_recommendations(
        self,
        current_value: float,
        base_value: float,
        age: int,
        mileage: float,
        condition: str,
        accident_history: str
    ) -> List[str]:
        """
        Generate intelligent recommendations based on valuation
        
        Args:
            current_value: Current market value
            base_value: Base market value
            age: Vehicle age
            mileage: Current mileage
            condition: Vehicle condition
            accident_history: Accident history
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Value retention analysis
        value_retained = (current_value / base_value * 100) if base_value > 0 else 0
        
        if value_retained > 60:
            recommendations.append(
                f"✅ Excellent value retention! This vehicle has retained {value_retained:.0f}% of its value, "
                f"which is well above average for its age."
            )
        elif value_retained > 40:
            recommendations.append(
                f"👍 Good value retention. This vehicle has retained {value_retained:.0f}% of its value, "
                f"which is average for its age."
            )
        else:
            recommendations.append(
                f"⚠️ Below average value retention ({value_retained:.0f}%). Consider negotiating a lower price "
                f"or looking for a better value vehicle."
            )
        
        # Age recommendations
        if age > 15:
            recommendations.append(
                f"🔧 At {age} years old, this vehicle is in the high-maintenance phase. "
                f"Expect significant repair costs in the coming years."
            )
        elif age > 10:
            recommendations.append(
                f"🔧 At {age} years old, this vehicle is entering the maintenance phase. "
                f"Budget for potential repairs and replacements."
            )
        elif age > 7:
            recommendations.append(
                f"📊 At {age} years old, this vehicle has passed its prime depreciation phase. "
                f"Good value for a reliable vehicle."
            )
        
        # Mileage recommendations
        if mileage > 200000:
            recommendations.append(
                f"📊 With {int(mileage):,} km, this vehicle has very high mileage. "
                f"Request detailed service records and inspect for wear."
            )
        elif mileage > 150000:
            recommendations.append(
                f"📊 With {int(mileage):,} km, this vehicle has above-average mileage. "
                f"Check maintenance history thoroughly."
            )
        elif mileage > 100000:
            recommendations.append(
                f"📊 With {int(mileage):,} km, this vehicle has average mileage for its age."
            )
        else:
            recommendations.append(
                f"📊 With {int(mileage):,} km, this vehicle has below-average mileage, "
                f"which adds value."
            )
        
        # Condition recommendations
        if condition.lower() in ["excellent", "very_good"]:
            recommendations.append(
                f"🌟 The {condition} condition adds significant value. "
                f"Well-maintained vehicles like this command premium prices."
            )
        elif condition.lower() in ["fair", "poor"]:
            recommendations.append(
                f"⚠️ The {condition} condition is below average. "
                f"Factor in the cost of repairs when negotiating the price."
            )
        
        # Accident history
        if accident_history.lower() != "none":
            recommendations.append(
                f"⚠️ Accident history ({accident_history}) significantly affects value. "
                f"Request repair documentation and inspection report."
            )
        
        # Add a summary recommendation
        if value_retained > 50 and age < 10 and mileage < 150000:
            recommendations.append(
                f"✅ This vehicle represents good value. Balanced combination of age, mileage, and condition."
            )
        elif value_retained < 30:
            recommendations.append(
                f"⚠️ This vehicle has depreciated significantly. Consider it only if the price is adjusted accordingly."
            )
        
        return recommendations
    
    def _calculate_confidence(
        self,
        age: int,
        mileage: float,
        condition: str,
        service_history: bool,
        previous_owners: int
    ) -> float:
        """
        Calculate confidence score for the valuation
        
        Args:
            age: Vehicle age
            mileage: Current mileage
            condition: Vehicle condition
            service_history: Whether service history is available
            previous_owners: Number of previous owners
        
        Returns:
            Confidence score (0-100)
        """
        score = 95.0  # Start with high confidence
        
        # Age penalty
        if age > 20:
            score -= 20
        elif age > 15:
            score -= 15
        elif age > 10:
            score -= 10
        elif age > 7:
            score -= 5
        
        # Mileage penalty
        if mileage > 250000:
            score -= 15
        elif mileage > 200000:
            score -= 10
        elif mileage > 150000:
            score -= 5
        elif mileage > 100000:
            score -= 3
        
        # Condition penalty
        if condition.lower() in ["poor"]:
            score -= 15
        elif condition.lower() in ["fair"]:
            score -= 10
        elif condition.lower() in ["good"]:
            score -= 3
        
        # Service history
        if not service_history:
            score -= 10
        
        # Previous owners
        if previous_owners > 4:
            score -= 8
        elif previous_owners > 3:
            score -= 5
        elif previous_owners > 2:
            score -= 3
        
        return max(score, 35)  # Don't go below 35%
    
    def get_depreciation_rate(self, depreciation_class: str) -> float:
        """
        Get the depreciation rate for a given class
        
        Args:
            depreciation_class: Vehicle depreciation class
        
        Returns:
            Annual depreciation rate
        """
        return self.depreciation_rates.get(depreciation_class, 0.12)
    
    def get_condition_multiplier(self, condition: str) -> float:
        """
        Get the multiplier for a given condition
        
        Args:
            condition: Vehicle condition
        
        Returns:
            Condition multiplier
        """
        return self.condition_multipliers.get(condition.lower(), 1.00)
    
    def get_location_multiplier(self, location: str) -> float:
        """
        Get the multiplier for a given location
        
        Args:
            location: Vehicle location/county
        
        Returns:
            Location multiplier
        """
        return self.location_multipliers.get(location.lower(), 0.95)
