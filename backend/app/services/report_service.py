"""
Report Service - Business logic for report generation
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
import logging
import random

from app.repositories.vehicle_repository import VehicleRepository
from app.repositories.mileage_repository import MileageRepository
from app.repositories.ownership_repository import OwnershipRepository
from app.core.database import supabase
from app.core.config import settings
from app.services.valuation_service import ValuationService
from app.services.cost_calculator import CostCalculator

logger = logging.getLogger(__name__)


class ReportService:
    """Service for generating reports"""
    
    def __init__(self):
        self.vehicle_repository = VehicleRepository()
        self.mileage_repository = MileageRepository()
        self.ownership_repository = OwnershipRepository()
        self.valuation_service = ValuationService()
        self.cost_calculator = CostCalculator()
    
    # ─── Mileage Reports ──────────────────────────────────────────────
    
    def generate_mileage_report(
        self, 
        user_id: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None,
        vehicle_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate mileage report for a user"""
        try:
            # Build query
            query = supabase.table(settings.TABLE_MILEAGE_REPORTS)\
                .select("*")\
                .eq("user_id", user_id)
            
            if vehicle_id:
                query = query.eq("vehicle_id", vehicle_id)
            
            if start_date:
                query = query.gte("created_at", start_date)
            if end_date:
                query = query.lte("created_at", end_date)
            
            query = query.order("created_at", desc=True)
            
            result = query.execute()
            reports = result.data or []
            
            # Calculate statistics
            total_distance = sum(r.get('trip_distance', 0) for r in reports)
            total_cost = sum(r.get('total_cost', 0) for r in reports)
            total_fuel = sum(r.get('fuel_cost', 0) for r in reports)
            
            # Group by vehicle
            vehicles = {}
            for r in reports:
                vid = r.get('vehicle_id')
                if vid:
                    if vid not in vehicles:
                        vehicles[vid] = {
                            "vehicle_id": vid,
                            "vehicle_name": r.get('vehicle_name', 'Unknown'),
                            "trips": 0,
                            "distance": 0,
                            "cost": 0,
                            "fuel": 0
                        }
                    vehicles[vid]["trips"] += 1
                    vehicles[vid]["distance"] += r.get('trip_distance', 0)
                    vehicles[vid]["cost"] += r.get('total_cost', 0)
                    vehicles[vid]["fuel"] += r.get('fuel_cost', 0)
            
            return {
                "report_type": "mileage",
                "generated_at": datetime.now().isoformat(),
                "period": {
                    "start": start_date or "all",
                    "end": end_date or "all"
                },
                "summary": {
                    "total_reports": len(reports),
                    "total_distance": round(total_distance, 2),
                    "total_cost": round(total_cost, 2),
                    "total_fuel_cost": round(total_fuel, 2),
                    "average_cost_per_km": round(total_cost / total_distance, 2) if total_distance > 0 else 0,
                    "average_km_per_trip": round(total_distance / len(reports), 2) if reports else 0
                },
                "vehicles": list(vehicles.values()),
                "data": reports
            }
            
        except Exception as e:
            logger.error(f"Error generating mileage report: {e}")
            return self._fallback_mileage_report(user_id)
    
    def _fallback_mileage_report(self, user_id: str) -> Dict[str, Any]:
        """Fallback mileage report when database query fails"""
        return {
            "report_type": "mileage",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_reports": 0,
                "total_distance": 0,
                "total_cost": 0,
                "total_fuel_cost": 0,
                "average_cost_per_km": 0,
                "average_km_per_trip": 0
            },
            "vehicles": [],
            "data": [],
            "note": "No mileage data available"
        }
    
    # ─── Ownership Reports ────────────────────────────────────────────
    
    def generate_ownership_report(
        self, 
        user_id: str, 
        vehicle_id: Optional[str] = None,
        include_projections: bool = True
    ) -> Dict[str, Any]:
        """Generate ownership report for a user"""
        try:
            # Get ownership reports
            query = supabase.table(settings.TABLE_OWNERSHIP_REPORTS)\
                .select("*")\
                .eq("user_id", user_id)
            
            if vehicle_id:
                query = query.eq("vehicle_id", vehicle_id)
            
            query = query.order("created_at", desc=True)
            
            result = query.execute()
            reports = result.data or []
            
            # Get vehicles
            vehicles = {}
            for r in reports:
                vid = r.get('vehicle_id')
                if vid and vid not in vehicles:
                    vehicles[vid] = {
                        "vehicle_id": vid,
                        "vehicle_name": r.get('vehicle_name', 'Unknown'),
                        "reports": 0,
                        "total_cost": 0,
                        "avg_monthly": 0,
                        "avg_yearly": 0
                    }
            
            # Calculate statistics
            total_cost = sum(r.get('total_cost', 0) for r in reports)
            
            # Generate projections if requested
            projections = []
            if include_projections and reports:
                avg_monthly_cost = total_cost / (len(reports) * 12) if reports else 0
                projections = self._generate_cost_projections(avg_monthly_cost)
            
            return {
                "report_type": "ownership",
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_reports": len(reports),
                    "total_cost": round(total_cost, 2),
                    "average_cost_per_month": round(total_cost / (len(reports) * 12), 2) if reports else 0,
                    "average_cost_per_year": round(total_cost / len(reports), 2) if reports else 0,
                    "average_cost_per_km": self._calculate_avg_cost_per_km(reports)
                },
                "vehicles": list(vehicles.values()),
                "projections": projections,
                "data": reports
            }
            
        except Exception as e:
            logger.error(f"Error generating ownership report: {e}")
            return self._fallback_ownership_report(user_id)
    
    def _fallback_ownership_report(self, user_id: str) -> Dict[str, Any]:
        """Fallback ownership report"""
        return {
            "report_type": "ownership",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_reports": 0,
                "total_cost": 0,
                "average_cost_per_month": 0,
                "average_cost_per_year": 0,
                "average_cost_per_km": 0
            },
            "vehicles": [],
            "projections": [],
            "data": [],
            "note": "No ownership data available"
        }
    
    # ─── Valuation Reports ────────────────────────────────────────────
    
    def generate_valuation_report(
        self, 
        user_id: str, 
        vehicle_ids: Optional[List[str]] = None,
        include_market_comparison: bool = True
    ) -> Dict[str, Any]:
        """Generate valuation report for vehicles"""
        try:
            # Get vehicles
            if vehicle_ids:
                query = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                    .select("*")\
                    .in_("id", vehicle_ids)
            else:
                query = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                    .select("*")\
                    .limit(20)
            
            result = query.execute()
            vehicles = result.data or []
            
            # Get valuations for each vehicle
            valuations = []
            total_value = 0
            
            for v in vehicles:
                val = self.valuation_service.calculate_valuation(
                    variant_id=v.get('id'),
                    year=v.get('year', 2020),
                    mileage=50000,
                    condition="good"
                )
                if val:
                    valuations.append({
                        "vehicle": {
                            "id": v.get('id'),
                            "make": v.get('make_name') or v.get('make'),
                            "model": v.get('model_name') or v.get('model'),
                            "variant": v.get('name') or v.get('variant'),
                            "year": v.get('year')
                        },
                        "valuation": {
                            "market_value": val.get('market_value', 0),
                            "retail_value": val.get('retail_value', 0),
                            "trade_value": val.get('trade_value', 0),
                            "confidence": val.get('confidence_score', 0)
                        }
                    })
                    total_value += val.get('market_value', 0)
            
            # Market comparison
            market_data = None
            if include_market_comparison:
                market_data = self._get_market_comparison()
            
            return {
                "report_type": "valuation",
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_vehicles": len(vehicles),
                    "total_market_value": round(total_value, 2),
                    "average_value": round(total_value / len(vehicles), 2) if vehicles else 0,
                    "valuation_date": datetime.now().isoformat()
                },
                "market_comparison": market_data,
                "valuations": valuations,
                "data": vehicles
            }
            
        except Exception as e:
            logger.error(f"Error generating valuation report: {e}")
            return self._fallback_valuation_report()
    
    def _fallback_valuation_report(self) -> Dict[str, Any]:
        """Fallback valuation report"""
        return {
            "report_type": "valuation",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_vehicles": 0,
                "total_market_value": 0,
                "average_value": 0,
                "valuation_date": datetime.now().isoformat()
            },
            "market_comparison": None,
            "valuations": [],
            "data": [],
            "note": "No valuation data available"
        }
    
    # ─── Fleet Reports ────────────────────────────────────────────────
    
    def generate_fleet_report(self, user_id: str) -> Dict[str, Any]:
        """Generate fleet report for a user with multiple vehicles"""
        try:
            # Get user's vehicles
            vehicles = supabase.table("vehicles")\
                .select("*")\
                .eq("user_id", user_id)\
                .execute()
            
            vehicles_data = vehicles.data or []
            
            fleet_stats = {
                "total_vehicles": len(vehicles_data),
                "total_value": 0,
                "average_age": 0,
                "total_mileage": 0,
                "fuel_efficiency": 0,
                "maintenance_cost": 0,
                "insurance_cost": 0
            }
            
            vehicle_details = []
            total_age = 0
            
            for v in vehicles_data:
                # Get valuation
                val = self.valuation_service.calculate_valuation(
                    variant_id=v.get('variant_id'),
                    year=v.get('year', 2020),
                    mileage=v.get('mileage', 0),
                    condition="good"
                )
                
                value = val.get('market_value', 0) if val else 0
                age = datetime.now().year - (v.get('year') or 2020)
                
                fleet_stats["total_value"] += value
                total_age += age
                fleet_stats["total_mileage"] += v.get('mileage', 0)
                
                vehicle_details.append({
                    "id": v.get('id'),
                    "plate": v.get('plate'),
                    "make_model": v.get('make_model'),
                    "year": v.get('year'),
                    "mileage": v.get('mileage', 0),
                    "value": value,
                    "age": age,
                    "insurance_cost": value * 0.045,
                    "maintenance_cost": value * 0.02
                })
            
            fleet_stats["average_age"] = round(total_age / len(vehicles_data), 1) if vehicles_data else 0
            fleet_stats["insurance_cost"] = sum(v["insurance_cost"] for v in vehicle_details)
            fleet_stats["maintenance_cost"] = sum(v["maintenance_cost"] for v in vehicle_details)
            
            return {
                "report_type": "fleet",
                "generated_at": datetime.now().isoformat(),
                "summary": fleet_stats,
                "vehicles": vehicle_details
            }
            
        except Exception as e:
            logger.error(f"Error generating fleet report: {e}")
            return {
                "report_type": "fleet",
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_vehicles": 0,
                    "total_value": 0,
                    "average_age": 0,
                    "total_mileage": 0,
                    "fuel_efficiency": 0,
                    "maintenance_cost": 0,
                    "insurance_cost": 0
                },
                "vehicles": []
            }
    
    # ─── Cost Projections ─────────────────────────────────────────────
    
    def generate_cost_projection(
        self, 
        vehicle_id: str, 
        years: int = 5,
        annual_mileage: float = 20000,
        fuel_price: float = 200
    ) -> Dict[str, Any]:
        """Generate cost projection for a vehicle"""
        try:
            # Get vehicle details
            vehicle = supabase.table("vehicles")\
                .select("*")\
                .eq("id", vehicle_id)\
                .execute()
            
            if not vehicle.data:
                return {"error": "Vehicle not found"}
            
            vehicle_data = vehicle.data[0]
            
            # Get variant details
            variant = None
            if vehicle_data.get('variant_id'):
                variant = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                    .select("*")\
                    .eq("id", vehicle_data['variant_id'])\
                    .execute()
                variant = variant.data[0] if variant.data else None
            
            # Calculate projections
            projections = []
            current_value = vehicle_data.get('value', 3000000)
            current_mileage = vehicle_data.get('mileage', 0)
            
            for year in range(1, years + 1):
                # Depreciation
                dep_rate = 0.15 - (year * 0.01)
                dep_rate = max(0.08, min(0.25, dep_rate))
                depreciation = current_value * dep_rate
                current_value -= depreciation
                
                # Fuel cost
                fuel_consumption = variant.get('fuel_consumption_combined', 8) if variant else 8
                fuel_cost = (annual_mileage / 100) * fuel_consumption * fuel_price * (1 + year * 0.04)
                
                # Maintenance
                maintenance = 15000 * (1 + year * 0.08)
                
                # Insurance
                insurance = current_value * 0.045 * (1 + year * 0.03)
                
                # Tyres
                tyre_cost = 40000 * (1 + year * 0.04)
                
                # Total
                total = depreciation + fuel_cost + maintenance + insurance + tyre_cost
                current_mileage += annual_mileage
                
                projections.append({
                    "year": year,
                    "depreciation": round(depreciation, 2),
                    "fuel_cost": round(fuel_cost, 2),
                    "maintenance": round(maintenance, 2),
                    "insurance": round(insurance, 2),
                    "tyre_cost": round(tyre_cost, 2),
                    "total": round(total, 2),
                    "remaining_value": round(current_value, 2),
                    "total_mileage": round(current_mileage, 2)
                })
            
            return {
                "vehicle": {
                    "id": vehicle_data.get('id'),
                    "plate": vehicle_data.get('plate'),
                    "make_model": vehicle_data.get('make_model')
                },
                "parameters": {
                    "years": years,
                    "annual_mileage": annual_mileage,
                    "fuel_price": fuel_price,
                    "fuel_consumption": fuel_consumption if variant else 8
                },
                "projections": projections,
                "total_cost": round(sum(p["total"] for p in projections), 2),
                "final_value": round(current_value, 2)
            }
            
        except Exception as e:
            logger.error(f"Error generating cost projection: {e}")
            return {"error": str(e)}
    
    # ─── Helper Methods ───────────────────────────────────────────────
    
    def _calculate_avg_cost_per_km(self, reports: List[Dict]) -> float:
        """Calculate average cost per kilometer"""
        total_distance = sum(r.get('annual_mileage', 0) for r in reports)
        total_cost = sum(r.get('total_cost', 0) for r in reports)
        return round(total_cost / total_distance, 2) if total_distance > 0 else 0
    
    def _get_market_comparison(self) -> Dict[str, Any]:
        """Get market comparison data"""
        try:
            # Get market statistics
            result = supabase.table(settings.TABLE_MARKET_PRICES)\
                .select("*")\
                .limit(1000)\
                .execute()
            
            listings = result.data or []
            
            if not listings:
                return {"note": "No market data available"}
            
            # Calculate statistics
            prices = [l.get('price', 0) for l in listings if l.get('price')]
            if not prices:
                return {"note": "No price data available"}
            
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            
            # Group by make
            makes = {}
            for l in listings:
                make = l.get('make', 'Unknown')
                if make not in makes:
                    makes[make] = {'count': 0, 'prices': []}
                makes[make]['count'] += 1
                if l.get('price'):
                    makes[make]['prices'].append(l.get('price'))
            
            make_stats = []
            for make, data in makes.items():
                if data['prices']:
                    make_stats.append({
                        'make': make,
                        'count': data['count'],
                        'avg_price': round(sum(data['prices']) / len(data['prices']), 2),
                        'min_price': min(data['prices']),
                        'max_price': max(data['prices'])
                    })
            
            make_stats.sort(key=lambda x: x['count'], reverse=True)
            
            return {
                "total_listings": len(listings),
                "average_price": round(avg_price, 2),
                "price_range": {
                    "min": round(min_price, 2),
                    "max": round(max_price, 2)
                },
                "top_makes": make_stats[:10]
            }
            
        except Exception as e:
            logger.error(f"Error getting market comparison: {e}")
            return {"error": str(e)}
    
    def _generate_cost_projections(self, avg_monthly_cost: float) -> List[Dict]:
        """Generate cost projections for future years"""
        projections = []
        for year in range(1, 6):
            inflation = 1 + (year - 1) * 0.04
            yearly_cost = avg_monthly_cost * 12 * inflation
            projections.append({
                "year": year,
                "projected_monthly": round(avg_monthly_cost * inflation, 2),
                "projected_yearly": round(yearly_cost, 2),
                "inflation_factor": round(inflation, 2)
            })
        return projections
    
    # ─── Export Methods ───────────────────────────────────────────────
    
    def export_report_to_csv(self, report_data: Dict[str, Any]) -> str:
        """Export report data to CSV format"""
        try:
            import csv
            from io import StringIO
            
            output = StringIO()
            
            # Determine report type
            report_type = report_data.get('report_type', 'unknown')
            
            if report_type == 'mileage':
                writer = csv.writer(output)
                writer.writerow(['Date', 'Vehicle', 'Distance (km)', 'Fuel Cost', 'Service Cost', 'Tyre Cost', 'Insurance Cost', 'Depreciation', 'Total Cost'])
                
                for item in report_data.get('data', []):
                    writer.writerow([
                        item.get('created_at', ''),
                        item.get('vehicle_name', ''),
                        item.get('trip_distance', 0),
                        item.get('fuel_cost', 0),
                        item.get('service_cost', 0),
                        item.get('tyre_cost', 0),
                        item.get('insurance_cost', 0),
                        item.get('depreciation_cost', 0),
                        item.get('total_cost', 0)
                    ])
            
            elif report_type == 'ownership':
                writer = csv.writer(output)
                writer.writerow(['Vehicle', 'Total Cost', 'Monthly Average', 'Yearly Average', 'Cost per km'])
                
                for item in report_data.get('data', []):
                    writer.writerow([
                        item.get('vehicle_name', ''),
                        item.get('total_cost', 0),
                        item.get('monthly_average', 0),
                        item.get('yearly_average', 0),
                        item.get('cost_per_km', 0)
                    ])
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            return ""
    
    def export_report_to_json(self, report_data: Dict[str, Any]) -> str:
        """Export report data to JSON format"""
        try:
            return json.dumps(report_data, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error exporting report to JSON: {e}")
            return json.dumps({"error": str(e)})
