"""
Request Schemas for API - COMPLETE
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


# ─── VALUATION SCHEMAS ─────────────────────────────────────────────

class ValuationRequest(BaseModel):
    """Vehicle valuation request model"""
    variant_id: str = Field(..., description="Vehicle variant ID from database")
    year: int = Field(..., ge=1990, le=datetime.now().year, description="Year of manufacture")
    mileage: float = Field(..., ge=0, le=1000000, description="Current odometer reading in km")
    condition: str = Field("good", description="Vehicle condition: excellent, very_good, good, fair, poor")
    accident_history: str = Field("none", description="Accident history: none, minor, major, total_loss")
    previous_owners: int = Field(0, ge=0, le=20, description="Number of previous owners")
    service_history: bool = Field(True, description="Whether service history is available")
    location: str = Field("nairobi", description="Vehicle location/county")
    modifications: Optional[List[str]] = Field(default=[], description="List of modifications")
    custom_adjustments: Optional[Dict[str, float]] = Field(default={}, description="Custom value adjustments")
    images: Optional[List[str]] = Field(None, description="Base64 encoded images for AI analysis")
    
    @validator('condition')
    def validate_condition(cls, v):
        allowed = ['excellent', 'very_good', 'good', 'fair', 'poor']
        if v.lower() not in allowed:
            raise ValueError(f"Condition must be one of: {', '.join(allowed)}")
        return v.lower()
    
    @validator('accident_history')
    def validate_accident(cls, v):
        allowed = ['none', 'minor', 'major', 'total_loss']
        if v.lower() not in allowed:
            raise ValueError(f"Accident history must be one of: {', '.join(allowed)}")
        return v.lower()


# ─── RUNNING COST SCHEMAS ──────────────────────────────────────────

class RunningCostRequest(BaseModel):
    """Running cost calculation request for a trip"""
    variant_id: str = Field(..., description="Vehicle variant ID")
    distance: float = Field(150, ge=1, le=100000, description="Trip distance in km")
    annual_mileage: float = Field(20000, ge=0, le=200000, description="Annual mileage in km")
    fuel_price: float = Field(200, ge=0, description="Fuel price per liter (KES)")
    trip_type: str = Field("mixed", description="Trip type: urban, highway, mixed, offroad")
    driving_style: str = Field("normal", description="Driving style: eco, normal, aggressive")
    usage_type: str = Field("private", description="Usage type: private, commercial, fleet")
    location: str = Field("nairobi", description="Location for cost adjustment")
    condition: str = Field("good", description="Vehicle condition")
    year: Optional[int] = Field(None, description="Vehicle year")
    financed: bool = Field(False, description="Is the vehicle financed")
    down_payment: float = Field(30, ge=0, le=100, description="Down payment percentage")
    interest_rate: float = Field(16, ge=0, le=100, description="Annual interest rate")
    loan_term: int = Field(4, ge=1, le=10, description="Loan term in years")
    years: int = Field(5, ge=1, le=15, description="Number of years to project")
    include_insurance: bool = Field(True, description="Include insurance in calculation")
    include_maintenance: bool = Field(True, description="Include maintenance in calculation")
    include_tyres: bool = Field(True, description="Include tyre replacement in calculation")
    include_depreciation: bool = Field(True, description="Include depreciation in calculation")
    user_id: Optional[str] = Field(None, description="User ID for saving report")
    
    @validator('trip_type')
    def validate_trip_type(cls, v):
        allowed = ['urban', 'highway', 'mixed', 'offroad']
        if v.lower() not in allowed:
            raise ValueError(f"Trip type must be one of: {', '.join(allowed)}")
        return v.lower()
    
    @validator('driving_style')
    def validate_driving_style(cls, v):
        allowed = ['eco', 'normal', 'aggressive']
        if v.lower() not in allowed:
            raise ValueError(f"Driving style must be one of: {', '.join(allowed)}")
        return v.lower()


# ─── MILEAGE SCHEMAS ───────────────────────────────────────────────

class MileageRequest(BaseModel):
    """Mileage adjustment request"""
    variant_id: str = Field(..., description="Vehicle variant ID")
    current_mileage: float = Field(..., ge=0, description="Current odometer reading")
    expected_annual_mileage: float = Field(20000, ge=0, description="Expected annual mileage")
    age_years: int = Field(..., ge=0, description="Vehicle age in years")


class MileageRateRequest(BaseModel):
    """Mileage rate calculation request"""
    variant_id: str = Field(..., description="Vehicle variant ID")
    annual_mileage: float = Field(20000, ge=0, description="Annual mileage in km")
    fuel_price: float = Field(200, ge=0, description="Fuel price per liter (KES)")
    maintenance_cost_per_km: float = Field(1.5, ge=0, description="Maintenance cost per km")
    tyre_cost_per_km: float = Field(0.8, ge=0, description="Tyre cost per km")
    insurance_cost_per_km: float = Field(2.5, ge=0, description="Insurance cost per km")
    include_depreciation: bool = Field(True, description="Include depreciation in calculation")
    include_insurance: bool = Field(True, description="Include insurance in calculation")
    include_maintenance: bool = Field(True, description="Include maintenance in calculation")
    include_tyres: bool = Field(True, description="Include tyres in calculation")
    location: Optional[str] = Field("nairobi", description="Location for cost adjustment")
    trip_type: Optional[str] = Field("mixed", description="Trip type for cost adjustment")
    financed: bool = Field(False, description="Is the vehicle financed")
    down_payment: float = Field(30, ge=0, le=100, description="Down payment percentage")
    interest_rate: float = Field(16, ge=0, le=100, description="Annual interest rate")
    loan_term: int = Field(4, ge=1, le=10, description="Loan term in years")
    year: Optional[int] = Field(None, description="Vehicle year")
    user_id: Optional[str] = Field(None, description="User ID for saving report")


# ─── OWNERSHIP SCHEMAS ─────────────────────────────────────────────

class OwnershipRequest(BaseModel):
    """Ownership cost request"""
    variant_id: str = Field(..., description="Vehicle variant ID")
    purchase_price: float = Field(..., ge=0, description="Purchase price in KES")
    down_payment: float = Field(0, ge=0, description="Down payment in KES")
    loan_term_months: int = Field(36, ge=1, le=84, description="Loan term in months")
    interest_rate: float = Field(14.0, ge=0, le=100, description="Annual interest rate %")
    annual_insurance: float = Field(50000, ge=0, description="Annual insurance premium")
    annual_maintenance: float = Field(30000, ge=0, description="Annual maintenance cost")


class OwnershipCostRequest(BaseModel):
    """Ownership cost calculation request (alternative schema)"""
    variant_id: str = Field(..., description="Vehicle variant ID")
    purchase_price: float = Field(..., ge=0, description="Purchase price in KES")
    down_payment: float = Field(0, ge=0, description="Down payment in KES")
    loan_term_years: int = Field(3, ge=1, le=7, description="Loan term in years")
    interest_rate: float = Field(14.0, ge=0, le=100, description="Annual interest rate %")
    annual_mileage: float = Field(20000, ge=0, description="Annual mileage in km")
    fuel_price: float = Field(200, ge=0, description="Fuel price per liter (KES)")
    insurance_rate: float = Field(3.0, ge=0, le=10, description="Annual insurance rate as % of value")
    maintenance_cost_per_km: float = Field(1.5, ge=0, description="Maintenance cost per km")
    tyre_cost_per_km: float = Field(0.8, ge=0, description="Tyre cost per km")
    include_depreciation: bool = Field(True, description="Include depreciation in calculation")
    include_insurance: bool = Field(True, description="Include insurance in calculation")
    include_maintenance: bool = Field(True, description="Include maintenance in calculation")
    include_tyres: bool = Field(True, description="Include tyres in calculation")
    years_owned: int = Field(5, ge=1, le=15, description="Number of years owned")
    usage_type: str = Field("private", description="Usage type: private, commercial, fleet")
    condition: str = Field("good", description="Vehicle condition")
    financed: bool = Field(False, description="Is the vehicle financed")
    location: str = Field("nairobi", description="Location for cost adjustment")
    user_id: Optional[str] = Field(None, description="User ID for saving report")


# ─── FUEL SCHEMAS ──────────────────────────────────────────────────

class FuelRequest(BaseModel):
    """Fuel cost request"""
    variant_id: str = Field(..., description="Vehicle variant ID")
    monthly_km: float = Field(1500, ge=0, description="Monthly kilometers driven")
    fuel_price: float = Field(200, ge=0, description="Fuel price per liter (KES)")


# ─── VEHICLE SEARCH SCHEMAS ────────────────────────────────────────

class VehicleSearchRequest(BaseModel):
    """Vehicle search request"""
    make: Optional[str] = None
    model: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    vehicle_type: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class VehicleCreateRequest(BaseModel):
    """Vehicle creation request"""
    make_id: str = Field(..., description="Make ID")
    model_id: str = Field(..., description="Model ID")
    name: str = Field(..., description="Variant name")
    year: int = Field(..., ge=1900, le=datetime.now().year + 1)
    engine_cc: float = Field(..., ge=50, le=10000)
    fuel_type: str = Field(..., description="petrol, diesel, hybrid, electric")
    transmission: str = Field(..., description="automatic, manual, cvt")
    market_value: float = Field(..., ge=0)
    depreciation_class: str = Field("DEFAULT")
    fuel_consumption: float = Field(8.0, ge=0)
    insurance_group: int = Field(5, ge=1, le=20)
    service_interval: int = Field(15000, ge=0)
    service_cost: float = Field(15000, ge=0)
    tyre_cost: float = Field(12000, ge=0)
    body_type: Optional[str] = "sedan"
    drive_type: Optional[str] = "2WD"
    vehicle_class: Optional[str] = None
    tyre_size: Optional[str] = None


# ─── SERVICE PRICE SCHEMAS ─────────────────────────────────────────

class ServicePriceCreateRequest(BaseModel):
    """Create a service price"""
    service_type: str = Field(..., description="Service type identifier")
    service_name: str = Field(..., description="Display name")
    price: float = Field(..., ge=0, description="Price in KES")
    currency: str = Field("KES", description="Currency code")
    description: Optional[str] = Field("", description="Service description")
    icon: Optional[str] = Field("", description="Emoji icon")
    display_order: int = Field(0, description="Display order")
    is_active: bool = Field(True, description="Whether service is active")


# ─── EXPORT ALL ─────────────────────────────────────────────────────

__all__ = [
    "ValuationRequest",
    "RunningCostRequest",
    "MileageRequest",
    "MileageRateRequest",
    "OwnershipRequest",
    "OwnershipCostRequest",
    "FuelRequest",
    "VehicleSearchRequest",
    "VehicleCreateRequest",
    "ServicePriceCreateRequest",
]
