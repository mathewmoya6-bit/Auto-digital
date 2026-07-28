"""
Ownership Service - Business logic for ownership cost calculations
ALL DATA sourced from scraper and database
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.repositories.vehicle_repository import VehicleRepository
from app.repositories.ownership_repository import OwnershipRepository
from app.engines.ownership_engine import OwnershipEngine
from app.schemas.request import OwnershipCostRequest
from app.schemas.response import OwnershipCostResponse
from app.core.database import supabase
from app.core.config import settings
from app.services.data_service import DataService

logger = logging.getLogger(__name__)


class OwnershipService:
    """Service for ownership cost calculations using scraper and database data"""
    
    def __init__(self):
        self.vehicle_repository = VehicleRepository()
        self.ownership_repository = OwnershipRepository()
        self.engine = OwnershipEngine()
        self.data_service = DataService()
    
    # ─── Main Calculation ──────────────────────────────────────────────
    
    def calculate_ownership_cost(self, request: OwnershipCostRequest) -> Optional[OwnershipCostResponse]:
        """Calculate total cost of ownership using scraper and database data"""
        
        # ─── Get vehicle data from database ──────────────────────────
        variant = self.vehicle_repository.get_variant_by_id(request.variant_id)
        if not variant:
            logger.error(f"Variant not found: {request.variant_id}")
            return None
        
        # ─── Get market data from scraper ────────────────────────────
        make = variant.get("make_name") or variant.get("make")
        model = variant.get("model_name") or variant.get("model")
        
        market_stats = self.data_service.get_market_statistics(
            make=make,
            model=model,
            days=90
        )
        
        # ─── Get similar listings from scraper ──────────────────────
        similar_listings = self.data_service.get_market_prices(
            make=make,
            model=model,
            limit=50
        )
        
        # ─── Get market value from scraper ────────────────────────────
        market_value = self._get_market_value(variant, market_stats)
        
        # ─── Get location factors from database ──────────────────────
        location = request.location if hasattr(request, 'location') else "nairobi"
        location_data = self.data_service.get_location_factors(location)
        
        # ─── Get vehicle type parameters from database ──────────────
        body_type = variant.get("body_type") or variant.get("body_type_name", "sedan").lower()
        type_params = self.data_service.get_vehicle_type_parameters(body_type)
        
        # ─── Get insurance rates from database ──────────────────────
        insurance_data = self.data_service.get_insurance_rates(body_type)
        
        # ─── Get service intervals from database ─────────────────────
        service_data = self.data_service.get_service_intervals(body_type)
        
        # ─── Get depreciation rates from database ────────────────────
        dep_class = variant.get("depreciation_class") or f"{body_type.upper()}_D"
        dep_data = self.data_service.get_depreciation_rates(dep_class)
        
        # ─── Get fuel prices from database ───────────────────────────
        fuel_type = variant.get("fuel_type", "petrol")
        fuel_data = self.data_service.get_fuel_prices(fuel_type)
        fuel_price = request.fuel_price or fuel_data.get("price", 200.00)
        
        # ─── Calculate ownership cost ─────────────────────────────────
        result = self.engine.calculate_ownership_cost(
            variant=variant,
            request=request,
            market_value=market_value,
            market_stats=market_stats,
            similar_listings=similar_listings,
            location_data=location_data,
            type_params=type_params,
            insurance_data=insurance_data,
            service_data=service_data,
            dep_data=dep_data,
            fuel_price=fuel_price
        )
        
        # ─── Save report ──────────────────────────────────────────────
        try:
            report_data = {
                "user_id": request.user_id if hasattr(request, 'user_id') else None,
                "vehicle_id": request.variant_id,
                "vehicle_name": variant.get("name", "Unknown"),
                "make": make,
                "model": model,
                "year": variant.get("year"),
                "years_owned": request.years_owned,
                "annual_mileage": request.annual_mileage,
                "usage_type": request.usage_type,
                "condition": request.condition,
                "financed": request.financed,
                "purchase_price": request.purchase_price or market_value,
                "market_value": market_value,
                "resale_value": result.get("resale_value", 0),
                "total_cost": result.get("total_cost", 0),
                "cost_per_km": result.get("cost_per_km", 0),
                "cost_per_month": result.get("total_cost", 0) / (request.years_owned * 12) if result.get("total_cost") else 0,
                "yearly_breakdown": result.get("year_by_year", []),
                "market_data": {
                    "listings_available": market_stats.get("total_listings", 0),
                    "market_health": market_stats.get("market_health", "unknown"),
                    "average_price": market_stats.get("average_price", 0)
                },
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            self.ownership_repository.save_ownership_report(report_data)
            logger.info(f"Ownership report saved for user {request.user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to save ownership report: {e}")
        
        return result
    
    def _get_market_value(self, variant: Dict, market_stats: Dict) -> float:
        """Get market value from scraper or database"""
        # Prefer scraper data
        if market_stats.get("total_listings", 0) > 0:
            median_price = market_stats.get("median_price", 0)
            avg_price = market_stats.get("average_price", 0)
            if median_price > 0:
                return median_price
            if avg_price > 0:
                return avg_price
        
        # Use variant stored value
        if variant.get("market_value"):
            return variant["market_value"]
        
        if variant.get("base_price"):
            return variant["base_price"]
        
        if variant.get("price"):
            return variant["price"]
        
        # Estimate
        body_type = variant.get("body_type") or variant.get("body_type_name", "sedan").lower()
        year = variant.get("year") or datetime.now().year
        age = datetime.now().year - year
        
        base_values = {
            "suv": 4500000, "sedan": 3500000, "hatchback": 2500000,
            "pickup": 4000000, "van": 3800000, "luxury": 8000000,
            "crossover": 3800000, "coupe": 5000000, "convertible": 5500000
        }
        value = base_values.get(body_type, 3000000)
        value *= max(0.3, 1 - (age * 0.10))
        return max(value, 300000)
    
    # ─── Report Retrieval ──────────────────────────────────────────────
    
    def get_ownership_reports(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get ownership reports for a user"""
        return self.ownership_repository.get_ownership_reports(user_id, limit)
    
    def get_ownership_report_by_id(self, report_id: str) -> Optional[Dict]:
        """Get a specific ownership report by ID"""
        try:
            result = supabase.table(settings.TABLE_OWNERSHIP_REPORTS)\
                .select("*")\
                .eq("id", report_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting ownership report: {e}")
            return None
    
    # ─── Comparison ────────────────────────────────────────────────────
    
    def compare_vehicles(self, variant_ids: List[str], request: OwnershipCostRequest) -> List[Dict]:
        """Compare ownership costs between multiple vehicles using scraper data"""
        results = []
        
        for variant_id in variant_ids:
            variant = self.vehicle_repository.get_variant_by_id(variant_id)
            if not variant:
                continue
            
            # Get market data
            market_stats = self.data_service.get_market_statistics(
                make=variant.get("make_name") or variant.get("make"),
                model=variant.get("model_name") or variant.get("model"),
                days=90
            )
            
            variant_request = OwnershipCostRequest(
                variant_id=variant_id,
                years_owned=request.years_owned,
                annual_mileage=request.annual_mileage,
                usage_type=request.usage_type,
                condition=request.condition,
                financed=request.financed,
                user_id=request.user_id if hasattr(request, 'user_id') else None,
                location=request.location if hasattr(request, 'location') else "nairobi"
            )
            
            result = self.calculate_ownership_cost(variant_request)
            if result:
                results.append({
                    "variant_id": variant_id,
                    "make": variant.get("make_name", "Unknown"),
                    "model": variant.get("model_name", "Unknown"),
                    "variant": variant.get("name", "Unknown"),
                    "total_cost": result.get("total_cost", 0),
                    "cost_per_km": result.get("cost_per_km", 0),
                    "annual_cost": result.get("annual_cost", 0),
                    "monthly_cost": result.get("monthly_cost", 0),
                    "year_by_year": result.get("year_by_year", []),
                    "breakdown": result.get("breakdown", {}),
                    "market_value": result.get("market_value", 0),
                    "resale_value": result.get("resale_value", 0),
                    "listings_available": market_stats.get("total_listings", 0)
                })
        
        # Sort by total cost
        results.sort(key=lambda x: x["total_cost"])
        
        return results
    
    # ─── Advanced Calculations ────────────────────────────────────────
    
    def calculate_breakeven(self, variant_id: str, request: OwnershipCostRequest) -> Dict:
        """Calculate breakeven point for ownership vs leasing/renting"""
        result = self.calculate_ownership_cost(request)
        if not result:
            return {"error": "Could not calculate ownership cost"}
        
        monthly_lease = self._estimate_lease_cost(request)
        total_lease_cost = monthly_lease * request.years_owned * 12
        
        ownership_total = result.get("total_cost", 0)
        lease_total = total_lease_cost
        
        breakeven_month = None
        for month in range(1, request.years_owned * 12 + 1):
            ownership_cumulative = ownership_total * (month / (request.years_owned * 12))
            lease_cumulative = lease_total * (month / (request.years_owned * 12))
            if lease_cumulative >= ownership_cumulative:
                breakeven_month = month
                break
        
        return {
            "ownership_total": round(ownership_total, 2),
            "lease_total": round(lease_total, 2),
            "monthly_lease": round(monthly_lease, 2),
            "breakeven_month": breakeven_month,
            "breakeven_years": round(breakeven_month / 12, 1) if breakeven_month else None,
            "recommendation": "Buy" if ownership_total < lease_total else "Lease"
        }
    
    def _estimate_lease_cost(self, request: OwnershipCostRequest) -> float:
        """Estimate monthly lease cost from market data"""
        variant = self.vehicle_repository.get_variant_by_id(request.variant_id)
        if not variant:
            return 30000
        
        market_value = variant.get("market_value") or variant.get("base_price") or 3000000
        return market_value * 0.015
    
    # ─── TCO (Total Cost of Ownership) ────────────────────────────────
    
    def calculate_tco(
        self,
        variant_id: str,
        years: int = 5,
        annual_mileage: float = 20000,
        fuel_price: float = 200,
        include_opportunity_cost: bool = True,
        location: str = "nairobi"
    ) -> Dict:
        """Calculate Total Cost of Ownership with all factors"""
        
        variant = self.vehicle_repository.get_variant_by_id(variant_id)
        if not variant:
            return {"error": "Vehicle not found"}
        
        # Get market value from scraper
        market_stats = self.data_service.get_market_statistics(
            make=variant.get("make_name") or variant.get("make"),
            model=variant.get("model_name") or variant.get("model"),
            days=90
        )
        
        market_value = self._get_market_value(variant, market_stats)
        base_price = request.purchase_price if hasattr(request, 'purchase_price') else market_value
        
        request = OwnershipCostRequest(
            variant_id=variant_id,
            years_owned=years,
            annual_mileage=annual_mileage,
            usage_type="private",
            condition="good",
            financed=False,
            purchase_price=base_price,
            location=location
        )
        
        result = self.calculate_ownership_cost(request)
        if not result:
            return {"error": "Could not calculate TCO"}
        
        opportunity_cost = 0
        if include_opportunity_cost:
            opportunity_cost = base_price * 0.08 * years
        
        total_tco = result.get("total_cost", 0) + opportunity_cost
        
        return {
            "variant_id": variant_id,
            "make": variant.get("make_name", "Unknown"),
            "model": variant.get("model_name", "Unknown"),
            "variant": variant.get("name", "Unknown"),
            "year": variant.get("year"),
            "years": years,
            "annual_mileage": annual_mileage,
            "purchase_price": round(base_price, 2),
            "market_value": round(market_value, 2),
            "depreciation": round(result.get("breakdown", {}).get("depreciation_total", 0), 2),
            "fuel_cost": round(result.get("breakdown", {}).get("fuel_total", 0), 2),
            "maintenance": round(result.get("breakdown", {}).get("maintenance_total", 0), 2),
            "insurance": round(result.get("breakdown", {}).get("insurance_total", 0), 2),
            "tyres": round(result.get("breakdown", {}).get("tyre_total", 0), 2),
            "licensing": round(result.get("breakdown", {}).get("licensing_total", 0), 2),
            "opportunity_cost": round(opportunity_cost, 2),
            "total_ownership_cost": round(result.get("total_cost", 0), 2),
            "tco": round(total_tco, 2),
            "cost_per_km": round(result.get("cost_per_km", 0), 2),
            "cost_per_month": round(result.get("total_cost", 0) / (years * 12), 2),
            "resale_value": round(result.get("resale_value", 0), 2),
            "market_data": {
                "listings_available": market_stats.get("total_listings", 0),
                "market_health": market_stats.get("market_health", "unknown"),
                "average_price": market_stats.get("average_price", 0)
            }
        }
    
    # ─── Annual Breakdown ─────────────────────────────────────────────
    
    def get_annual_breakdown(self, variant_id: str, years: int = 5, location: str = "nairobi") -> List[Dict]:
        """Get annual breakdown of ownership costs"""
        
        request = OwnershipCostRequest(
            variant_id=variant_id,
            years_owned=years,
            annual_mileage=20000,
            usage_type="private",
            condition="good",
            financed=False,
            location=location
        )
        
        result = self.calculate_ownership_cost(request)
        if not result:
            return []
        
        return result.get("year_by_year", [])
    
    # ─── Savings Calculator ────────────────────────────────────────────
    
    def calculate_savings(
        self,
        current_variant_id: str,
        new_variant_id: str,
        years: int = 5,
        location: str = "nairobi"
    ) -> Dict:
        """Calculate savings by switching vehicles using market data"""
        
        current_request = OwnershipCostRequest(
            variant_id=current_variant_id,
            years_owned=years,
            annual_mileage=20000,
            usage_type="private",
            condition="good",
            financed=False,
            location=location
        )
        
        current_result = self.calculate_ownership_cost(current_request)
        if not current_result:
            return {"error": "Could not calculate current vehicle costs"}
        
        new_request = OwnershipCostRequest(
            variant_id=new_variant_id,
            years_owned=years,
            annual_mileage=20000,
            usage_type="private",
            condition="good",
            financed=False,
            location=location
        )
        
        new_result = self.calculate_ownership_cost(new_request)
        if not new_result:
            return {"error": "Could not calculate new vehicle costs"}
        
        return {
            "total_savings": round(current_result.get("total_cost", 0) - new_result.get("total_cost", 0), 2),
            "monthly_savings": round((current_result.get("total_cost", 0) - new_result.get("total_cost", 0)) / (years * 12), 2),
            "fuel_savings": round(
                current_result.get("breakdown", {}).get("fuel_total", 0) - 
                new_result.get("breakdown", {}).get("fuel_total", 0), 2
            ),
            "maintenance_savings": round(
                current_result.get("breakdown", {}).get("maintenance_total", 0) - 
                new_result.get("breakdown", {}).get("maintenance_total", 0), 2
            ),
            "insurance_savings": round(
                current_result.get("breakdown", {}).get("insurance_total", 0) - 
                new_result.get("breakdown", {}).get("insurance_total", 0), 2
            ),
            "depreciation_savings": round(
                current_result.get("breakdown", {}).get("depreciation_total", 0) - 
                new_result.get("breakdown", {}).get("depreciation_total", 0), 2
            ),
            "current_vehicle": {
                "make": current_result.get("make", "Unknown"),
                "model": current_result.get("model", "Unknown"),
                "variant": current_result.get("variant", "Unknown"),
                "total_cost": current_result.get("total_cost", 0),
                "cost_per_km": current_result.get("cost_per_km", 0)
            },
            "new_vehicle": {
                "make": new_result.get("make", "Unknown"),
                "model": new_result.get("model", "Unknown"),
                "variant": new_result.get("variant", "Unknown"),
                "total_cost": new_result.get("total_cost", 0),
                "cost_per_km": new_result.get("cost_per_km", 0)
            }
        }
    
    # ─── Stats ─────────────────────────────────────────────────────────
    
    def get_ownership_stats(self, user_id: str) -> Dict:
        """Get ownership statistics for a user"""
        try:
            reports = self.ownership_repository.get_ownership_reports(user_id, 100)
            
            if not reports:
                return {
                    "total_vehicles": 0,
                    "total_cost": 0,
                    "average_cost": 0,
                    "most_expensive": None,
                    "most_efficient": None
                }
            
            total_cost = sum(r.get("total_cost", 0) for r in reports)
            
            most_expensive = max(reports, key=lambda x: x.get("total_cost", 0)) if reports else None
            
            most_efficient = min(
                [r for r in reports if r.get("cost_per_km", 0) > 0],
                key=lambda x: x.get("cost_per_km", 0),
                default=None
            )
            
            return {
                "total_vehicles": len(reports),
                "total_cost": round(total_cost, 2),
                "average_cost": round(total_cost / len(reports), 2) if reports else 0,
                "most_expensive": {
                    "vehicle": most_expensive.get("vehicle_name", "Unknown") if most_expensive else None,
                    "cost": most_expensive.get("total_cost", 0) if most_expensive else 0
                } if most_expensive else None,
                "most_efficient": {
                    "vehicle": most_efficient.get("vehicle_name", "Unknown") if most_efficient else None,
                    "cost_per_km": most_efficient.get("cost_per_km", 0) if most_efficient else 0
                } if most_efficient else None
            }
            
        except Exception as e:
            logger.error(f"Error getting ownership stats: {e}")
            return {
                "total_vehicles": 0,
                "total_cost": 0,
                "average_cost": 0,
                "most_expensive": None,
                "most_efficient": None
            }
