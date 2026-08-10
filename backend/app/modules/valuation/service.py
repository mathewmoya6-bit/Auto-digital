# app/modules/valuation/service.py
# Auto-D Kenya - Valuation Service
# ================================================================
# TYPE: MODULE - Valuation business logic
# ================================================================

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import secrets

from app.modules.valuation.engine import ValuationEngine
from app.modules.valuation.repository import ValuationRepository
from app.core.database import get_supabase
from app.core.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)


class ValuationService:
    """
    Valuation service for business logic.
    
    Handles:
    - Vehicle valuation calculation
    - Vehicle data retrieval from vehicle_base_prices (CRSP)
    - Report generation
    - History management
    - Statistics
    """
    
    def __init__(self):
        """Initialize the valuation service."""
        self.engine = ValuationEngine()
        self.repository = ValuationRepository()
        self.supabase = get_supabase()
        logger.info("ValuationService initialized")
    
    # ================================================================
    # MAIN VALUATION METHOD
    # ================================================================
    
    async def calculate_valuation(
        self,
        vehicle_crsp_id: int,  # Changed from variant_id
        year: int,
        mileage: int,
        condition: str = "good",
        accident_history: str = "none",
        location: str = "nairobi",
        fuel_type: Optional[str] = None,
        transmission: Optional[str] = None,
        ownership_count: int = 1,
        service_history: bool = True,
        user_id: Optional[str] = None,
        profit_margin_percent: float = 5.00
    ) -> Dict[str, Any]:
        """
        Calculate vehicle valuation.
        
        Args:
            vehicle_crsp_id: Vehicle CRSP ID from vehicle_base_prices
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
            profit_margin_percent: Profit margin percentage for valuation
            
        Returns:
            Dict[str, Any]: Complete valuation report matching ValuationReportResponse
            
        Raises:
            NotFoundException: If vehicle data cannot be found
            ValidationException: If input validation fails
        """
        
        logger.info(f"Starting valuation calculation for vehicle_crsp_id: {vehicle_crsp_id}")
        
        # ─── VALIDATION ──────────────────────────────────────────────────
        
        if not vehicle_crsp_id or vehicle_crsp_id <= 0:
            raise ValidationException("Valid vehicle CRSP ID required")
        
        if year < 1980 or year > datetime.now().year + 1:
            raise ValidationException(f"Invalid year: {year}")
        
        if mileage < 0:
            raise ValidationException(f"Invalid mileage: {mileage}")
        
        if profit_margin_percent < 0:
            raise ValidationException("Profit margin cannot be negative")
        
        # Normalize inputs
        condition = condition.lower().strip()
        accident_history = accident_history.lower().strip()
        location = location.upper().strip()
        
        # ─── CONDITION MAPPING ──────────────────────────────────────────
        # Map Python conditions to database enum values
        condition_map = {
            "very_good": "EXCELLENT",
            "excellent": "EXCELLENT",
            "good": "GOOD",
            "fair": "FAIR",
            "poor": "POOR"
        }
        
        condition_db = condition_map.get(condition, "GOOD")
        
        # ─── ACCIDENT MAPPING ───────────────────────────────────────────
        # Map Python accident values to database enum values
        accident_map = {
            "none": "NONE",
            "minor": "MINOR_REPAIR",
            "major": "ACCIDENT_REPAIRED",
            "total_loss": "STRUCTURAL_DAMAGE"
        }
        
        accident_history_db = accident_map.get(accident_history, "NONE")
        
        logger.info(
            f"Valuation request: vehicle_crsp_id={vehicle_crsp_id}, year={year}, "
            f"mileage={mileage}, condition={condition_db}, "
            f"accident={accident_history_db}"
        )
        
        # ─── GET VEHICLE DATA FROM CRSP ────────────────────────────────
        
        try:
            crsp_vehicle = self._get_crsp_vehicle(vehicle_crsp_id)
            crsp_price = self._get_crsp_price(crsp_vehicle)
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error fetching CRSP vehicle {vehicle_crsp_id}: {str(e)}")
            raise NotFoundException(f"Failed to fetch CRSP vehicle: {str(e)}")
        
        # ─── BUILD VEHICLE OBJECT FROM CRSP ───────────────────────────
        
        vehicle = {
            "crsp_id": vehicle_crsp_id,
            "make": (
                crsp_vehicle.get("make")
                or crsp_vehicle.get("make_name")
            ),
            "model": (
                crsp_vehicle.get("model")
                or crsp_vehicle.get("model_name")
            ),
            "variant_name": (
                crsp_vehicle.get("variant")
                or crsp_vehicle.get("variant_name")
            ),
            "fuel_type": (
                crsp_vehicle.get("crsp_fuel")
                or crsp_vehicle.get("fuel_type")
                or crsp_vehicle.get("fuel_type_name")
            ),
            "transmission": (
                crsp_vehicle.get("transmission")
                or crsp_vehicle.get("transmission_type_name")
            ),
            "engine_size_cc": (
                crsp_vehicle.get("engine_capacity_cc")
                or crsp_vehicle.get("engine_capacity")
                or crsp_vehicle.get("engine_size_cc")
            ),
            "body_type": (
                crsp_vehicle.get("body_type")
                or crsp_vehicle.get("body_type_name")
            ),
            "crsp_price": crsp_price,
            "year": year,
        }
        
        # Override with provided values if available
        if fuel_type:
            vehicle["fuel_type"] = fuel_type
        if transmission:
            vehicle["transmission"] = transmission
        
        logger.info(f"Vehicle: {vehicle['make']} {vehicle['model']} ({vehicle['variant_name']})")
        
        # ─── DETERMINE VEHICLE TYPE ───────────────────────────────────
        
        # Use the vehicle_type from request if provided, otherwise infer from body_type
        vehicle_type = "SEDAN"  # Default
        
        # If we have a body_type, try to map it
        body_type = (vehicle.get("body_type") or "").upper()
        
        if "SUV" in body_type or "CROSSOVER" in body_type:
            vehicle_type = "SUV"
        elif "PICKUP" in body_type or "TRUCK" in body_type:
            vehicle_type = "PICKUP"
        elif "VAN" in body_type or "MINIVAN" in body_type:
            vehicle_type = "VAN"
        elif "HATCHBACK" in body_type:
            vehicle_type = "HATCHBACK"
        elif "SEDAN" in body_type or "SALOON" in body_type:
            vehicle_type = "SEDAN"
        elif "COUPE" in body_type:
            vehicle_type = "COUPE"
        elif "CONVERTIBLE" in body_type:
            vehicle_type = "CONVERTIBLE"
        
        logger.info(f"Vehicle type: {vehicle_type}")
        
        # ─── CALL REPOSITORY FOR VALUATION ──────────────────────────────
        
        try:
            # Validate inputs for repository
            if vehicle_crsp_id <= 0:
                raise ValidationException("vehicle_crsp_id must be greater than zero")
            
            if year < 1900:
                raise ValidationException("Invalid manufacture year")
            
            if mileage < 0:
                raise ValidationException("Mileage cannot be negative")
            
            # Call the repository's calculation method
            result_data = self.repository.calculate_valuation(
                vehicle_crsp_id=vehicle_crsp_id,
                manufacture_year=year,
                mileage_km=mileage,
                vehicle_type=vehicle_type,
                condition_name=condition_db,
                accident_status=accident_history_db,
                location_name=location,
                profit_margin_percent=profit_margin_percent,
            )
            
            logger.info(
                f"Valuation calculation completed successfully: "
                f"final_value={result_data.get('final_value')}"
            )
            
            # Extract values from result
            final_value = float(result_data.get("final_value", 0))
            fair_market_value = float(result_data.get("fair_market_value", final_value))
            confidence_score = int(result_data.get("confidence_score", 65))
            
            # ─── GENERATE REPORT NUMBER ──────────────────────────────────
            
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            random_suffix = secrets.token_hex(4).upper()
            report_number = f"AUTO-VAL-{timestamp}-{random_suffix}"
            
            # ─── BUILD FINAL RESPONSE ────────────────────────────────────
            # Must match ValuationReportResponse schema
            
            now = datetime.utcnow()
            
            # Build the vehicle info with crsp_id (required by schema)
            vehicle_info = {
                "crsp_id": vehicle_crsp_id,
                "variant_id": vehicle_crsp_id,
                "make": vehicle.get("make"),
                "model": vehicle.get("model"),
                "variant_name": vehicle.get("variant_name"),
                "year": year,
                "fuel_type": vehicle.get("fuel_type"),
                "transmission": vehicle.get("transmission"),
                "engine_size_cc": vehicle.get("engine_size_cc"),
                "body_type": vehicle.get("body_type"),
            }
            
            response = {
                # Report metadata - flattened
                "report_number": report_number,
                "generated_at": now,
                "status": "completed",
                "version": "2.0",
                
                # Vehicle information
                "vehicle": vehicle_info,
                
                # Valuation results
                "valuation": {
                    "vehicle": vehicle_info,
                    "market_value": round(final_value, 2),
                    "retail_value": round(final_value * 1.08, 2),
                    "trade_value": round(final_value * 0.85, 2),
                    "dealer_value": round(final_value * 0.95, 2),
                    "recommended_selling_price": round(final_value * 1.10, 2),
                    "currency": "KES",
                    "confidence_score": confidence_score,
                    "estimated_value_range": {
                        "minimum": round(final_value * 0.90, 2),
                        "maximum": round(final_value * 1.10, 2),
                    },
                    "sample_size": 0,
                    "adjustments": [],
                    "comparables": [],
                    "warnings": [],
                    "calculated_at": now,
                },
                
                # Flattened value fields (required by ValuationReportResponse)
                "market_value": round(final_value, 2),
                "retail_value": round(final_value * 1.08, 2),
                "trade_value": round(final_value * 0.85, 2),
                "dealer_value": round(final_value * 0.95, 2),
                "confidence_score": confidence_score,
                "calculated_at": now,
                
                # Adjustments and comparables
                "adjustments": [],
                "comparables": [],
                
                # Analysis
                "recommendation": None,
                "warnings": [],
                
                # Currency
                "currency": "KES",
                
                # Depreciation (optional)
                "depreciation": None,
                
                # Disclaimer
                "disclaimer": (
                    "This valuation is generated using the AUTO-D vehicle valuation "
                    "engine and should be treated as an indicative market estimate."
                )
            }
            
            # ─── SAVE TO HISTORY ─────────────────────────────────────────
            
            if user_id:
                await self._save_valuation_history(
                    user_id=user_id,
                    variant_id=vehicle_crsp_id,
                    report_number=report_number,
                    make=vehicle.get("make"),
                    model=vehicle.get("model"),
                    market_value=response["market_value"],
                    retail_value=response["retail_value"],
                    trade_value=response["trade_value"],
                    confidence_score=response["confidence_score"],
                    year=year,
                    mileage=mileage,
                    location=location,
                    condition=condition_db,
                    accident_history=accident_history_db
                )
            
            logger.info(f"Valuation report {report_number} generated successfully")
            return response
            
        except (NotFoundException, ValidationException):
            raise
        except ValueError as e:
            logger.error(f"Validation error in valuation calculation: {str(e)}")
            raise ValidationException(str(e))
        except Exception as e:
            logger.error(f"Valuation calculation failed: {str(e)}")
            # Create fallback valuation
            base_price = self._estimate_base_price(vehicle, year)
            fallback_result = self._create_fallback_valuation(
                vehicle,
                year,
                mileage,
                base_price
            )
            
            # Build response with fallback
            fallback_response = self._build_response_from_result(
                fallback_result,
                vehicle,
                vehicle_crsp_id,
                year
            )
            
            return fallback_response
    
    # ================================================================
    # CRSP VEHICLE LOOKUP
    # ================================================================
    
    def _get_crsp_vehicle(
        self,
        vehicle_crsp_id: int
    ) -> Dict[str, Any]:
        """
        Get vehicle directly from the new CRSP master database.
        """
        try:
            response = (
                self.supabase
                .table("vehicle_base_prices")
                .select("*")
                .eq("crsp_id", vehicle_crsp_id)
                .limit(1)
                .execute()
            )

            if not response.data:
                raise NotFoundException(
                    f"CRSP vehicle {vehicle_crsp_id} not found"
                )

            vehicle = response.data[0]

            logger.info(
                "CRSP vehicle found: crsp_id=%s make=%s model=%s",
                vehicle_crsp_id,
                vehicle.get("make"),
                vehicle.get("model"),
            )

            return vehicle

        except NotFoundException:
            raise

        except Exception as exc:
            logger.exception(
                "Failed to fetch CRSP vehicle %s",
                vehicle_crsp_id,
            )

            raise NotFoundException(
                f"Failed to fetch CRSP vehicle {vehicle_crsp_id}: {exc}"
            )
    
    # ================================================================
    # CRSP PRICE EXTRACTION
    # ================================================================
    
    def _get_crsp_price(
        self,
        crsp_vehicle: Dict[str, Any]
    ) -> float:
        """
        Extract the CRSP base price from the new CRSP record.
        """
        price_fields = (
            "crsp_price",
            "crsp_kes",
            "base_price",
            "price",
            "market_value",
            "retail_price",
        )

        for field in price_fields:
            value = crsp_vehicle.get(field)

            if value is None:
                continue

            try:
                price = float(value)

                if price > 0:
                    return price

            except (TypeError, ValueError):
                continue

        logger.error(
            "CRSP vehicle %s has no valid price: %s",
            crsp_vehicle.get("crsp_id"),
            crsp_vehicle,
        )

        raise ValidationException(
            f"CRSP vehicle {crsp_vehicle.get('crsp_id')} "
            "does not have a valid CRSP price"
        )
    
    # ================================================================
    # RESPONSE BUILDER
    # ================================================================
    
    def _build_response_from_result(
        self,
        result: Dict[str, Any],
        vehicle: Dict[str, Any],
        vehicle_crsp_id: int,
        year: int
    ) -> Dict[str, Any]:
        """Build a valuation response from a result dictionary."""
        
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_suffix = secrets.token_hex(4).upper()
        report_number = f"AUTO-VAL-{timestamp}-{random_suffix}"
        
        market_value = result.get("market_value", 0)
        now = datetime.utcnow()
        
        # Build vehicle info with crsp_id
        vehicle_info = {
            "crsp_id": vehicle_crsp_id,
            "variant_id": vehicle_crsp_id,
            "make": vehicle.get("make"),
            "model": vehicle.get("model"),
            "variant_name": vehicle.get("variant_name"),
            "year": year,
            "fuel_type": vehicle.get("fuel_type"),
            "transmission": vehicle.get("transmission"),
            "engine_size_cc": vehicle.get("engine_size_cc"),
            "body_type": vehicle.get("body_type"),
        }
        
        return {
            # Report metadata - flattened
            "report_number": report_number,
            "generated_at": now,
            "status": "completed",
            "version": "2.0",
            
            # Vehicle information
            "vehicle": vehicle_info,
            
            # Valuation results
            "valuation": {
                "vehicle": vehicle_info,
                "market_value": round(market_value, 2),
                "retail_value": round(market_value * 1.08, 2),
                "trade_value": round(market_value * 0.85, 2),
                "dealer_value": round(market_value * 0.95, 2),
                "recommended_selling_price": round(market_value * 1.10, 2),
                "currency": "KES",
                "confidence_score": int(result.get("confidence_score", 40)),
                "estimated_value_range": {
                    "minimum": round(market_value * 0.90, 2),
                    "maximum": round(market_value * 1.10, 2),
                },
                "sample_size": result.get("sample_size", 0),
                "adjustments": [],
                "comparables": result.get("comparables", []),
                "warnings": [],
                "calculated_at": now,
            },
            
            # Flattened value fields
            "market_value": round(market_value, 2),
            "retail_value": round(market_value * 1.08, 2),
            "trade_value": round(market_value * 0.85, 2),
            "dealer_value": round(market_value * 0.95, 2),
            "confidence_score": int(result.get("confidence_score", 40)),
            "calculated_at": now,
            
            # Adjustments and comparables
            "adjustments": [],
            "comparables": result.get("comparables", []),
            
            # Analysis
            "recommendation": None,
            "warnings": [],
            
            # Currency
            "currency": "KES",
            
            # Depreciation (optional)
            "depreciation": None,
            
            # Disclaimer
            "disclaimer": (
                "This valuation is generated using the AUTO-D vehicle valuation "
                "engine and should be treated as an indicative market estimate."
            )
        }
    
    # ================================================================
    # BASE PRICE ESTIMATION (Fallback)
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
            # Check database connection using vehicle_base_prices
            self.supabase.table("vehicle_base_prices").select("crsp_id").limit(1).execute()
            db_status = "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            db_status = "unhealthy"
        
        return {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "service": "valuation",
            "version": "2.0",
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_status
        }
