"""
Miscellaneous Engine - Calculates miscellaneous vehicle costs
Includes parking, tolls, cleaning, permits, and other expenses
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

from app.schemas.response import CostComponent
from app.services.market_service import MarketService

logger = logging.getLogger(__name__)


class MiscellaneousEngine:
    """Engine for calculating miscellaneous vehicle costs"""
    
    # ─── Kenyan Market Rates ──────────────────────────────────────────
    KENYA_MISC_RATES = {
        "parking": {
            "nairobi": {"daily": 300, "monthly": 6000, "hourly": 50},
            "mombasa": {"daily": 200, "monthly": 4000, "hourly": 40},
            "kisumu": {"daily": 150, "monthly": 3000, "hourly": 30},
            "nakuru": {"daily": 150, "monthly": 3000, "hourly": 30},
            "eldoret": {"daily": 150, "monthly": 3000, "hourly": 30},
            "other": {"daily": 100, "monthly": 2000, "hourly": 20}
        },
        "tolls": {
            "nairobi_mombasa": 300,
            "nairobi_nakuru": 250,
            "nairobi_kisumu": 400,
            "nairobi_eldoret": 350,
            "nairobi_malindi": 350,
            "nairobi_nanyuki": 200,
            "mombasa_malindi": 150,
            "mombasa_lamu": 200,
            "urban": 50,
            "per_km": 1.5
        },
        "cleaning": {
            "base": 500,
            "per_1000km": 100,
            "suv_multiplier": 1.3,
            "luxury_multiplier": 1.5,
            "pickup_multiplier": 1.2,
            "offroad_multiplier": 1.8
        },
        "permits": {
            "annual": 1500,
            "commercial": 5000,
            "fleet": 3000,
            "special": 2000
        },
        "accessories": {
            "base": 2000,
            "per_year": 1000,
            "suv_multiplier": 1.2,
            "luxury_multiplier": 1.5
        },
        "emergency": {
            "base": 1000,
            "per_year": 500,
            "offroad_multiplier": 1.5
        }
    }
    
    def __init__(self):
        self.market_service = MarketService()
    
    def calculate(
        self, 
        vehicle: Dict[str, Any], 
        distance: float, 
        trip_type: str,
        location: str = "nairobi",
        annual_mileage: float = 20000,
        usage_type: str = "private"
    ) -> CostComponent:
        """Calculate miscellaneous costs (parking, tolls, cleaning, etc.)"""
        
        # ─── Get market-based rates ──────────────────────────────────
        market_data = self.market_service.get_location_factors(location)
        location_factor = market_data.get("factors", {}).get("price_adjustment", 1.0)
        
        # ─── Calculate parking costs ──────────────────────────────────
        parking_cost = self._calculate_parking_cost(location, trip_type, location_factor)
        
        # ─── Calculate toll costs ────────────────────────────────────
        toll_cost = self._calculate_toll_cost(trip_type, distance, location)
        
        # ─── Calculate cleaning costs ────────────────────────────────
        cleaning_cost = self._calculate_cleaning_cost(vehicle, distance)
        
        # ─── Calculate permits ───────────────────────────────────────
        permit_cost = self._calculate_permit_cost(usage_type, annual_mileage)
        
        # ─── Calculate accessories ──────────────────────────────────
        accessory_cost = self._calculate_accessory_cost(vehicle)
        
        # ─── Calculate emergency fund ──────────────────────────────
        emergency_cost = self._calculate_emergency_fund(vehicle, distance)
        
        # ─── Total miscellaneous cost ──────────────────────────────
        total_misc = (
            parking_cost +
            toll_cost +
            cleaning_cost +
            permit_cost +
            accessory_cost +
            emergency_cost
        )
        
        # ─── Generate description ──────────────────────────────────
        description = self._generate_description(
            parking_cost=parking_cost,
            toll_cost=toll_cost,
            cleaning_cost=cleaning_cost,
            permit_cost=permit_cost,
            accessory_cost=accessory_cost,
            emergency_cost=emergency_cost,
            location=location,
            trip_type=trip_type
        )
        
        return CostComponent(
            component="Miscellaneous",
            amount=round(total_misc, 2),
            description=description,
            breakdown={
                "parking": round(parking_cost, 2),
                "tolls": round(toll_cost, 2),
                "cleaning": round(cleaning_cost, 2),
                "permits": round(permit_cost, 2),
                "accessories": round(accessory_cost, 2),
                "emergency_fund": round(emergency_cost, 2)
            }
        )
    
    def _calculate_parking_cost(self, location: str, trip_type: str, location_factor: float) -> float:
        """Calculate parking costs based on location and trip type"""
        
        # Get parking rates for location
        parking_rates = self.KENYA_MISC_RATES["parking"].get(
            location.lower(), 
            self.KENYA_MISC_RATES["parking"]["other"]
        )
        
        # Base daily rate
        base_rate = parking_rates.get("daily", 200)
        
        # Adjust for location factor
        base_rate *= location_factor
        
        # Trip type adjustment
        trip_multipliers = {
            "urban": 1.0,      # Daily parking
            "highway": 0.3,    # Less parking on highways
            "mixed": 0.6,      # Some parking
            "offroad": 0.2     # Little to no parking
        }
        multiplier = trip_multipliers.get(trip_type, 0.5)
        
        return base_rate * multiplier
    
    def _calculate_toll_cost(self, trip_type: str, distance: float, location: str) -> float:
        """Calculate toll costs based on trip type and distance"""
        
        # Check if trip is on a major highway route
        toll_routes = self.KENYA_MISC_RATES["tolls"]
        
        # Calculate toll cost per km
        if trip_type == "highway":
            # Use per_km rate for highway trips
            toll_per_km = toll_routes.get("per_km", 1.5)
            base_toll = distance * toll_per_km
        else:
            # Urban and mixed trips have lower tolls
            base_toll = toll_routes.get("urban", 50)
        
        return base_toll
    
    def _calculate_cleaning_cost(self, vehicle: Dict[str, Any], distance: float) -> float:
        """Calculate cleaning costs based on vehicle type and distance"""
        
        cleaning_rates = self.KENYA_MISC_RATES["cleaning"]
        base_cost = cleaning_rates["base"]
        
        # Distance factor (cleaning needed more often with more use)
        distance_factor = 1 + (distance / 10000) * 0.1
        
        # Vehicle type multiplier
        body_type = vehicle.get("body_type") or vehicle.get("body_type_name", "sedan").lower()
        type_multipliers = {
            "suv": cleaning_rates.get("suv_multiplier", 1.3),
            "crossover": cleaning_rates.get("suv_multiplier", 1.3),
            "pickup": cleaning_rates.get("pickup_multiplier", 1.2),
            "truck": cleaning_rates.get("pickup_multiplier", 1.2),
            "luxury": cleaning_rates.get("luxury_multiplier", 1.5),
            "coupe": cleaning_rates.get("luxury_multiplier", 1.5),
            "convertible": cleaning_rates.get("luxury_multiplier", 1.5),
            "sedan": 1.0,
            "hatchback": 1.0,
            "wagon": 1.0,
            "van": 1.1,
            "minivan": 1.1
        }
        type_multiplier = type_multipliers.get(body_type, 1.0)
        
        # Offroad adjustment
        if trip_type == "offroad":
            type_multiplier *= cleaning_rates.get("offroad_multiplier", 1.8)
        
        return base_cost * distance_factor * type_multiplier
    
    def _calculate_permit_cost(self, usage_type: str, annual_mileage: float) -> float:
        """Calculate permit costs based on usage type"""
        
        permit_rates = self.KENYA_MISC_RATES["permits"]
        
        if usage_type == "commercial":
            return permit_rates["commercial"]
        elif usage_type == "fleet":
            return permit_rates["fleet"]
        elif usage_type in ["taxi", "uber", "bolt"]:
            return permit_rates["commercial"] * 0.8
        else:
            return permit_rates["annual"]
    
    def _calculate_accessory_cost(self, vehicle: Dict[str, Any]) -> float:
        """Calculate accessories and equipment costs"""
        
        accessory_rates = self.KENYA_MISC_RATES["accessories"]
        base_cost = accessory_rates["base"]
        
        # Vehicle type multiplier
        body_type = vehicle.get("body_type") or vehicle.get("body_type_name", "sedan").lower()
        type_multipliers = {
            "suv": accessory_rates.get("suv_multiplier", 1.2),
            "crossover": accessory_rates.get("suv_multiplier", 1.2),
            "luxury": accessory_rates.get("luxury_multiplier", 1.5),
            "coupe": accessory_rates.get("luxury_multiplier", 1.5),
            "pickup": 1.0,
            "truck": 1.0,
            "sedan": 1.0,
            "hatchback": 1.0
        }
        type_multiplier = type_multipliers.get(body_type, 1.0)
        
        # Year factor (newer vehicles might have more accessories)
        year = vehicle.get("year") or datetime.now().year
        year_factor = 1 + (datetime.now().year - year) * 0.02
        
        return base_cost * type_multiplier * year_factor
    
    def _calculate_emergency_fund(self, vehicle: Dict[str, Any], distance: float) -> float:
        """Calculate emergency fund allocation"""
        
        emergency_rates = self.KENYA_MISC_RATES["emergency"]
        base_fund = emergency_rates["base"]
        
        # Distance factor
        distance_factor = 1 + (distance / 50000) * 0.2
        
        # Vehicle type adjustment
        body_type = vehicle.get("body_type") or vehicle.get("body_type_name", "sedan").lower()
        if body_type in ["offroad", "truck"]:
            distance_factor *= emergency_rates.get("offroad_multiplier", 1.5)
        
        # Age factor (older vehicles need more emergency funds)
        year = vehicle.get("year") or datetime.now().year
        age_factor = 1 + (datetime.now().year - year) * 0.05
        
        return base_fund * distance_factor * min(age_factor, 1.5)
    
    def _generate_description(
        self,
        parking_cost: float,
        toll_cost: float,
        cleaning_cost: float,
        permit_cost: float,
        accessory_cost: float,
        emergency_cost: float,
        location: str,
        trip_type: str
    ) -> str:
        """Generate a detailed description of miscellaneous costs"""
        
        descriptions = []
        
        if parking_cost > 0:
            descriptions.append(f"Parking fees (KES {parking_cost:.2f})")
        if toll_cost > 0:
            descriptions.append(f"Tolls and road fees (KES {toll_cost:.2f})")
        if cleaning_cost > 0:
            descriptions.append(f"Vehicle cleaning (KES {cleaning_cost:.2f})")
        if permit_cost > 0:
            descriptions.append(f"Permits and licenses (KES {permit_cost:.2f})")
        if accessory_cost > 0:
            descriptions.append(f"Accessories and equipment (KES {accessory_cost:.2f})")
        if emergency_cost > 0:
            descriptions.append(f"Emergency fund allocation (KES {emergency_cost:.2f})")
        
        if not descriptions:
            return "No miscellaneous costs calculated"
        
        base = f"Miscellaneous costs for {trip_type} trip in {location}: "
        return base + ", ".join(descriptions)
    
    def calculate_annual_miscellaneous(
        self,
        vehicle: Dict[str, Any],
        annual_mileage: float = 20000,
        location: str = "nairobi",
        usage_type: str = "private"
    ) -> Dict[str, float]:
        """Calculate annual miscellaneous costs"""
        
        # Calculate per-trip costs and annualize
        average_trip_distance = annual_mileage / 365  # per day average
        
        # Calculate daily miscellaneous cost
        daily_cost = self.calculate(
            vehicle=vehicle,
            distance=average_trip_distance,
            trip_type="mixed",
            location=location,
            annual_mileage=annual_mileage,
            usage_type=usage_type
        )
        
        # Annualize
        annual_cost = daily_cost.amount * 365
        
        return {
            "annual_miscellaneous": round(annual_cost, 2),
            "daily_miscellaneous": round(daily_cost.amount, 2),
            "breakdown": daily_cost.breakdown,
            "description": daily_cost.description
        }
