# app/modules/valuation/service.py
# ================================================================
# Auto-D Kenya - Valuation Service
# ================================================================

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import secrets

from app.modules.valuation.repository import ValuationRepository
from app.core.exceptions import NotFoundException, ValidationException
from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class ValuationService:
    """Valuation service for Auto-D Kenya."""
    
    def __init__(self):
        self.repository = ValuationRepository()
        self.supabase = get_supabase()
        logger.info("ValuationService initialized")
    
    # ================================================================
    # MAIN VALUATION
    # ================================================================
    
    def calculate_valuation(
        self,
        make: str,
        model: str,
        year: int,
        mileage: int = 0,
        condition: str = "good",
        accident_history: str = "none",
        previous_owners: int = 1,
        location: str = "nairobi",
        fuel_type: Optional[str] = None,
        transmission: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        trim: Optional[str] = None,
        engine_capacity: Optional[str] = None,
        profit_margin: float = 0.0,
        crsp_id: Optional[int] = None,
        crsp_kes: Optional[float] = None,
        variant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Calculate vehicle valuation based on frontend payload.
        
        Args:
            make: Vehicle make
            model: Vehicle model
            year: Manufacture year
            mileage: Odometer reading
            condition: Vehicle condition
            accident_history: Accident history
            previous_owners: Number of previous owners
            location: Vehicle location
            fuel_type: Fuel type
            transmission: Transmission type
            vehicle_type: Vehicle type
            trim: Vehicle trim
            engine_capacity: Engine capacity
            profit_margin: Profit margin percentage
            crsp_id: Optional CRSP ID
            crsp_kes: Optional CRSP price
            variant_id: Optional variant ID (for lookup)
            
        Returns:
            Dict[str, Any]: Valuation results
        """
        logger.info(f"Calculating valuation for make='{make}', model='{model}', year={year}")
        logger.info(f"Additional params: crsp_id={crsp_id}, variant_id={variant_id}")
        
        # ─── Try to resolve make and model if missing ──────────────────
        resolved_make = make
        resolved_model = model
        
        # If make or model is missing, try to look them up
        if not resolved_make or not resolved_model:
            logger.warning(f"Make or model missing: make='{resolved_make}', model='{resolved_model}'")
            
            # Try using crsp_id first
            lookup_id = crsp_id or variant_id
            if lookup_id:
                logger.info(f"Attempting to look up make/model from ID: {lookup_id}")
                
                # Try vehicle_master_specs first (most complete data)
                try:
                    response = (
                        self.supabase
                        .table("vehicle_master_specs")
                        .select("make_name, model_name, variant_name")
                        .eq("variant_id", lookup_id)
                        .limit(1)
                        .execute()
                    )
                    if response.data:
                        resolved_make = response.data[0].get("make_name") or resolved_make
                        resolved_model = response.data[0].get("model_name") or resolved_model
                        if not trim:
                            trim = response.data[0].get("variant_name") or trim
                        logger.info(f"Found from master_specs: make='{resolved_make}', model='{resolved_model}'")
                except Exception as e:
                    logger.warning(f"Failed to lookup in master_specs: {e}")
            
            # If still missing, try CRSP table
            if not resolved_make or not resolved_model:
                try:
                    # Try vehicle_crsp_lookup
                    response = (
                        self.supabase
                        .table("vehicle_crsp_lookup")
                        .select("make, model, trim_level, engine_capacity, fuel, transmission")
                        .eq("crsp_id", lookup_id)
                        .limit(1)
                        .execute()
                    )
                    if not response.data:
                        response = (
                            self.supabase
                            .table("vehicle_crsp_lookup")
                            .select("make, model, trim_level, engine_capacity, fuel, transmission")
                            .eq("id", lookup_id)
                            .limit(1)
                            .execute()
                        )
                    if response.data:
                        resolved_make = response.data[0].get("make") or resolved_make
                        resolved_model = response.data[0].get("model") or resolved_model
                        if not trim:
                            trim = response.data[0].get("trim_level") or trim
                        if not engine_capacity:
                            engine_capacity = response.data[0].get("engine_capacity") or engine_capacity
                        if not fuel_type:
                            fuel_type = response.data[0].get("fuel") or fuel_type
                        if not transmission:
                            transmission = response.data[0].get("transmission") or transmission
                        logger.info(f"Found from CRSP: make='{resolved_make}', model='{resolved_model}'")
                except Exception as e:
                    logger.warning(f"Failed to lookup in CRSP: {e}")
        
        # ─── Final validation ──────────────────────────────────────────
        # If still empty, use placeholders
        if not resolved_make:
            resolved_make = "Unknown"
            logger.warning("Using 'Unknown' for make")
        if not resolved_model:
            resolved_model = "Unknown"
            logger.warning("Using 'Unknown' for model")
        
        # Validate year
        if year < 1900 or year > datetime.now(timezone.utc).year + 1:
            raise ValidationException(f"Invalid year: {year}")
        
        if mileage < 0:
            raise ValidationException(f"Invalid mileage: {mileage}")
        
        # ─── Normalize inputs ────────────────────────────────────────
        condition = condition.lower().strip()
        accident_history = accident_history.lower().strip()
        location = location.lower().strip()
        
        # ─── Calculate Valuation ──────────────────────────────────────
        result = self.repository.calculate_valuation(
            make=resolved_make,
            model=resolved_model,
            year=year,
            mileage=mileage,
            condition=condition,
            accident_history=accident_history,
            previous_owners=previous_owners,
            location=location,
            fuel_type=fuel_type,
            transmission=transmission,
            vehicle_type=vehicle_type,
            trim=trim,
            engine_capacity=engine_capacity,
            profit_margin=profit_margin,
            crsp_id=crsp_id,
            crsp_kes=crsp_kes,
        )
        
        # Add resolved values to result
        if result.get("vehicle"):
            result["vehicle"]["make"] = resolved_make
            result["vehicle"]["model"] = resolved_model
            if trim:
                result["vehicle"]["trim"] = trim
        
        logger.info(f"Valuation complete: {result.get('estimated_value', 0)} KES")
        return result
    
    # ================================================================
    # BULK VALUATION
    # ================================================================
    
    def calculate_bulk_valuations(
        self,
        requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate multiple valuations."""
        results = []
        for req in requests:
            try:
                result = self.calculate_valuation(**req)
                results.append({"success": True, "result": result})
            except Exception as e:
                logger.error(f"Bulk valuation failed: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "vehicle": f"{req.get('make', 'Unknown')} {req.get('model', 'Unknown')}"
                })
        return results
    
    # ================================================================
    # CRSP LOOKUP HELPERS
    # ================================================================
    
    def search_crsp(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        """Search CRSP records."""
        return self.repository.search_crsp(
            make=make,
            model=model,
            manufacture_year=year,
            limit=limit,
        )
    
    def get_crsp_vehicle(self, crsp_id: int) -> Optional[Dict[str, Any]]:
        """Get CRSP vehicle by ID."""
        record = self.repository.get_crsp_by_id(crsp_id)
        if not record:
            record = self.repository.get_crsp_by_crsp_id(crsp_id)
        return record
    
    def get_makes(self) -> List[str]:
        """Get all makes."""
        return self.repository.get_all_makes()
    
    def get_models(self, make: str) -> List[str]:
        """Get models for a make."""
        return self.repository.get_models_by_make(make)
    
    def get_years(self, make: str, model: str) -> List[int]:
        """Get years for a model."""
        return self.repository.get_years_by_model(make, model)
    
    def get_trims(self, make: str, model: str, year: int) -> List[Dict[str, Any]]:
        """Get trims for a model and year."""
        return self.repository.get_trims_by_model_year(make, model, year)
    
    # ================================================================
    # HISTORY MANAGEMENT
    # ================================================================
    
    async def save_valuation_history(
        self,
        user_id: str,
        result: Dict[str, Any],
        request: Dict[str, Any],
    ) -> None:
        """Save valuation to history."""
        try:
            supabase = get_supabase()
            
            # Get make and model from result or request
            vehicle = result.get("vehicle", {})
            make = request.get("make") or vehicle.get("make") or "Unknown"
            model = request.get("model") or vehicle.get("model") or "Unknown"
            
            history_data = {
                "user_id": user_id,
                "make": make,
                "model": model,
                "year": request.get("year", 0),
                "mileage": request.get("mileage", 0),
                "market_value": result.get("market_value", 0),
                "retail_value": result.get("retail_value", 0),
                "trade_value": result.get("trade_value", 0),
                "confidence_score": result.get("confidence_score", 0),
                "valuation_date": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            
            supabase.table("valuation_history").insert(history_data).execute()
            logger.info(f"Valuation history saved for user {user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to save valuation history: {str(e)}")
    
    async def get_valuation_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get valuation history for a user."""
        try:
            supabase = get_supabase()
            response = (
                supabase
                .table("valuation_history")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []
    
    async def get_valuation_by_id(self, report_id: int, user_id: str) -> Optional[Dict[str, Any]]:
        """Get valuation by ID."""
        try:
            supabase = get_supabase()
            response = (
                supabase
                .table("valuation_history")
                .select("*")
                .eq("id", report_id)
                .eq("user_id", user_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to get valuation {report_id}: {e}")
            return None
    
    # ================================================================
    # STATISTICS
    # ================================================================
    
    async def get_valuation_stats(self, user_id: str) -> Dict[str, Any]:
        """Get valuation statistics."""
        history = await self.get_valuation_history(user_id)
        
        if not history:
            return {
                "total_valuations": 0,
                "average_value": 0.0,
                "average_confidence_score": 0.0,
                "min_market_value": 0.0,
                "max_market_value": 0.0,
                "currency": "KES",
            }
        
        values = [h.get("market_value", 0) for h in history if h.get("market_value", 0) > 0]
        confidences = [h.get("confidence_score", 0) for h in history if h.get("confidence_score", 0) > 0]
        
        return {
            "total_valuations": len(history),
            "average_value": sum(values) / len(values) if values else 0.0,
            "average_confidence_score": sum(confidences) / len(confidences) if confidences else 0.0,
            "min_market_value": min(values) if values else 0.0,
            "max_market_value": max(values) if values else 0.0,
            "currency": "KES",
        }
    
    # ================================================================
    # HEALTH CHECK
    # ================================================================
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for valuation service."""
        try:
            self.repository.get_all_makes()
            db_status = "healthy"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            db_status = "unhealthy"
        
        return {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "service": "valuation",
            "version": "2.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": db_status,
        }
