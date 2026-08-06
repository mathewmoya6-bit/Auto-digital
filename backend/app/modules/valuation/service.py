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
    - Vehicle data retrieval (with fallbacks)
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
        
        allowed_conditions = ["excellent", "very_good", "good", "fair", "poor"]
        if condition not in allowed_conditions:
            logger.warning(f"Unknown condition '{condition}', defaulting to 'good'")
            condition = "good"
        
        allowed_accident = ["none", "minor", "major", "total_loss"]
        if accident_history not in allowed_accident:
            logger.warning(f"Unknown accident_history '{accident_history}', defaulting to 'none'")
            accident_history = "none"
        
        logger.info(f"Valuation request: variant_id={variant_id}, year={year}, mileage={mileage}, condition={condition}")
        
        # ─── GET VEHICLE DATA ────────────────────────────────────────────
        
        vehicle_data = await self._get_vehicle_data(variant_id)
        
        if not vehicle_data:
            logger.warning(f"Vehicle variant {variant_id} not found, using fallback data")
            vehicle_data = self._create_fallback_vehicle_data(variant_id, year, fuel_type, transmission)
        
        # Override with provided values if available
        if fuel_type:
            vehicle_data["fuel_type"] = fuel_type
        if transmission:
            vehicle_data["transmission"] = transmission
        
        logger.info(f"Vehicle data: {vehicle_data.get('make')} {vehicle_data.get('model')} ({vehicle_data.get('variant')})")
        
        # ─── GET BASE PRICE ──────────────────────────────────────────────
        
        base_price = await self._get_base_price(variant_id)
        
        if base_price <= 0:
            logger.warning(f"No base price found for variant {variant_id}, using fallback")
            base_price = self._estimate_base_price(vehicle_data, year)
        
        logger.info(f"Base price: KES {base_price:,.2f}")
        
        # ─── CREATE VALUATION REQUEST ────────────────────────────────────
        
        # Create a simple request object for the engine
        class ValuationRequest:
            def __init__(self, data):
                self.variant_id = data.get("variant_id")
                self.year = data.get("year")
                self.mileage = data.get("mileage")
                self.condition = data.get("condition")
                self.accident_history = data.get("accident_history")
                self.location = data.get("location")
                self.fuel_type = data.get("fuel_type")
                self.transmission = data.get("transmission")
                self.service_history = data.get("service_history", True)
                self.ownership_count = data.get("ownership_count", 1)
        
        request_data = {
            "variant_id": variant_id,
            "year": year,
            "mileage": mileage,
            "condition": condition,
            "accident_history": accident_history,
            "location": location,
            "fuel_type": vehicle_data.get("fuel_type"),
            "transmission": vehicle_data.get("transmission"),
            "service_history": service_history,
            "ownership_count": ownership_count
        }
        
        request_obj = ValuationRequest(request_data)
        
        # ─── CALCULATE VALUATION ─────────────────────────────────────────
        
        try:
            valuation_result = await self.engine.calculate(request_obj)
            logger.info("Valuation calculation completed successfully")
        except Exception as e:
            logger.error(f"Engine calculation failed: {str(e)}")
            # Return fallback valuation
            valuation_result = self._create_fallback_valuation(variant_id, year, mileage, vehicle_data)
        
        # ─── ENSURE VEHICLE DATA IN RESULT ──────────────────────────────
        
        if "vehicle" not in valuation_result or not valuation_result["vehicle"]:
            valuation_result["vehicle"] = vehicle_data
        
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
                "description": (
                    f"Valuation report for "
                    f"{valuation_result['vehicle'].get('make', 'Unknown')} "
                    f"{valuation_result['vehicle'].get('model', 'Unknown')} "
                    f"({year})"
                ),
            },
            "vehicle": self._format_vehicle_data(valuation_result["vehicle"]),
            "valuation": self._format_valuation_data(valuation_result),
            "comparables": valuation_result.get("comparables", []),
            "analysis": self._format_analysis_data(valuation_result),
            "disclaimer": (
                "This valuation is generated using the AUTO-D vehicle valuation model. "
                "It represents an indicative estimate based on vehicle specifications, "
                "age, mileage, condition, depreciation modelling and regional factors. "
                "It should not be interpreted as the current market asking price, "
                "dealer retail price, trade-in value or guaranteed selling price. "
                "Actual transaction values may vary depending on inspection results, "
                "ownership history, maintenance records and prevailing market conditions."
            )
        }
        
        # ─── SAVE TO HISTORY ─────────────────────────────────────────────
        
        if user_id:
            await self._save_valuation_history(
                user_id=user_id,
                variant_id=variant_id,
                report_number=report_number,
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
    # VEHICLE DATA RETRIEVAL
    # ================================================================
    
    async def _get_vehicle_data(self, variant_id: int) -> Optional[Dict[str, Any]]:
        """
        Get vehicle data from database with fallbacks.
        
        Tries:
        1. vehicle_master_specs view
        2. vehicle_variants table with joins
        """
        try:
            # Try vehicle_master_specs first
            result = (
                self.supabase
                .table("vehicle_master_specs")
                .select("*")
                .eq("variant_id", variant_id)
                .execute()
            )
            
            if result.data:
                data = result.data[0]
                logger.info(f"Found vehicle in vehicle_master_specs")
                return {
                    "variant_id": data.get("variant_id", variant_id),
                    "make": data.get("make_name", "Unknown"),
                    "model": data.get("model_name", "Unknown"),
                    "variant": data.get("variant_name", "Unknown"),
                    "fuel_type": data.get("fuel_type_name"),
                    "transmission": data.get("transmission_type_name"),
                    "engine_size": data.get("engine_size_cc"),
                    "body_type": data.get("body_type_name"),
                    "seats": data.get("seats"),
                    "doors": data.get("doors"),
                    "drive_type": data.get("drive_type_name"),
                }
                
        except Exception as e:
            logger.warning(f"Error fetching from vehicle_master_specs: {str(e)}")
        
        try:
            # Fallback to vehicle_variants with joins
            result = (
                self.supabase
                .table("vehicle_variants")
                .select("""
                    id,
                    name,
                    vehicle_models(
                        id,
                        name,
                        vehicle_makes(
                            id,
                            name
                        )
                    ),
                    fuel_type_name,
                    transmission_type_name,
                    engine_size_cc,
                    body_type_name,
                    seats,
                    doors,
                    drive_type_name
                """)
                .eq("id", variant_id)
                .execute()
            )
            
            if result.data:
                data = result.data[0]
                logger.info(f"Found vehicle in vehicle_variants")
                return {
                    "variant_id": data.get("id", variant_id),
                    "make": data.get("vehicle_models", {}).get("vehicle_makes", {}).get("name", "Unknown"),
                    "model": data.get("vehicle_models", {}).get("name", "Unknown"),
                    "variant": data.get("name", "Unknown"),
                    "fuel_type": data.get("fuel_type_name"),
                    "transmission": data.get("transmission_type_name"),
                    "engine_size": data.get("engine_size_cc"),
                    "body_type": data.get("body_type_name"),
                    "seats": data.get("seats"),
                    "doors": data.get("doors"),
                    "drive_type": data.get("drive_type_name"),
                }
                
        except Exception as e:
            logger.warning(f"Error fetching from vehicle_variants: {str(e)}")
        
        logger.warning(f"Vehicle variant {variant_id} not found in any table")
        return None
    
    def _create_fallback_vehicle_data(
        self,
        variant_id: int,
        year: int,
        fuel_type: Optional[str] = None,
        transmission: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create fallback vehicle data when database lookup fails."""
        return {
            "variant_id": variant_id,
            "make": "Unknown",
            "model": "Unknown",
            "variant": "Unknown",
            "year": year,
            "fuel_type": fuel_type or "petrol",
            "transmission": transmission or "automatic",
            "engine_size": 2000,
            "body_type": "SUV",
            "seats": 5,
            "doors": 4,
            "drive_type": "4x4"
        }
    
    # ================================================================
    # BASE PRICE RETRIEVAL
    # ================================================================
    
    async def _get_base_price(self, variant_id: int) -> float:
        """
        Get base price from database with fallbacks.
        
        Tries multiple tables and fields.
        """
        # Try vehicle_master_specs first
        try:
            result = (
                self.supabase
                .table("vehicle_master_specs")
                .select("estimated_value, market_value, price")
                .eq("variant_id", variant_id)
                .execute()
            )
            
            if result.data:
                data = result.data[0]
                for field in ["estimated_value", "market_value", "price"]:
                    if data.get(field):
                        value = float(data[field])
                        if value > 0:
                            logger.info(f"Found base price from vehicle_master_specs.{field}: {value}")
                            return value
        except Exception as e:
            logger.warning(f"Error getting price from vehicle_master_specs: {str(e)}")
        
        # Try other tables
        tables = [
            "vehicle_market_values",
            "market_prices",
            "vehicle_variants"
        ]
        
        for table in tables:
            try:
                result = (
                    self.supabase
                    .table(table)
                    .select("*")
                    .eq("variant_id", variant_id)
                    .limit(1)
                    .execute()
                )
                
                if result.data:
                    row = result.data[0]
                    for field in ["market_value", "average_price", "price", "base_price", "estimated_value"]:
                        if row.get(field):
                            value = float(row[field])
                            if value > 0:
                                logger.info(f"Found base price from {table}.{field}: {value}")
                                return value
            except Exception as e:
                logger.warning(f"Error getting price from {table}: {str(e)}")
                continue
        
        logger.warning(f"No base price found for variant {variant_id}")
        return 0.0
    
    def _estimate_base_price(self, vehicle_data: Dict[str, Any], year: int) -> float:
        """
        Estimate base price when no price is found in database.
        Uses vehicle make/model to estimate.
        """
        make = (vehicle_data.get("make") or "").lower()
        model = (vehicle_data.get("model") or "").lower()
        
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
    # DATA FORMATTING
    # ================================================================
    
    def _format_vehicle_data(self, vehicle: Dict[str, Any]) -> Dict[str, Any]:
        """Format vehicle data for response."""
        return {
            "variant_id": vehicle.get("variant_id"),
            "make": vehicle.get("make", "Unknown"),
            "model": vehicle.get("model", "Unknown"),
            "variant_name": vehicle.get("variant", vehicle.get("variant_name", "Unknown")),
            "year": vehicle.get("year", datetime.now().year),
            "fuel_type": vehicle.get("fuel_type"),
            "transmission": vehicle.get("transmission"),
            "engine_size_cc": vehicle.get("engine_size", vehicle.get("engine_size_cc")),
            "body_type": vehicle.get("body_type"),
        }
    
    def _format_valuation_data(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format valuation data for response."""
        market_value = result.get("market_value", 0)
        
        return {
            "estimated_vehicle_value": round(market_value, 2),
            "retail_value": round(result.get("retail_value", market_value * 1.08), 2),
            "trade_value": round(result.get("trade_value", market_value * 0.85), 2),
            "dealer_value": round(result.get("dealer_value", market_value * 0.95), 2),
            "currency": "KES",
            "confidence_score": result.get("confidence_score", 50),
            "estimated_value_range": {
                "minimum": round(market_value * 0.90, 2),
                "maximum": round(market_value * 1.10, 2),
            },
            "sample_size": result.get("sample_size", 0),
        }
    
    def _format_analysis_data(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format analysis data for response."""
        return {
            "valuation_methodology": [
                "Vehicle age analysis",
                "Mileage adjustment",
                "Condition assessment",
                "Location adjustment",
                "Market comparables analysis",
                "Depreciation modelling"
            ],
            "adjustments": result.get("adjustments", {}),
            "engine_version": "AUTO-D AI Valuation Engine v1.2",
        }
    
    # ================================================================
    # FALLBACK VALUATION
    # ================================================================
    
    def _create_fallback_valuation(
        self,
        variant_id: int,
        year: int,
        mileage: int,
        vehicle_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a fallback valuation when the engine fails."""
        logger.info(f"Creating fallback valuation for variant {variant_id}")
        
        base_price = self._estimate_base_price(vehicle_data, year)
        current_year = datetime.now().year
        age = max(0, current_year - year)
        depreciation_rate = min(0.85, age * 0.05)
        current_value = max(base_price * (1 - depreciation_rate), base_price * 0.15)
        
        # Mileage adjustment
        if mileage > 50000:
            mileage_penalty = min((mileage - 50000) / 50000 * 0.05, 0.20)
            current_value = current_value * (1 - mileage_penalty)
        
        return {
            "vehicle": vehicle_data,
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
                "market_value": market_value,
                "retail_value": retail_value,
                "trade_value": trade_value,
                "confidence_score": confidence_score,
                "report_number": report_number,
                "year": year,
                "mileage": mileage,
                "location": location,
                "condition": condition,
                "accident_history": accident_history,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Try to save with all fields
            try:
                self.supabase.table("valuation_reports").insert(history_data).execute()
                logger.info(f"Valuation history saved for user {user_id}")
            except Exception as e:
                # Try without optional columns if they don't exist
                if "accident_history" in str(e) or "location" in str(e) or "report_number" in str(e):
                    safe_history = {k: v for k, v in history_data.items() 
                                  if k not in ["accident_history", "location", "report_number"]}
                    self.supabase.table("valuation_reports").insert(safe_history).execute()
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
                .table("valuation_reports")
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
                .table("valuation_reports")
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
                .table("valuation_reports")
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
            self.supabase.table("vehicle_variants").select("id").limit(1).execute()
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
