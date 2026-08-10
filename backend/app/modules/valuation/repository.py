# app/modules/valuation/repository.py
# ================================================================
# Auto-D Kenya - Valuation Repository
# ================================================================
# TYPE: MODULE - Valuation data access layer
# ================================================================

import logging
from typing import Any, Dict, Optional

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)


class ValuationRepository:
    """
    Valuation repository for database operations.
    
    Handles:
    - CRSP vehicle lookup
    - Base price extraction
    - Valuation calculation via PostgreSQL RPC
    """
    
    def __init__(self):
        """Initialize the repository."""
        self.supabase = get_supabase()
        logger.info("ValuationRepository initialized")
    
    # ================================================================
    # MAIN VALUATION CALCULATION
    # ================================================================
    
    def calculate_valuation(
        self,
        vehicle_crsp_id: int,
        manufacture_year: int,
        mileage_km: int,
        vehicle_type: str = "SEDAN",
        condition_name: str = "GOOD",
        accident_status: str = "NONE",
        location_name: str = "NAIROBI",
        profit_margin_percent: float = 5.00,
    ) -> Dict[str, Any]:
        """
        Calculate vehicle valuation using PostgreSQL RPC.
        
        Args:
            vehicle_crsp_id: CRSP vehicle ID
            manufacture_year: Vehicle manufacture year
            mileage_km: Vehicle mileage in kilometres
            vehicle_type: Vehicle type (SEDAN, SUV, etc.)
            condition_name: Vehicle condition (EXCELLENT, GOOD, FAIR, POOR)
            accident_status: Accident status (NONE, MINOR_REPAIR, etc.)
            location_name: Vehicle location
            profit_margin_percent: Profit margin percentage
            
        Returns:
            Dict[str, Any]: Valuation result from database
            
        Raises:
            ValidationException: If inputs are invalid
            NotFoundException: If CRSP vehicle not found
            ValueError: If valuation calculation fails
        """
        
        # ─── VALIDATION ──────────────────────────────────────────────────
        
        if vehicle_crsp_id <= 0:
            raise ValidationException("Invalid CRSP vehicle ID")
        
        if manufacture_year < 1900 or manufacture_year > 2100:
            raise ValidationException(f"Invalid manufacture year: {manufacture_year}")
        
        if mileage_km < 0:
            raise ValidationException(f"Invalid mileage: {mileage_km}")
        
        if profit_margin_percent < 0 or profit_margin_percent > 100:
            raise ValidationException(f"Invalid profit margin: {profit_margin_percent}")
        
        logger.info(
            "Calculating valuation for CRSP ID %s, year %s, mileage %s",
            vehicle_crsp_id,
            manufacture_year,
            mileage_km,
        )
        
        # ─── GET CRSP VEHICLE RECORD ────────────────────────────────────
        
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
            
            crsp_record = response.data[0]
            
            logger.info(
                "CRSP vehicle found: crsp_id=%s, make=%s, model=%s",
                vehicle_crsp_id,
                crsp_record.get("make"),
                crsp_record.get("model"),
            )
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error fetching CRSP vehicle {vehicle_crsp_id}: {str(e)}")
            raise NotFoundException(f"Failed to fetch CRSP vehicle: {str(e)}")
        
        # ─── EXTRACT BASE PRICE ─────────────────────────────────────────
        
        base_price = self._extract_base_price(crsp_record, vehicle_crsp_id)
        
        logger.info(f"CRSP base price: {base_price}")
        
        # ─── CALL VALUATION RPC ──────────────────────────────────────────
        
        try:
            params = {
                "p_vehicle_crsp_id": vehicle_crsp_id,
                "p_manufacture_year": manufacture_year,
                "p_mileage_km": mileage_km,
                "p_vehicle_type": vehicle_type.upper().strip(),
                "p_condition_name": condition_name.upper().strip(),
                "p_accident_status": accident_status.upper().strip(),
                "p_location_name": location_name.upper().strip(),
                "p_profit_margin_percent": float(profit_margin_percent),
            }
            
            logger.info(
                "Calling calculate_vehicle_valuation with params: %s",
                params,
            )
            
            response = (
                self.supabase
                .rpc(
                    "calculate_vehicle_valuation",
                    params,
                )
                .execute()
            )
            
            if not response.data:
                raise ValueError(
                    f"No valuation result returned for CRSP {vehicle_crsp_id}"
                )
            
            # PostgreSQL RETURNS TABLE normally returns a list
            result = response.data[0]
            
            logger.info(
                "Valuation calculation completed: final_value=%s, confidence=%s",
                result.get("final_value"),
                result.get("confidence_score"),
            )
            
            # ─── EXTRACT VALUATION VALUE ────────────────────────────────
            
            final_value = self._extract_valuation_value(result, base_price)
            
            logger.info(f"Final valuation value: {final_value}")
            
            # ─── ENSURE CONFIDENCE SCORE IS VALID ───────────────────────
            
            confidence_score = result.get("confidence_score")
            
            if confidence_score is None:
                confidence_score = 65
            else:
                try:
                    confidence_score = int(confidence_score)
                except (TypeError, ValueError):
                    confidence_score = 65
            
            # If final value is zero or negative, set confidence to 0
            if final_value <= 0:
                confidence_score = 0
            
            # ─── BUILD RESPONSE ──────────────────────────────────────────
            
            return {
                # Core valuation
                "final_value": final_value,
                "confidence_score": confidence_score,
                
                # CRSP reference
                "crsp_value": base_price,
                "crsp_vehicle": crsp_record,
                
                # Database result fields
                "fair_market_value": result.get("fair_market_value", final_value),
                "market_value": result.get("market_value", final_value),
                "current_value": result.get("current_value", final_value),
                "estimated_value": result.get("estimated_value", final_value),
                
                # Depreciation
                "depreciation_rate": result.get("depreciation_rate", 0),
                "depreciation_value": result.get("depreciation_value", 0),
                "value_after_depreciation": result.get("value_after_depreciation", final_value),
                
                # Adjustments
                "mileage_adjustment": result.get("mileage_adjustment", 0),
                "condition_adjustment": result.get("condition_adjustment", 0),
                "accident_adjustment": result.get("accident_adjustment", 0),
                "location_adjustment": result.get("location_adjustment", 0),
                "market_adjustment": result.get("market_adjustment", 0),
                
                # Profit
                "profit_margin_percent": result.get("profit_margin_percent", profit_margin_percent),
                "profit_margin_value": result.get("profit_margin_value", 0),
                "recommended_selling_price": result.get("recommended_selling_price", final_value * 1.10),
                
                # Reference
                "valuation_reference": result.get("valuation_reference"),
                
                # Metadata
                "sample_size": result.get("sample_size", 0),
                "vehicle_age": result.get("vehicle_age", 0),
                "manufacture_year": manufacture_year,
                "mileage_km": mileage_km,
                "condition_name": condition_name,
                "accident_status": accident_status,
                "location_name": location_name,
                "vehicle_type": vehicle_type,
                "profit_margin_percent": profit_margin_percent,
            }
            
        except (NotFoundException, ValidationException, ValueError):
            raise
        except Exception as e:
            logger.error(f"Valuation calculation failed: {str(e)}")
            raise ValueError(f"Valuation calculation failed: {str(e)}")
    
    # ================================================================
    # PRICE EXTRACTION METHODS
    # ================================================================
    
    def _extract_base_price(
        self,
        crsp_record: Dict[str, Any],
        vehicle_crsp_id: int
    ) -> float:
        """
        Extract the base price from a CRSP record.
        
        Args:
            crsp_record: CRSP vehicle record
            vehicle_crsp_id: CRSP ID for error messages
            
        Returns:
            float: Base price
            
        Raises:
            ValidationException: If no valid price found
        """
        
        price_fields = (
            "crsp_price",
            "crsp_kes",
            "base_price",
            "price",
            "market_value",
            "retail_price",
            "estimated_value",
            "dealer_price",
            "trade_value",
        )
        
        for field in price_fields:
            value = crsp_record.get(field)
            
            if value is not None:
                try:
                    price = float(value)
                    
                    if price > 0:
                        logger.info(f"Base price found in field '{field}': {price}")
                        return price
                        
                except (TypeError, ValueError):
                    continue
        
        logger.error(
            "CRSP vehicle %s has no valid price in any field: %s",
            vehicle_crsp_id,
            crsp_record,
        )
        
        raise ValidationException(
            f"CRSP vehicle {vehicle_crsp_id} does not have a valid base price"
        )
    
    @staticmethod
    def _extract_valuation_value(
        result_data: Dict[str, Any],
        crsp_price: Optional[float] = None,
    ) -> float:
        """
        Extract a valid valuation value from repository result.
        
        Args:
            result_data: Database result dictionary
            crsp_price: Fallback CRSP price
            
        Returns:
            float: Valid valuation value
            
        Raises:
            ValidationException: If no valid value found
        """
        
        # Try fields in order of preference
        fields = (
            "final_value",
            "estimated_vehicle_value",
            "estimated_value",
            "market_value",
            "fair_market_value",
            "current_value",
            "calculated_value",
            "value_after_depreciation",
            "recommended_selling_price",
        )
        
        for field in fields:
            value = result_data.get(field)
            
            if value is None:
                continue
            
            try:
                value = float(value)
                
                if value > 0:
                    logger.info(f"Valuation value extracted from field '{field}': {value}")
                    return value
                    
            except (TypeError, ValueError):
                continue
        
        # Fallback to CRSP price if available
        if crsp_price is not None:
            try:
                price = float(crsp_price)
                
                if price > 0:
                    logger.warning(
                        "Repository returned no usable valuation. "
                        "Using CRSP price as fallback: %.2f",
                        price,
                    )
                    return price
                    
            except (TypeError, ValueError):
                pass
        
        logger.error(
            "No valid valuation value found in result: %s",
            result_data,
        )
        
        raise ValidationException(
            "No valid valuation value returned from CRSP valuation engine"
        )
    
    # ================================================================
    # BULK VALUATION
    # ================================================================
    
    def calculate_bulk_valuations(
        self,
        requests: list,
    ) -> list:
        """
        Calculate multiple valuations in bulk.
        
        Args:
            requests: List of valuation request dictionaries
            
        Returns:
            list: List of valuation results
        """
        
        results = []
        
        for request in requests:
            try:
                result = self.calculate_valuation(
                    vehicle_crsp_id=request.get("vehicle_crsp_id"),
                    manufacture_year=request.get("manufacture_year"),
                    mileage_km=request.get("mileage_km", 0),
                    vehicle_type=request.get("vehicle_type", "SEDAN"),
                    condition_name=request.get("condition_name", "GOOD"),
                    accident_status=request.get("accident_status", "NONE"),
                    location_name=request.get("location_name", "NAIROBI"),
                    profit_margin_percent=request.get("profit_margin_percent", 5.00),
                )
                
                results.append({
                    "success": True,
                    "result": result,
                })
                
            except Exception as e:
                results.append({
                    "success": False,
                    "error": str(e),
                    "vehicle_crsp_id": request.get("vehicle_crsp_id"),
                })
        
        return results
    
    # ================================================================
    # CRSP VEHICLE LOOKUP
    # ================================================================
    
    def get_crsp_vehicle(
        self,
        vehicle_crsp_id: int,
    ) -> Dict[str, Any]:
        """
        Get a CRSP vehicle record by ID.
        
        Args:
            vehicle_crsp_id: CRSP vehicle ID
            
        Returns:
            Dict[str, Any]: CRSP vehicle record
            
        Raises:
            NotFoundException: If vehicle not found
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
            
            return response.data[0]
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error fetching CRSP vehicle: {str(e)}")
            raise NotFoundException(f"Failed to fetch CRSP vehicle: {str(e)}")


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    "ValuationRepository",
]
