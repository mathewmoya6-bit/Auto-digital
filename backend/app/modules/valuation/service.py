# app/modules/valuation/service.py
# Auto-D Kenya - Valuation Service
# ================================================================
# TYPE: MODULE - Valuation business logic
# ================================================================

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import secrets

from app.modules.valuation.engine import ValuationEngine
from app.core.database import get_supabase
from app.core.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)


class ValuationService:
    """
    Valuation service for business logic.
    
    Handles:
    - Vehicle valuation calculation
    - Vehicle data retrieval from vehicle_master_specs
    - Report generation
    - History management
    - Statistics
    """
    
    def __init__(self):
        """Initialize the valuation service."""
        self.engine = ValuationEngine()
        self.supabase = get_supabase()
        logger.info("ValuationService initialized")
    
    # ================================================================
    # MAIN VALUATION METHOD
    # ================================================================
    
    async def calculate_valuation(
        self,
        variant_id: int,
        year: int,
        mileage: int,
        condition: str = "good",
        accident_history: str = "none",
        location: str = "nairobi",
        fuel_type: Optional[str] = None,
        transmission: Optional[str] = None,
        ownership_count: int = 1,
        service_history: bool = True,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate vehicle valuation.
        
        Args:
            variant_id: Vehicle variant ID
            year: Vehicle year of manufacture
            mileage: Odometer reading in km
            condition: Vehicle condition (excellent, very_good, good, fair, poor)
            accident_history: Accident history (none, minor, major, total_loss)
            location: Vehicle location
            fuel_type: Optional fuel type override
            transmission: Optional transmission override
            ownership_count: Number of previous owners
            service_history: Whether service records exist
            user_id: Optional user ID for saving history
            
        Returns:
            Dict[str, Any]: Complete valuation report
            
        Raises:
            NotFoundException: If vehicle data cannot be found
            ValidationException: If input validation fails
        """
        
        logger.info(f"Starting valuation calculation for variant_id: {variant_id}")
        
        # ─── VALIDATION ──────────────────────────────────────────────────
        
        if not variant_id or variant_id <= 0:
            raise ValidationException("Valid variant ID required")
        
        if year < 1980 or year > datetime.now().year + 1:
            raise ValidationException(f"Invalid year: {year}")
        
        if mileage < 0:
            raise ValidationException(f"Invalid mileage: {mileage}")
        
        # Normalize inputs
        condition = condition.lower().strip()
        accident_history = accident_history.lower().strip()
        location = location.lower().strip()
        
        # ─── CONDITION MAPPING ──────────────────────────────────────────
        # Map Python conditions to database enum values
        condition_map = {
            "very_good": "EXCELLENT",
            "excellent": "EXCELLENT",
            "good": "GOOD",
            "fair": "FAIR",
            "poor": "POOR"
        }
        
        condition = condition_map.get(condition, "GOOD")
        
        # ─── ACCIDENT MAPPING ───────────────────────────────────────────
        # Map Python accident values to database enum values
        accident_map = {
            "none": "NO_ACCIDENT",
            "minor": "MINOR_REPAIR",
            "major": "ACCIDENT_REPAIRED",
            "total_loss": "STRUCTURAL_DAMAGE"
        }
        
        accident_history = accident_map.get(accident_history, "NO_ACCIDENT")
        
        logger.info(f"Valuation request: variant_id={variant_id}, year={year}, mileage={mileage}, condition={condition}, accident={accident_history}")
        
        # ─── GET VEHICLE DATA FROM vehicle_master_specs ─────────────────
        
        try:
            # Try with variant_id column
            variant_response = (
                self.supabase
                .table("vehicle_master_specs")
                .select("*")
                .eq("variant_id", variant_id)
                .limit(1)
                .execute()
            )
            
            # If no result, try with id column
            if not variant_response.data:
                logger.info(f"No result with variant_id, trying with id column")
                variant_response = (
                    self.supabase
                    .table("vehicle_master_specs")
                    .select("*")
                    .eq("id", variant_id)
                    .limit(1)
                    .execute()
                )
            
            if not variant_response.data:
                logger.error(f"Vehicle variant {variant_id} not found in vehicle_master_specs")
                raise NotFoundException(f"Vehicle variant {variant_id} not found")
            
            variant_data = variant_response.data[0]
            logger.info(f"Found vehicle: {variant_data.get('make_name')} {variant_data.get('model_name')}")
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error fetching variant {variant_id}: {str(e)}")
            raise NotFoundException(f"Failed to fetch variant: {str(e)}")
        
        # ─── BUILD VEHICLE OBJECT ───────────────────────────────────────
        
        vehicle = {
            "variant_id": variant_id,
            "make": variant_data.get("make_name"),
            "model": variant_data.get("model_name"),
            "variant_name": variant_data.get("variant_name"),
            "year": year,
            "fuel_type": variant_data.get("fuel_type_name"),
            "transmission": variant_data.get("transmission_type_name"),
            "engine_size_cc": variant_data.get("engine_size_cc"),
            "body_type": variant_data.get("body_type_name"),
        }
        
        # Override with provided values if available
        if fuel_type:
            vehicle["fuel_type"] = fuel_type
        if transmission:
            vehicle["transmission"] = transmission
        
        logger.info(f"Vehicle: {vehicle['make']} {vehicle['model']} ({vehicle['variant_name']})")
        
        # ─── GET BASE PRICE ──────────────────────────────────────────────
        
        # Try to get base price from vehicle_master_specs
        base_price = 0
        price_fields = [
            "estimated_value",
            "market_value",
            "price",
            "retail_price",
            "base_price",
            "dealer_price"
        ]
        
        for field in price_fields:
            if variant_data.get(field):
                try:
                    value = float(variant_data[field])
                    if value > 0:
                        base_price = value
                        logger.info(f"Found base price from field '{field}': {base_price}")
                        break
                except (ValueError, TypeError):
                    continue
        
        if base_price <= 0:
            logger.warning(f"No base price found for variant {variant_id}, using fallback")
            base_price = self._estimate_base_price(vehicle, year)
        
        logger.info(f"Base price: KES {base_price:,.2f}")
        
        # ─── CALL DATABASE VALUATION FUNCTION ──────────────────────────
        
        try:
            # Call the database function directly with the variant_id
            result_data = (
                self.supabase
                .rpc(
                    "calculate_vehicle_value",
                    {
                        "p_crsp_id": variant_id,
                        "p_manufacture_year": year,
                        "p_mileage": mileage,
                        "p_condition": condition,
                        "p_accident_status": accident_history,
                        "p_location": location.upper()
                    }
                )
                .execute()
            )
            
            if not result_data.data:
                raise Exception("Database valuation returned no result")
            
            db_value = result_data.data[0]
            
            # Build result from database response
            result = {
                "market_value": float(db_value["final_value"]),
                "retail_value": float(db_value["final_value"]) * 1.08,
                "trade_value": float(db_value["final_value"]) * 0.85,
                "dealer_value": float(db_value["final_value"]) * 0.95,
                "confidence_score": float(db_value["confidence_score"]),
                "adjustments": {
                    "mileage": db_value["mileage_adjustment"],
                    "condition": db_value["condition_adjustment"],
                    "accident": db_value["accident_adjustment"],
                    "location": db_value["location_adjustment"],
                },
                "sample_size": 0,
                "comparables": []
            }
            
            logger.info("Valuation calculation completed successfully using database function")
            
        except Exception as e:
            logger.error(f"Database valuation failed: {e}")
            # Fallback to local calculation if database function fails
            result = self._create_fallback_valuation(vehicle, year, mileage, base_price)
        
        # ─── FIX CONFIDENCE SCORE ───────────────────────────────────────
        
        confidence_score = result.get("confidence_score", 50)
        # If confidence_score is <= 1, it's likely a decimal (0-1) that needs converting to percentage
        if confidence_score <= 1:
            confidence_score = confidence_score * 100
        
        # ─── GENERATE REPORT NUMBER ──────────────────────────────────────
        
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_suffix = secrets.token_hex(4).upper()
        report_number = f"AUTO-VAL-{timestamp}-{random_suffix}"
        
        # ─── BUILD FINAL RESPONSE ────────────────────────────────────────
        
        response = {
            "report": {
                "title": "AUTO-D Vehicle Valuation Report",
                "report_number": report_number,
                "generated_at": datetime.utcnow(),
                "status": "completed",
                "version": "1.0",
                "description": f"{vehicle['make']} {vehicle['model']} valuation",
            },
            "vehicle": {
                "variant_id": variant_id,
                "make": vehicle.get("make"),
                "model": vehicle.get("model"),
                "variant_name": vehicle.get("variant_name"),
                "year": year,
                "fuel_type": vehicle.get("fuel_type"),
                "transmission": vehicle.get("transmission"),
                "engine_size_cc": vehicle.get("engine_size_cc"),
                "body_type": vehicle.get("body_type"),
            },
            "valuation": {
                "estimated_vehicle_value": round(result.get("market_value", 0), 2),
                "retail_value": round(result.get("retail_value", result.get("market_value", 0) * 1.08), 2),
                "trade_value": round(result.get("trade_value", result.get("market_value", 0) * 0.85), 2),
                "dealer_value": round(result.get("dealer_value", result.get("market_value", 0) * 0.95), 2),
                "currency": "KES",
                "confidence_score": int(confidence_score),
                "estimated_value_range": {
                    "minimum": round(result.get("market_value", 0) * 0.90, 2),
                    "maximum": round(result.get("market_value", 0) * 1.10, 2),
                },
                "sample_size": result.get("sample_size", 0),
            },
            "comparables": result.get("comparables", []),
            "analysis": {
                "valuation_methodology": [
                    "Vehicle age",
                    "Mileage",
                    "Vehicle condition",
                    "Market comparison",
                    "Depreciation model",
                ],
                "adjustments": result.get("adjustments", {}),
                "engine_version": "AUTO-D AI Valuation Engine v1.2",
            },
            "disclaimer": (
                "This valuation is generated using the AUTO-D vehicle valuation "
                "engine and should be treated as an indicative market estimate."
            )
        }
        
        # ─── SAVE TO HISTORY ─────────────────────────────────────────────
        
        if user_id:
            await self._save_valuation_history(
                user_id=user_id,
                variant_id=variant_id,
                report_number=report_number,
                make=vehicle.get("make"),
                model=vehicle.get("model"),
                market_value=response["valuation"]["estimated_vehicle_value"],
                retail_value=response["valuation"]["retail_value"],
                trade_value=response["valuation"]["trade_value"],
                confidence_score=response["valuation"]["confidence_score"],
                year=year,
                mileage=mileage,
                location=location,
                condition=condition,
                accident_history=accident_history
            )
        
        logger.info(f"Valuation report {report_number} generated successfully")
        return response
    
    # ================================================================
    # BASE PRICE ESTIMATION
    # ================================================================
    
    def _estimate_base_price(self, vehicle: Dict[str, Any], year: int) -> float:
        """
        Estimate base price when no price is found in database.
        Uses vehicle make/model to estimate.
        """
        make = (vehicle.get("make") or "").lower()
        model = (vehicle.get("model") or "").lower()
        
        # Default prices by segment (Kenya market)
        if "toyota" in make:
            if "land cruiser" in model or "prado" in model:
                return 8500000.0
            elif "hilux" in model or "fortuner" in model:
                return 5500000.0
            elif "corolla" in model or "premio" in model or "axio" in model:
                return 3500000.0
            elif "rav4" in model or "chr" in model:
                return 4500000.0
            elif "harrier" in model or "venza" in model:
                return 5000000.0
            else:
                return 3000000.0
        elif "mercedes" in make or "bmw" in make or "audi" in make:
            return 6000000.0
        elif "nissan" in make or "honda" in make or "mazda" in make:
            return 3500000.0
        elif "subaru" in make:
            return 4000000.0
        elif "volkswagen" in make or "vw" in make:
            return 3500000.0
        elif "ford" in make:
            return 4000000.0
        elif "isuzu" in make:
            return 5000000.0
        else:
            return 2500000.0
    
    # ================================================================
    # FALLBACK VALUATION
    # ================================================================
    
    def _create_fallback_valuation(
        self,
        vehicle: Dict[str, Any],
        year: int,
        mileage: int,
        base_price: float
    ) -> Dict[str, Any]:
        """Create a fallback valuation when the engine fails."""
        logger.info("Creating fallback valuation")
        
        current_year = datetime.now().year
        age = max(0, current_year - year)
        depreciation_rate = min(0.85, age * 0.05)
        current_value = max(base_price * (1 - depreciation_rate), base_price * 0.15)
        
        # Mileage adjustment
        if mileage > 50000:
            mileage_penalty = min((mileage - 50000) / 50000 * 0.05, 0.20)
            current_value = current_value * (1 - mileage_penalty)
        
        return {
            "market_value": round(current_value, 2),
            "retail_value": round(current_value * 1.08, 2),
            "trade_value": round(current_value * 0.85, 2),
            "dealer_value": round(current_value * 0.95, 2),
            "confidence_score": 40,
            "adjustments": {
                "age": round(1 - depreciation_rate, 2),
                "mileage": 0.90 if mileage > 50000 else 1.00,
                "condition": 1.00,
                "location": 1.00,
                "accident": 1.00
            },
            "sample_size": 5,
            "comparables": []
        }
    
    # ================================================================
    # HISTORY MANAGEMENT
    # ================================================================
    
    async def _save_valuation_history(
        self,
        user_id: str,
        variant_id: int,
        report_number: str,
        make: str,
        model: str,
        market_value: float,
        retail_value: float,
        trade_value: float,
        confidence_score: int,
        year: int,
        mileage: int,
        location: str,
        condition: str,
        accident_history: str
    ) -> None:
        """Save valuation to history."""
        try:
            history_data = {
                "user_id": user_id,
                "variant_id": variant_id,
                "report_number": report_number,
                "make": make,
                "model": model,
                "market_value": market_value,
                "retail_value": retail_value,
                "trade_value": trade_value,
                "confidence_score": confidence_score,
                "year": year,
                "mileage": mileage,
                "location": location,
                "condition": condition,
                "accident_history": accident_history,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Try to save with all fields
            try:
                self.supabase.table("valuation_history").insert(history_data).execute()
                logger.info(f"Valuation history saved for user {user_id}")
            except Exception as e:
                # Try without optional columns if they don't exist
                if "accident_history" in str(e) or "location" in str(e) or "report_number" in str(e):
                    safe_history = {k: v for k, v in history_data.items() 
                                  if k not in ["accident_history", "location", "report_number"]}
                    self.supabase.table("valuation_history").insert(safe_history).execute()
                    logger.info(f"Valuation history saved (without optional fields) for user {user_id}")
                else:
                    raise
                    
        except Exception as e:
            logger.warning(f"Failed to save valuation history: {str(e)}")
    
    # ================================================================
    # HISTORY RETRIEVAL
    # ================================================================
    
    async def get_valuation_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get valuation history for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List[Dict[str, Any]]: List of valuation reports
        """
        try:
            response = (
                self.supabase
                .table("valuation_history")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Error getting valuation history: {str(e)}")
            return []
    
    async def get_valuation_by_id(
        self,
        report_id: int,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific valuation report by ID.
        
        Args:
            report_id: Report ID
            user_id: User ID for authorization
            
        Returns:
            Optional[Dict[str, Any]]: Valuation report or None
        """
        try:
            response = (
                self.supabase
                .table("valuation_history")
                .select("*")
                .eq("id", report_id)
                .eq("user_id", user_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting valuation {report_id}: {str(e)}")
            return None
    
    async def get_valuation_by_report_number(
        self,
        report_number: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a valuation report by report number.
        
        Args:
            report_number: Report number
            user_id: User ID for authorization
            
        Returns:
            Optional[Dict[str, Any]]: Valuation report or None
        """
        try:
            response = (
                self.supabase
                .table("valuation_history")
                .select("*")
                .eq("report_number", report_number)
                .eq("user_id", user_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting valuation by report number: {str(e)}")
            return None
    
    # ================================================================
    # STATISTICS
    # ================================================================
    
    async def get_valuation_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get valuation statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict[str, Any]: Statistics
        """
        try:
            history = await self.get_valuation_history(user_id)
            
            if not history:
                return {
                    "total_valuations": 0,
                    "average_value": 0.0,
                    "highest_value": 0.0,
                    "lowest_value": 0.0,
                    "last_valuation_date": None,
                    "total_value": 0.0,
                    "valuations_by_make": {},
                    "valuations_by_month": {},
                    "average_confidence": 0.0
                }
            
            values = []
            makes = {}
            months = {}
            confidences = []
            
            for item in history:
                value = item.get("market_value", 0)
                if value > 0:
                    values.append(value)
                
                confidence = item.get("confidence_score", 0)
                if confidence > 0:
                    confidences.append(confidence)
                
                # Group by make (if available)
                make = item.get("make", "Unknown")
                makes[make] = makes.get(make, 0) + 1
                
                # Group by month
                created_at = item.get("created_at")
                if created_at:
                    try:
                        date = datetime.fromisoformat(created_at)
                        month_key = date.strftime("%Y-%m")
                        months[month_key] = months.get(month_key, 0) + 1
                    except:
                        pass
            
            return {
                "total_valuations": len(history),
                "average_value": sum(values) / len(values) if values else 0.0,
                "highest_value": max(values) if values else 0.0,
                "lowest_value": min(values) if values else 0.0,
                "last_valuation_date": history[0].get("created_at") if history else None,
                "total_value": sum(values),
                "valuations_by_make": makes,
                "valuations_by_month": months,
                "average_confidence": sum(confidences) / len(confidences) if confidences else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error getting valuation stats: {str(e)}")
            return {
                "total_valuations": 0,
                "average_value": 0.0,
                "highest_value": 0.0,
                "lowest_value": 0.0,
                "last_valuation_date": None,
                "total_value": 0.0,
                "valuations_by_make": {},
                "valuations_by_month": {},
                "average_confidence": 0.0
            }
    
    # ================================================================
    # HEALTH CHECK
    # ================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the valuation service.
        
        Returns:
            Dict[str, Any]: Health status
        """
        try:
            # Check database connection
            self.supabase.table("vehicle_master_specs").select("variant_id").limit(1).execute()
            db_status = "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            db_status = "unhealthy"
        
        return {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "service": "valuation",
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_status
        }
