# valuation_engine.py
# Auto-D Kenya - Vehicle Valuation Service Engine
# ================================================================
# TYPE: SERVICE - Core valuation calculation engine

import logging
import math
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal

from config import settings
from database import get_supabase
from utils.helpers import (
    get_location_factor, get_condition_factor, get_accident_factor,
    calculate_age, clamp
)

logger = logging.getLogger(__name__)


class ValuationEngine:
    """
    Vehicle Valuation Engine.
    
    Calculates vehicle market value using multiple factors:
    - Base price from market data
    - Age depreciation
    - Mileage adjustment
    - Location factor
    - Condition factor
    - Accident history factor
    - Fuel type factor
    - Body type factor
    """
    
    def __init__(self):
        self.supabase = get_supabase()
        
        # Depreciation rates by vehicle type
        self.depreciation_rates = {
            "suv": {
                "premium": 0.12,
                "standard": 0.15,
                "budget": 0.18
            },
            "sedan": {
                "premium": 0.10,
                "standard": 0.13,
                "budget": 0.16
            },
            "pickup": {
                "premium": 0.11,
                "standard": 0.14,
                "budget": 0.17
            },
            "hatchback": {
                "premium": 0.12,
                "standard": 0.15,
                "budget": 0.18
            },
            "luxury": {
                "premium": 0.20,
                "standard": 0.25,
                "budget": 0.30
            },
            "default": {
                "premium": 0.15,
                "standard": 0.18,
                "budget": 0.20
            }
        }
        
        # Fuel type factors
        self.fuel_factors = {
            "petrol": 1.00,
            "diesel": 1.08,
            "electric": 1.30,
            "hybrid": 1.20,
            "lpg": 0.95,
            "cng": 0.90
        }
        
        # Body type factors
        self.body_factors = {
            "suv": 1.05,
            "sedan": 1.00,
            "hatchback": 0.95,
            "pickup": 1.08,
            "van": 1.00,
            "truck": 1.10,
            "bus": 1.05,
            "motorcycle": 0.50,
            "crossover": 1.03,
            "coupe": 1.02,
            "convertible": 0.98,
            "wagon": 0.97,
            "minivan": 0.95
        }
    
    async def get_base_price(self, variant_id: str, year: int) -> float:
        """
        Get base price for a vehicle variant.
        
        Args:
            variant_id: Vehicle variant ID
            year: Year of manufacture
            
        Returns:
            Base price in KES
        """
        try:
            # Try to get from variant data
            variant = self.supabase.table("vehicle_variants").select("*").eq("variant_id", variant_id).execute()
            if variant.data:
                # Check if variant has price data
                if variant.data[0].get("base_price"):
                    return float(variant.data[0]["base_price"])
            
            # Try to get from market prices
            market = self.supabase.table("market_prices").select("avg_price").eq("variant_id", variant_id).execute()
            if market.data and market.data[0].get("avg_price"):
                return float(market.data[0]["avg_price"])
            
            # Fallback: get from make/model
            variant_data = variant.data[0] if variant.data else {}
            make = variant_data.get("make_name", "")
            model = variant_data.get("model_name", "")
            
            if make and model:
                market = self.supabase.table("market_prices").select("avg_price").eq("make", make).eq("model", model).execute()
                if market.data and market.data[0].get("avg_price"):
                    return float(market.data[0]["avg_price"])
            
            # Default fallback
            return 3500000
            
        except Exception as e:
            logger.error(f"Error getting base price: {str(e)}")
            return 3500000
    
    def calculate_age_factor(self, year: int) -> float:
        """
        Calculate age depreciation factor.
        
        Args:
            year: Year of manufacture
            
        Returns:
            Age factor (0.0 - 1.0)
        """
        age = calculate_age(year)
        
        if age <= 0:
            return 1.0
        elif age <= 1:
            return 0.95
        elif age <= 2:
            return 0.90
        elif age <= 3:
            return 0.85
        elif age <= 4:
            return 0.80
        elif age <= 5:
            return 0.75
        elif age <= 6:
            return 0.70
        elif age <= 7:
            return 0.65
        elif age <= 8:
            return 0.60
        elif age <= 10:
            return 0.50
        elif age <= 12:
            return 0.40
        elif age <= 15:
            return 0.30
        else:
            return 0.20
    
    def calculate_mileage_factor(self, mileage: float, age: int) -> float:
        """
        Calculate mileage adjustment factor.
        
        Args:
            mileage: Odometer reading in km
            age: Vehicle age in years
            
        Returns:
            Mileage factor (0.0 - 1.0)
        """
        if mileage <= 0:
            return 1.0
        
        # Expected annual mileage (20,000 km/year)
        expected_mileage = max(age * 20000, 10000)
        
        # Calculate deviation from expected
        if expected_mileage > 0:
            ratio = mileage / expected_mileage
        else:
            ratio = 1.0
        
        # Apply adjustment
        if ratio <= 0.5:
            return 1.05  # Low mileage bonus
        elif ratio <= 0.75:
            return 1.02
        elif ratio <= 1.0:
            return 1.00
        elif ratio <= 1.25:
            return 0.97
        elif ratio <= 1.5:
            return 0.93
        elif ratio <= 2.0:
            return 0.85
        else:
            return 0.75
    
    def get_depreciation_rate(self, body_type: str, trim_level: str = "standard") -> float:
        """
        Get depreciation rate based on vehicle type.
        
        Args:
            body_type: Vehicle body type
            trim_level: Trim level (premium, standard, budget)
            
        Returns:
            Annual depreciation rate
        """
        body_type = (body_type or "default").lower()
        trim_level = (trim_level or "standard").lower()
        
        # Map trim to category
        if trim_level in ["premium", "luxury", "top", "high"]:
            category = "premium"
        elif trim_level in ["budget", "basic", "entry", "low"]:
            category = "budget"
        else:
            category = "standard"
        
        # Get rates for body type
        rates = self.depreciation_rates.get(body_type, self.depreciation_rates["default"])
        return rates.get(category, 0.15)
    
    def get_fuel_factor(self, fuel_type: str) -> float:
        """Get fuel type factor."""
        fuel_type = (fuel_type or "petrol").lower()
        return self.fuel_factors.get(fuel_type, 1.00)
    
    def get_body_factor(self, body_type: str) -> float:
        """Get body type factor."""
        body_type = (body_type or "sedan").lower()
        # Clean body type for lookup
        for key in self.body_factors:
            if key in body_type:
                return self.body_factors[key]
        return 1.00
    
    def calculate_adjusted_value(
        self,
        base_price: float,
        age_factor: float,
        mileage_factor: float,
        location_factor: float,
        condition_factor: float,
        accident_factor: float,
        fuel_factor: float = 1.0,
        body_factor: float = 1.0,
        previous_owners: int = 1,
        service_history: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate adjusted vehicle value.
        
        Args:
            base_price: Base price
            age_factor: Age factor
            mileage_factor: Mileage factor
            location_factor: Location factor
            condition_factor: Condition factor
            accident_factor: Accident factor
            fuel_factor: Fuel type factor
            body_factor: Body type factor
            previous_owners: Number of previous owners
            service_history: Whether service history is available
            
        Returns:
            Dictionary with adjusted values
        """
        # Calculate combined factor
        combined_factor = (
            age_factor *
            mileage_factor *
            location_factor *
            condition_factor *
            accident_factor *
            fuel_factor *
            body_factor
        )
        
        # Adjust for previous owners
        if previous_owners > 1:
            owner_penalty = 1 - ((previous_owners - 1) * 0.015)
            owner_penalty = max(0.90, owner_penalty)
            combined_factor *= owner_penalty
        
        # Adjust for service history
        if not service_history:
            combined_factor *= 0.97  # 3% penalty for no service history
        
        # Calculate values
        market_value = base_price * combined_factor
        retail_value = market_value * 1.08  # Retail markup
        trade_value = market_value * 0.92   # Trade-in discount
        dealer_value = market_value * 0.95   # Dealer price
        
        # Clamp values to reasonable ranges
        market_value = max(market_value, base_price * 0.10)
        retail_value = max(retail_value, market_value)
        trade_value = min(trade_value, market_value)
        dealer_value = clamp(dealer_value, trade_value, retail_value)
        
        return {
            "market_value": round(market_value, 2),
            "retail_value": round(retail_value, 2),
            "trade_value": round(trade_value, 2),
            "dealer_value": round(dealer_value, 2),
            "combined_factor": round(combined_factor, 4),
            "age_factor": round(age_factor, 4),
            "mileage_factor": round(mileage_factor, 4),
            "location_factor": round(location_factor, 4),
            "condition_factor": round(condition_factor, 4),
            "accident_factor": round(accident_factor, 4)
        }
    
    def calculate_confidence_score(
        self,
        base_price: float,
        adjusted_value: float,
        age: int,
        mileage: float,
        has_images: bool = False,
        has_service_history: bool = True,
        data_points: int = 1
    ) -> float:
        """
        Calculate confidence score for the valuation.
        
        Args:
            base_price: Base price
            adjusted_value: Adjusted value
            age: Vehicle age
            mileage: Odometer reading
            has_images: Whether images were provided
            has_service_history: Whether service history is available
            data_points: Number of data points
            
        Returns:
            Confidence score (0-100)
        """
        # Start with base confidence
        confidence = 70.0
        
        # Adjust based on data quality
        if age < 5:
            confidence += 5
        elif age > 15:
            confidence -= 10
        
        if mileage < 50000:
            confidence += 5
        elif mileage > 150000:
            confidence -= 10
        
        if has_images:
            confidence += 10
        
        if has_service_history:
            confidence += 5
        
        # Adjust based on data points
        if data_points >= 10:
            confidence += 10
        elif data_points >= 5:
            confidence += 5
        elif data_points == 0:
            confidence -= 15
        
        # Clamp to 0-100
        return clamp(confidence, 0, 100)
    
    async def calculate_valuation(
        self,
        variant_id: str,
        year: int,
        mileage: float,
        condition: str = "good",
        accident_history: str = "none",
        previous_owners: int = 1,
        service_history: bool = True,
        location: str = "nairobi",
        images: Optional[List[str]] = None,
        variant_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete valuation calculation.
        
        Args:
            variant_id: Vehicle variant ID
            year: Year of manufacture
            mileage: Odometer reading
            condition: Vehicle condition
            accident_history: Accident history
            previous_owners: Number of previous owners
            service_history: Whether service history is available
            location: Vehicle location
            images: List of image URLs
            variant_data: Optional pre-fetched variant data
            
        Returns:
            Complete valuation result
        """
        try:
            # Get variant data if not provided
            if not variant_data:
                variant_result = self.supabase.table("vehicle_variants").select("*").eq("variant_id", variant_id).execute()
                variant_data = variant_result.data[0] if variant_result.data else {}
            
            # Get base price
            base_price = await self.get_base_price(variant_id, year)
            
            # Calculate factors
            age = calculate_age(year)
            age_factor = self.calculate_age_factor(year)
            mileage_factor = self.calculate_mileage_factor(mileage, age)
            location_factor = get_location_factor(location)
            condition_factor = get_condition_factor(condition)
            accident_factor = get_accident_factor(accident_history)
            fuel_factor = self.get_fuel_factor(variant_data.get("fuel_type_name", ""))
            body_factor = self.get_body_factor(variant_data.get("body_type_name", ""))
            
            # Calculate adjusted values
            result = self.calculate_adjusted_value(
                base_price=base_price,
                age_factor=age_factor,
                mileage_factor=mileage_factor,
                location_factor=location_factor,
                condition_factor=condition_factor,
                accident_factor=accident_factor,
                fuel_factor=fuel_factor,
                body_factor=body_factor,
                previous_owners=previous_owners,
                service_history=service_history
            )
            
            # Calculate confidence score
            has_images = bool(images and len(images) > 0)
            data_points = 1  # Default to 1, would be more in production
            
            confidence = self.calculate_confidence_score(
                base_price=base_price,
                adjusted_value=result["market_value"],
                age=age,
                mileage=mileage,
                has_images=has_images,
                has_service_history=service_history,
                data_points=data_points
            )
            
            # Build vehicle name
            make = variant_data.get("make_name", "")
            model = variant_data.get("model_name", "")
            variant = variant_data.get("variant_name", "")
            vehicle_name = f"{make} {model}".strip()
            if variant:
                vehicle_name += f" {variant}"
            
            # Return complete valuation
            return {
                "variant_id": variant_id,
                "market_value": result["market_value"],
                "retail_value": result["retail_value"],
                "trade_value": result["trade_value"],
                "dealer_value": result["dealer_value"],
                "confidence_score": confidence,
                "base_price": base_price,
                "age_factor": result["age_factor"],
                "mileage_factor": result["mileage_factor"],
                "location_factor": result["location_factor"],
                "condition_factor": result["condition_factor"],
                "accident_factor": result["accident_factor"],
                "fuel_type_factor": fuel_factor,
                "body_type_factor": body_factor,
                "vehicle_name": vehicle_name,
                "year": year,
                "mileage": mileage,
                "location": location,
                "condition": condition,
                "age": age,
                "combined_factor": result["combined_factor"]
            }
            
        except Exception as e:
            logger.error(f"Valuation calculation error: {str(e)}")
            raise
