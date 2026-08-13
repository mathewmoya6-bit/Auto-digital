# app/modules/valuation/repository.py
# ================================================================
# Auto-D Kenya - Valuation Repository
# ================================================================

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)


class ValuationRepository:
    """Valuation data access layer."""
    
    CRSP_TABLE = "vehicle_crsp_lookup"
    
    def __init__(self):
        self.supabase = get_supabase()
        logger.info("ValuationRepository initialized")
    
    # ================================================================
    # CRSP LOOKUP
    # ================================================================
    
    def search_crsp(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        manufacture_year: Optional[int] = None,
        trim: Optional[str] = None,
        engine_capacity: Optional[str] = None,
        fuel: Optional[str] = None,
        transmission: Optional[str] = None,
        body_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search CRSP records with filters."""
        try:
            query = self.supabase.table(self.CRSP_TABLE).select("*")
            
            if make:
                query = query.ilike("make", f"%{make}%")
            if model:
                query = query.ilike("model", f"%{model}%")
            if manufacture_year:
                query = query.eq("manufacture_year", manufacture_year)
            if trim:
                query = query.ilike("trim_level", f"%{trim}%")
            if engine_capacity:
                query = query.eq("engine_capacity", engine_capacity)
            if fuel:
                query = query.ilike("fuel", f"%{fuel}%")
            if transmission:
                query = query.ilike("transmission", f"%{transmission}%")
            if body_type:
                query = query.ilike("body_type", f"%{body_type}%")
            
            query = query.order("crsp_kes", desc=True)
            query = query.limit(limit)
            
            response = query.execute()
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"CRSP search failed: {e}")
            return []
    
    def get_crsp_by_id(self, crsp_id: int) -> Optional[Dict[str, Any]]:
        """Get CRSP record by ID."""
        try:
            response = (
                self.supabase
                .table(self.CRSP_TABLE)
                .select("*")
                .eq("id", crsp_id)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to get CRSP by ID {crsp_id}: {e}")
            return None
    
    def get_crsp_by_crsp_id(self, crsp_id: int) -> Optional[Dict[str, Any]]:
        """Get CRSP record by crsp_id column."""
        try:
            response = (
                self.supabase
                .table(self.CRSP_TABLE)
                .select("*")
                .eq("crsp_id", crsp_id)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to get CRSP by crsp_id {crsp_id}: {e}")
            return None
    
    def get_crsp_by_make_model_year(
        self,
        make: str,
        model: str,
        year: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get best matching CRSP record by make, model, year."""
        try:
            query = (
                self.supabase
                .table(self.CRSP_TABLE)
                .select("*")
                .ilike("make", f"%{make}%")
                .ilike("model", f"%{model}%")
            )
            
            if year:
                query = query.eq("manufacture_year", year)
            
            query = query.order("crsp_kes", desc=True).limit(1)
            response = query.execute()
            
            if response.data:
                return response.data[0]
            
            # Try without year
            query = (
                self.supabase
                .table(self.CRSP_TABLE)
                .select("*")
                .ilike("make", f"%{make}%")
                .ilike("model", f"%{model}%")
                .order("crsp_kes", desc=True)
                .limit(1)
            )
            response = query.execute()
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"Failed to get CRSP by make/model: {e}")
            return None
    
    def get_all_makes(self) -> List[str]:
        """Get all unique makes from CRSP."""
        try:
            response = (
                self.supabase
                .table(self.CRSP_TABLE)
                .select("make")
                .order("make")
                .execute()
            )
            makes = set()
            for row in response.data or []:
                if row.get("make"):
                    makes.add(row["make"])
            return sorted(list(makes))
        except Exception as e:
            logger.error(f"Failed to get makes: {e}")
            return []
    
    def get_models_by_make(self, make: str) -> List[str]:
        """Get all models for a make."""
        try:
            response = (
                self.supabase
                .table(self.CRSP_TABLE)
                .select("model")
                .ilike("make", f"%{make}%")
                .order("model")
                .execute()
            )
            models = set()
            for row in response.data or []:
                if row.get("model"):
                    models.add(row["model"])
            return sorted(list(models))
        except Exception as e:
            logger.error(f"Failed to get models for {make}: {e}")
            return []
    
    def get_years_by_model(self, make: str, model: str) -> List[int]:
        """Get all years for a model."""
        try:
            response = (
                self.supabase
                .table(self.CRSP_TABLE)
                .select("manufacture_year")
                .ilike("make", f"%{make}%")
                .ilike("model", f"%{model}%")
                .order("manufacture_year", desc=True)
                .execute()
            )
            years = set()
            for row in response.data or []:
                if row.get("manufacture_year"):
                    years.add(row["manufacture_year"])
            return sorted(list(years), reverse=True)
        except Exception as e:
            logger.error(f"Failed to get years for {make} {model}: {e}")
            return []
    
    def get_trims_by_model_year(
        self,
        make: str,
        model: str,
        year: int,
    ) -> List[Dict[str, Any]]:
        """Get all trims for a model and year."""
        try:
            response = (
                self.supabase
                .table(self.CRSP_TABLE)
                .select("*")
                .ilike("make", f"%{make}%")
                .ilike("model", f"%{model}%")
                .eq("manufacture_year", year)
                .order("trim_level")
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Failed to get trims for {make} {model} {year}: {e}")
            return []
    
    # ================================================================
    # VALUATION CALCULATION
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
    ) -> Dict[str, Any]:
        """
        Calculate vehicle valuation using CRSP data and adjustment factors.
        
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
            crsp_id: Optional CRSP ID to use directly
            crsp_kes: Optional CRSP price to use directly
            
        Returns:
            Dict[str, Any]: Valuation results
        """
        # ─── Find CRSP Record ─────────────────────────────────────────
        crsp_record = None
        crsp_value = 0.0
        crsp_found_id = None
        
        # First, try using provided CRSP ID or price
        if crsp_id:
            crsp_record = self.get_crsp_by_id(crsp_id)
            if not crsp_record:
                crsp_record = self.get_crsp_by_crsp_id(crsp_id)
            if crsp_record:
                logger.info(f"Found CRSP record by ID {crsp_id}")
        
        # If provided CRSP price, use it directly
        if crsp_kes and crsp_kes > 0:
            crsp_value = crsp_kes
            logger.info(f"Using provided CRSP price: {crsp_value}")
        
        # If not found by ID, search by make/model/year
        if not crsp_record and make and model:
            crsp_record = self.get_crsp_by_make_model_year(make, model, year)
            if not crsp_record:
                crsp_record = self.get_crsp_by_make_model_year(make, model, None)
            if crsp_record:
                logger.info(f"Found CRSP record by make/model")
        
        # If we have a CRSP record, extract values
        if crsp_record:
            if crsp_value == 0:
                crsp_value = float(crsp_record.get("crsp_kes", 0) or 0)
            crsp_found_id = crsp_record.get("crsp_id") or crsp_record.get("id")
            # Use CRSP values if not provided
            if not make:
                make = crsp_record.get("make") or make
            if not model:
                model = crsp_record.get("model") or model
            if not trim:
                trim = crsp_record.get("trim_level") or trim
            if not engine_capacity:
                engine_capacity = str(crsp_record.get("engine_capacity") or "")
            if not fuel_type:
                fuel_type = crsp_record.get("fuel") or fuel_type
            if not transmission:
                transmission = crsp_record.get("transmission") or transmission
            logger.info(f"CRSP record: ID={crsp_found_id}, value={crsp_value}")
        
        # If no CRSP record and no CRSP value, estimate
        if crsp_value == 0:
            logger.warning(f"No CRSP record found for {make} {model} {year}")
        
        # ─── Calculate Age ────────────────────────────────────────────
        current_year = datetime.now(timezone.utc).year
        age = max(0, current_year - year)
        
        # ─── Depreciation Rate ────────────────────────────────────────
        depreciation_rate = self._get_depreciation_rate(age, vehicle_type)
        
        # ─── Adjustment Factors ──────────────────────────────────────
        mileage_factor = self._get_mileage_factor(mileage, age)
        condition_factor = self._get_condition_factor(condition)
        accident_factor = self._get_accident_factor(accident_history)
        owner_factor = self._get_owner_factor(previous_owners)
        location_factor = self._get_location_factor(location)
        fuel_factor = self._get_fuel_factor(fuel_type)
        transmission_factor = self._get_transmission_factor(transmission)
        
        # ─── Calculate Base Value ─────────────────────────────────────
        if crsp_value > 0:
            base_value = crsp_value
            crsp_found = True
        else:
            # Estimate based on make/model
            base_value = self._estimate_base_value(make, model, year)
            crsp_found = False
            logger.info(f"Using estimated base value: {base_value}")
        
        # ─── Apply Adjustments ────────────────────────────────────────
        adjusted_value = (
            base_value
            * (1.0 - depreciation_rate)
            * mileage_factor
            * condition_factor
            * accident_factor
            * owner_factor
            * location_factor
            * fuel_factor
            * transmission_factor
        )
        
        final_value = max(round(adjusted_value, 2), 0.0)
        
        # ─── Market Values ────────────────────────────────────────────
        retail_value = round(final_value * 1.08, 2)
        trade_value = round(final_value * 0.85, 2)
        dealer_value = round(final_value * 0.95, 2)
        selling_price = round(final_value * (1.0 + profit_margin / 100.0), 2) if profit_margin > 0 else None
        
        # ─── Confidence Score ────────────────────────────────────────
        confidence = self._calculate_confidence(crsp_found, age, mileage, condition)
        
        # ─── Adjustments Dictionary ──────────────────────────────────
        adjustments = {
            "depreciation_rate": round(depreciation_rate * 100, 1),
            "mileage_factor": round(mileage_factor, 2),
            "condition_factor": round(condition_factor, 2),
            "accident_factor": round(accident_factor, 2),
            "owner_factor": round(owner_factor, 2),
            "location_factor": round(location_factor, 2),
            "fuel_factor": round(fuel_factor, 2),
            "transmission_factor": round(transmission_factor, 2),
        }
        
        # ─── Warnings ──────────────────────────────────────────────────
        warnings = []
        if not crsp_found:
            warnings.append("No CRSP record found - using make/model estimate")
        if age > 15:
            warnings.append("Vehicle age exceeds 15 years; value may be uncertain")
        if mileage > 200000:
            warnings.append("High mileage may affect vehicle value")
        
        # ─── Build Response ───────────────────────────────────────────
        return {
            "success": True,
            "status": "completed",
            "crsp_found": crsp_found,
            "crsp_id": crsp_found_id,
            "crsp_value": round(crsp_value, 2),
            "estimated_value": final_value,
            "estimated_value_min": round(final_value * 0.90, 2),
            "estimated_value_max": round(final_value * 1.10, 2),
            "market_value": final_value,
            "retail_value": retail_value,
            "trade_value": trade_value,
            "dealer_value": dealer_value,
            "recommended_selling_price": selling_price,
            "confidence_score": confidence,
            "adjustments": adjustments,
            "depreciation": {
                "rate": round(depreciation_rate * 100, 1),
                "age_years": age,
                "remaining_value_percent": round((1.0 - depreciation_rate) * 100, 1),
            },
            "vehicle": {
                "crsp_id": crsp_found_id,
                "make": make,
                "model": model,
                "trim": trim,
                "year": year,
                "fuel_type": fuel_type,
                "transmission": transmission,
                "engine_capacity": engine_capacity,
                "body_type": crsp_record.get("body_type") if crsp_record else None,
                "vehicle_type": vehicle_type,
            },
            "message": "Valuation completed successfully.",
            "warnings": warnings,
            "currency": "KES",
            "calculated_at": datetime.now(timezone.utc).isoformat(),
            "comparables": [],
            "sample_size": 1 if crsp_found else 0,
            "recommendation": None,
        }
    
    # ================================================================
    # ADJUSTMENT FACTORS
    # ================================================================
    
    def _get_depreciation_rate(self, age: int, vehicle_type: Optional[str] = None) -> float:
        """Get depreciation rate based on age and vehicle type."""
        if age <= 1:
            return 0.10
        elif age <= 3:
            return 0.20
        elif age <= 5:
            return 0.30
        elif age <= 8:
            return 0.45
        elif age <= 12:
            return 0.60
        else:
            return 0.70
    
    def _get_mileage_factor(self, mileage: int, age: int) -> float:
        """Get mileage adjustment factor."""
        if mileage <= 0:
            return 1.0
        
        expected = max(15000 * max(age, 1), 1000)
        ratio = mileage / expected
        
        if ratio <= 0.75:
            return 1.03
        elif ratio <= 1.25:
            return 1.00
        elif ratio <= 1.75:
            return 0.95
        elif ratio <= 2.50:
            return 0.88
        else:
            return 0.80
    
    def _get_condition_factor(self, condition: str) -> float:
        """Get condition adjustment factor."""
        factors = {
            "excellent": 1.10,
            "very_good": 1.05,
            "good": 1.00,
            "fair": 0.90,
            "poor": 0.75,
        }
        return factors.get(condition.lower(), 1.00)
    
    def _get_accident_factor(self, accident_history: str) -> float:
        """Get accident history adjustment factor."""
        factors = {
            "none": 1.00,
            "minor": 0.92,
            "major": 0.75,
            "total_loss": 0.35,
        }
        return factors.get(accident_history.lower(), 1.00)
    
    def _get_owner_factor(self, previous_owners: int) -> float:
        """Get previous owners adjustment factor."""
        if previous_owners <= 1:
            return 1.00
        elif previous_owners <= 2:
            return 0.98
        elif previous_owners <= 3:
            return 0.95
        elif previous_owners <= 4:
            return 0.92
        else:
            return 0.88
    
    def _get_location_factor(self, location: str) -> float:
        """Get location adjustment factor."""
        factors = {
            "nairobi": 1.02,
            "mombasa": 1.00,
            "kisumu": 0.98,
            "nakuru": 0.98,
            "eldoret": 0.97,
            "thika": 0.97,
            "kiambu": 1.00,
            "kajiado": 0.98,
            "machakos": 0.97,
            "meru": 0.96,
            "nyeri": 0.96,
            "embu": 0.95,
            "malindi": 0.98,
            "nanyuki": 0.97,
        }
        return factors.get(location.lower(), 0.95)
    
    def _get_fuel_factor(self, fuel_type: Optional[str]) -> float:
        """Get fuel type adjustment factor."""
        if not fuel_type:
            return 1.0
        factors = {
            "petrol": 1.00,
            "diesel": 1.02,
            "electric": 1.05,
            "lpg": 0.95,
        }
        return factors.get(fuel_type.lower(), 1.00)
    
    def _get_transmission_factor(self, transmission: Optional[str]) -> float:
        """Get transmission adjustment factor."""
        if not transmission:
            return 1.0
        factors = {
            "manual": 0.95,
            "automatic": 1.00,
            "cvt": 0.98,
            "amt": 0.97,
        }
        return factors.get(transmission.lower(), 1.00)
    
    # ================================================================
    # BASE VALUE ESTIMATION
    # ================================================================
    
    def _estimate_base_value(self, make: str, model: str, year: int) -> float:
        """Estimate base value when no CRSP record exists."""
        make_lower = make.lower()
        model_lower = model.lower()
        
        # Base values by make (KES)
        base_values = {
            "toyota": 3500000,
            "honda": 2800000,
            "nissan": 2500000,
            "mazda": 2400000,
            "subaru": 3000000,
            "mercedes": 5000000,
            "bmw": 4500000,
            "audi": 4200000,
            "volkswagen": 3000000,
            "vw": 3000000,
            "ford": 3200000,
            "chevrolet": 2800000,
            "hyundai": 2500000,
            "kia": 2400000,
            "suzuki": 2000000,
            "mitsubishi": 2600000,
            "isuzu": 3500000,
            "land rover": 6000000,
            "jaguar": 5500000,
            "porsche": 8000000,
            "ferrari": 15000000,
            "lamborghini": 18000000,
        }
        
        # Model adjustments
        model_adjustments = {
            "land cruiser": 1.8,
            "prado": 1.5,
            "hilux": 1.3,
            "fortuner": 1.4,
            "rav4": 1.2,
            "chr": 1.1,
            "corolla": 0.8,
            "camry": 1.0,
            "premio": 0.85,
            "axio": 0.8,
            "harrier": 1.3,
            "venza": 1.2,
            "civic": 0.9,
            "accord": 1.0,
            "cr-v": 1.2,
            "hr-v": 1.0,
            "x-trail": 1.1,
            "qashqai": 1.0,
            "patrol": 1.8,
            "cx-5": 1.1,
            "demio": 0.7,
            "forester": 1.1,
            "outback": 1.0,
            "impreza": 0.9,
            "legacy": 0.95,
            "golf": 0.9,
            "passat": 1.0,
            "tiguan": 1.1,
            "c-class": 1.1,
            "e-class": 1.3,
            "s-class": 1.8,
            "3-series": 1.0,
            "5-series": 1.3,
            "x5": 1.5,
            "a4": 1.0,
            "a6": 1.2,
            "q5": 1.2,
        }
        
        # Get base value
        base_value = 2500000
        for key, value in base_values.items():
            if key in make_lower:
                base_value = value
                break
        
        # Apply model adjustment
        model_factor = 1.0
        for key, factor in model_adjustments.items():
            if key in model_lower:
                model_factor = factor
                break
        
        # Year factor
        current_year = datetime.now(timezone.utc).year
        age = max(0, current_year - year)
        if age <= 1:
            year_factor = 0.95
        elif age <= 3:
            year_factor = 0.80
        elif age <= 5:
            year_factor = 0.65
        elif age <= 8:
            year_factor = 0.50
        elif age <= 12:
            year_factor = 0.35
        else:
            year_factor = 0.20
        
        return round(base_value * model_factor * year_factor, 2)
    
    # ================================================================
    # CONFIDENCE CALCULATION
    # ================================================================
    
    def _calculate_confidence(
        self,
        crsp_found: bool,
        age: int,
        mileage: int,
        condition: str,
    ) -> int:
        """Calculate confidence score."""
        score = 50
        
        if crsp_found:
            score += 30
        
        if age <= 5:
            score += 10
        elif age <= 10:
            score += 5
        
        if mileage <= 50000:
            score += 10
        elif mileage <= 100000:
            score += 5
        elif mileage <= 150000:
            score += 0
        else:
            score -= 5
        
        condition_factors = {
            "excellent": 10,
            "very_good": 8,
            "good": 5,
            "fair": 0,
            "poor": -5,
        }
        score += condition_factors.get(condition.lower(), 0)
        
        return min(max(score, 0), 100)
