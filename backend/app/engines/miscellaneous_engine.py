"""
Miscellaneous Engine - Calculates miscellaneous vehicle costs
All data sourced from database and scraper data
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

from app.schemas.response import CostComponent
from app.services.data_service import DataService

logger = logging.getLogger(__name__)


class MiscellaneousEngine:
    """Engine for calculating miscellaneous vehicle costs using database data"""
    
    def __init__(self):
        self.data_service = DataService()
    
    def calculate(
        self, 
        vehicle: Dict[str, Any], 
        distance: float, 
        trip_type: str,
        location: str = "nairobi",
        annual_mileage: float = 20000,
        usage_type: str = "private"
    ) -> CostComponent:
        """Calculate miscellaneous costs from database"""
        
        # ─── Get data from database ──────────────────────────────────
        
        # 1. Get location factors
        location_data = self.data_service.get_location_factors(location)
        location_factor = location_data.get("price_adjustment", 1.0)
        
        # 2. Get vehicle type
        body_type = vehicle.get("body_type") or vehicle.get("body_type_name", "sedan").lower()
        
        # 3. Get cost parameters
        parking_params = self.data_service.get_cost_parameters("parking")
        toll_params = self.data_service.get_cost_parameters("tolls")
        cleaning_params = self.data_service.get_cost_parameters("cleaning")
        permit_params = self.data_service.get_cost_parameters("permits")
        accessory_params = self.data_service.get_cost_parameters("accessories")
        emergency_params = self.data_service.get_cost_parameters("emergency")
        
        # 4. Get vehicle type parameters
        type_params = self.data_service.get_vehicle_type_parameters(body_type)
        
        # ─── Calculate costs ──────────────────────────────────────────
        
        # Parking cost
        parking_cost = self._calculate_parking_cost(
            location=location,
            trip_type=trip_type,
            location_factor=location_factor,
            parking_params=parking_params
        )
        
        # Toll cost
        toll_cost = self._calculate_toll_cost(
            trip_type=trip_type,
            distance=distance,
            location=location,
            toll_params=toll_params
        )
        
        # Cleaning cost
        cleaning_cost = self._calculate_cleaning_cost(
            vehicle=vehicle,
            distance=distance,
            cleaning_params=cleaning_params,
            type_params=type_params,
            trip_type=trip_type
        )
        
        # Permit cost
        permit_cost = self._calculate_permit_cost(
            usage_type=usage_type,
            permit_params=permit_params
        )
        
        # Accessory cost
        accessory_cost = self._calculate_accessory_cost(
            vehicle=vehicle,
            accessory_params=accessory_params,
            type_params=type_params
        )
        
        # Emergency fund
        emergency_cost = self._calculate_emergency_fund(
            vehicle=vehicle,
            distance=distance,
            emergency_params=emergency_params,
            type_params=type_params
        )
        
        # ─── Total miscellaneous cost ──────────────────────────────────
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
            },
            data_source="database"
        )
    
    def _calculate_parking_cost(
        self,
        location: str,
        trip_type: str,
        location_factor: float,
        parking_params: Dict
    ) -> float:
        """Calculate parking costs from database"""
        # Get parking rates for location
        daily_rate = parking_params.get(f"{location}_daily", 200)
        monthly_rate = parking_params.get(f"{location}_monthly", 4000)
        
        # Base daily rate
        base_rate = daily_rate
        
        # Adjust for location factor
        base_rate *= location_factor
        
        # Trip type adjustment
        trip_multipliers = {
            "urban": 1.0,
            "highway": 0.3,
            "mixed": 0.6,
            "offroad": 0.2
        }
        multiplier = trip_multipliers.get(trip_type, 0.5)
        
        return base_rate * multiplier
    
    def _calculate_toll_cost(
        self,
        trip_type: str,
        distance: float,
        location: str,
        toll_params: Dict
    ) -> float:
        """Calculate toll costs from database"""
        # Get toll rates
        per_km_rate = toll_params.get("per_km", 1.5)
        urban_toll = toll_params.get("urban", 50)
        
        # Check for specific route
        route_key = f"{location}_toll"
        route_toll = toll_params.get(route_key, 0)
        
        if trip_type == "highway":
            if route_toll > 0:
                return route_toll
            return distance * per_km_rate
        else:
            return urban_toll
    
    def _calculate_cleaning_cost(
        self,
        vehicle: Dict[str, Any],
        distance: float,
        cleaning_params: Dict,
        type_params: Dict,
        trip_type: str
    ) -> float:
        """Calculate cleaning costs from database"""
        base_cost = cleaning_params.get("base", 500)
        per_1000km = cleaning_params.get("per_1000km", 100)
        
        # Distance factor
        distance_factor = 1 + (distance / 10000) * 0.1
        
        # Vehicle type multiplier from database
        type_multiplier = type_params.get("cleaning_multiplier", 1.0)
        
        # Offroad adjustment
        if trip_type == "offroad":
            type_multiplier *= cleaning_params.get("offroad_multiplier", 1.8)
        
        return (base_cost + (distance / 1000) * per_1000km) * distance_factor * type_multiplier
    
    def _calculate_permit_cost(
        self,
        usage_type: str,
        permit_params: Dict
    ) -> float:
        """Calculate permit costs from database"""
        # Get permit rates
        annual = permit_params.get("annual", 1500)
        commercial = permit_params.get("commercial", 5000)
        fleet = permit_params.get("fleet", 3000)
        
        if usage_type in ["commercial", "taxi", "uber", "bolt"]:
            return commercial
        elif usage_type == "fleet":
            return fleet
        else:
            return annual
    
    def _calculate_accessory_cost(
        self,
        vehicle: Dict[str, Any],
        accessory_params: Dict,
        type_params: Dict
    ) -> float:
        """Calculate accessories costs from database"""
        base_cost = accessory_params.get("base", 2000)
        per_year = accessory_params.get("per_year", 1000)
        
        # Vehicle type multiplier
        type_multiplier = type_params.get("accessory_multiplier", 1.0)
        
        # Year factor
        year = vehicle.get("year") or datetime.now().year
        year_factor = 1 + (datetime.now().year - year) * 0.02
        
        return (base_cost + per_year) * type_multiplier * year_factor
    
    def _calculate_emergency_fund(
        self,
        vehicle: Dict[str, Any],
        distance: float,
        emergency_params: Dict,
        type_params: Dict
    ) -> float:
        """Calculate emergency fund from database"""
        base_fund = emergency_params.get("base", 1000)
        per_year = emergency_params.get("per_year", 500)
        
        # Distance factor
        distance_factor = 1 + (distance / 50000) * 0.2
        
        # Vehicle type adjustment
        type_multiplier = type_params.get("emergency_multiplier", 1.0)
        
        # Age factor
        year = vehicle.get("year") or datetime.now().year
        age_factor = 1 + (datetime.now().year - year) * 0.05
        
        return (base_fund + per_year) * distance_factor * type_multiplier * min(age_factor, 1.5)
    
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
        """Generate a detailed description"""
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
        average_trip_distance = annual_mileage / 365
        
        daily_cost = self.calculate(
            vehicle=vehicle,
            distance=average_trip_distance,
            trip_type="mixed",
            location=location,
            annual_mileage=annual_mileage,
            usage_type=usage_type
        )
        
        annual_cost = daily_cost.amount * 365
        
        return {
            "annual_miscellaneous": round(annual_cost, 2),
            "daily_miscellaneous": round(daily_cost.amount, 2),
            "breakdown": daily_cost.breakdown,
            "description": daily_cost.description,
            "data_source": "database"
        }
