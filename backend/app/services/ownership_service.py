"""
Ownership Service - Business logic for ownership cost calculations
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

logger = logging.getLogger(__name__)


class OwnershipService:
    """Service for ownership cost calculations"""
    
    def __init__(self):
        self.vehicle_repository = VehicleRepository()
        self.ownership_repository = OwnershipRepository()
        self.engine = OwnershipEngine()
    
    # ─── Main Calculation ──────────────────────────────────────────────
    
    def calculate_ownership_cost(self, request: OwnershipCostRequest) -> Optional[OwnershipCostResponse]:
        """Calculate total cost of ownership"""
        # Get vehicle data
        variant = self.vehicle_repository.get_variant_by_id(request.variant_id)
        if not variant:
            logger.error(f"Variant not found: {request.variant_id}")
            return None
        
        # Calculate ownership cost
        result = self.engine.calculate(variant, request)
        
        # Save report
        try:
            report_data = {
                "user_id": request.user_id if hasattr(request, 'user_id') else None,
                "vehicle_id": request.variant_id,
                "years_owned": request.years_owned,
                "annual_mileage": request.annual_mileage,
                "usage_type": request.usage_type,
                "condition": request.condition,
                "financed": request.financed,
                "purchase_price": result.breakdown.get("purchase_price", 0),
                "resale_value": result.breakdown.get("resale_value", 0),
                "total_cost": result.total_cost,
                "cost_per_km": result.cost_per_km,
                "cost_per_month": result.annual_cost / 12 if result.annual_cost else 0,
                "yearly_breakdown": result.year_by_year,
                "created_at": datetime.now().isoformat()
            }
            
            self.ownership_repository.save_ownership_report(report_data)
            logger.info(f"Ownership report saved for user {request.user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to save ownership report: {e}")
        
        return result
    
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
        """Compare ownership costs between multiple vehicles"""
        results = []
        
        for variant_id in variant_ids:
            # Create a copy of request with this variant
            variant_request = OwnershipCostRequest(
                variant_id=variant_id,
                years_owned=request.years_owned,
                annual_mileage=request.annual_mileage,
                usage_type=request.usage_type,
                condition=request.condition,
                financed=request.financed,
                user_id=request.user_id if hasattr(request, 'user_id') else None
            )
            
            result = self.calculate_ownership_cost(variant_request)
            if result:
                results.append({
                    "variant_id": variant_id,
                    "total_cost": result.total_cost,
                    "cost_per_km": result.cost_per_km,
                    "annual_cost": result.annual_cost,
                    "year_by_year": result.year_by_year,
                    "breakdown": result.breakdown
                })
        
        # Sort by total cost
        results.sort(key=lambda x: x["total_cost"])
        
        return results
    
    # ─── Advanced Calculations ────────────────────────────────────────
    
    def calculate_breakeven(self, variant_id: str, request: OwnershipCostRequest) -> Dict:
        """Calculate breakeven point for ownership vs leasing/renting"""
        # Get ownership cost
        result = self.calculate_ownership_cost(request)
        if not result:
            return {"error": "Could not calculate ownership cost"}
        
        # Calculate leasing cost (estimated)
        monthly_lease = self._estimate_lease_cost(request)
        total_lease_cost = monthly_lease * request.years_owned * 12
        
        # Calculate breakeven
        ownership_total = result.total_cost
        lease_total = total_lease_cost
        
        # Find breakeven month
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
        """Estimate monthly lease cost"""
        # Get vehicle value
        variant = self.vehicle_repository.get_variant_by_id(request.variant_id)
        if not variant:
            return 30000  # Default
        
        # Estimate lease cost as 1.5% of vehicle value per month
        vehicle_value = variant.get("market_value", 3000000)
        return vehicle_value * 0.015
    
    # ─── TCO (Total Cost of Ownership) ────────────────────────────────
    
    def calculate_tco(
        self,
        variant_id: str,
        years: int = 5,
        annual_mileage: float = 20000,
        fuel_price: float = 200,
        include_opportunity_cost: bool = True
    ) -> Dict:
        """Calculate Total Cost of Ownership with all factors"""
        
        # Get vehicle
        variant = self.vehicle_repository.get_variant_by_id(variant_id)
        if not variant:
            return {"error": "Vehicle not found"}
        
        # Get base price
        base_price = variant.get("market_value") or variant.get("base_price") or 3000000
        
        # Create request
        request = OwnershipCostRequest(
            variant_id=variant_id,
            years_owned=years,
            annual_mileage=annual_mileage,
            usage_type="private",
            condition="good",
            financed=False,
            purchase_price=base_price
        )
        
        # Calculate ownership cost
        result = self.calculate_ownership_cost(request)
        if not result:
            return {"error": "Could not calculate TCO"}
        
        # Additional costs
        opportunity_cost = 0
        if include_opportunity_cost:
            # Opportunity cost = money that could have been earned
            opportunity_cost = base_price * 0.08 * years  # 8% return per year
        
        # Total TCO
        total_tco = result.total_cost + opportunity_cost
        
        return {
            "variant_id": variant_id,
            "make": variant.get("make_name", "Unknown"),
            "model": variant.get("model_name", "Unknown"),
            "variant": variant.get("name", "Unknown"),
            "years": years,
            "annual_mileage": annual_mileage,
            "purchase_price": round(base_price, 2),
            "depreciation": round(result.breakdown.get("depreciation_total", 0), 2),
            "fuel_cost": round(result.breakdown.get("fuel_total", 0), 2),
            "maintenance": round(result.breakdown.get("maintenance_total", 0), 2),
            "insurance": round(result.breakdown.get("insurance_total", 0), 2),
            "tyres": round(result.breakdown.get("tyre_total", 0), 2),
            "licensing": round(result.breakdown.get("licensing_total", 0), 2),
            "opportunity_cost": round(opportunity_cost, 2),
            "total_ownership_cost": round(result.total_cost, 2),
            "tco": round(total_tco, 2),
            "cost_per_km": round(result.cost_per_km, 2),
            "cost_per_month": round(result.total_cost / (years * 12), 2),
            "resale_value": round(result.breakdown.get("resale_value", 0), 2)
        }
    
    # ─── Annual Breakdown ─────────────────────────────────────────────
    
    def get_annual_breakdown(self, variant_id: str, years: int = 5) -> List[Dict]:
        """Get annual breakdown of ownership costs"""
        
        request = OwnershipCostRequest(
            variant_id=variant_id,
            years_owned=years,
            annual_mileage=20000,
            usage_type="private",
            condition="good",
            financed=False
        )
        
        result = self.calculate_ownership_cost(request)
        if not result:
            return []
        
        return result.year_by_year
    
    # ─── Savings Calculator ────────────────────────────────────────────
    
    def calculate_savings(
        self,
        current_variant_id: str,
        new_variant_id: str,
        years: int = 5
    ) -> Dict:
        """Calculate savings by switching vehicles"""
        
        # Get current vehicle
        current_request = OwnershipCostRequest(
            variant_id=current_variant_id,
            years_owned=years,
            annual_mileage=20000,
            usage_type="private",
            condition="good",
            financed=False
        )
        
        current_result = self.calculate_ownership_cost(current_request)
        if not current_result:
            return {"error": "Could not calculate current vehicle costs"}
        
        # Get new vehicle
        new_request = OwnershipCostRequest(
            variant_id=new_variant_id,
            years_owned=years,
            annual_mileage=20000,
            usage_type="private",
            condition="good",
            financed=False
        )
        
        new_result = self.calculate_ownership_cost(new_request)
        if not new_result:
            return {"error": "Could not calculate new vehicle costs"}
        
        # Calculate differences
        savings = {
            "total_savings": round(current_result.total_cost - new_result.total_cost, 2),
            "monthly_savings": round((current_result.total_cost - new_result.total_cost) / (years * 12), 2),
            "fuel_savings": round(
                current_result.breakdown.get("fuel_total", 0) - 
                new_result.breakdown.get("fuel_total", 0), 2
            ),
            "maintenance_savings": round(
                current_result.breakdown.get("maintenance_total", 0) - 
                new_result.breakdown.get("maintenance_total", 0), 2
            ),
            "insurance_savings": round(
                current_result.breakdown.get("insurance_total", 0) - 
                new_result.breakdown.get("insurance_total", 0), 2
            ),
            "depreciation_savings": round(
                current_result.breakdown.get("depreciation_total", 0) - 
                new_result.breakdown.get("depreciation_total", 0), 2
            ),
            "current_vehicle": {
                "make": current_result.make,
                "model": current_result.model,
                "variant": current_result.variant,
                "total_cost": current_result.total_cost,
                "cost_per_km": current_result.cost_per_km
            },
            "new_vehicle": {
                "make": new_result.make,
                "model": new_result.model,
                "variant": new_result.variant,
                "total_cost": new_result.total_cost,
                "cost_per_km": new_result.cost_per_km
            },
            "payback_period_months": self._calculate_payback_period(
                current_result.total_cost,
                new_result.total_cost,
                years
            )
        }
        
        return savings
    
    def _calculate_payback_period(self, current_cost: float, new_cost: float, years: int) -> int:
        """Calculate payback period in months"""
        annual_savings = (current_cost - new_cost) / years
        if annual_savings <= 0:
            return None
        
        # Assume purchase premium is 20% of new vehicle value
        purchase_premium = new_cost * 0.2
        payback_months = (purchase_premium / annual_savings) * 12
        return int(payback_months)
    
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
            
            # Calculate stats
            total_cost = sum(r.get("total_cost", 0) for r in reports)
            
            # Find most expensive
            most_expensive = max(reports, key=lambda x: x.get("total_cost", 0)) if reports else None
            
            # Find most efficient (lowest cost per km)
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
