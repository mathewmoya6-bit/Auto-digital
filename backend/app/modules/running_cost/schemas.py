# app/modules/running_cost/schemas.py
"""Running Cost schemas for Auto-D Kenya"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import Optional, List
from typing_extensions import Literal

# ─── PROJECTION YEAR MODEL ────────────────────────────────────────

class ProjectionYear(BaseModel):
    """Single year projection data"""
    year: int = Field(..., description="Year number (1-5)")
    fuel: float = Field(..., description="Fuel cost for the year")
    service: float = Field(..., description="Service cost for the year")
    tyres: float = Field(..., description="Tyre cost for the year")
    insurance: float = Field(..., description="Insurance cost for the year")
    depreciation: float = Field(..., description="Depreciation for the year")
    running_cost: float = Field(..., description="Total running cost for the year")
    total: float = Field(..., description="Total cost including depreciation for the year")
    value: float = Field(..., description="Remaining vehicle value at year end")


# ─── REQUEST MODEL ──────────────────────────────────────────────────

class RunningCostRequest(BaseModel):
    """Request for running cost calculation"""
    
    # ✅ FIX 1: Only one definition (keep in schemas.py)
    variant_id: int = Field(..., description="Vehicle variant ID", gt=0)
    
    # ✅ FIX 2: annual_mileage must be > 0 (prevent division by zero)
    distance: float = Field(150, description="Trip distance in km", gt=0, le=100000)
    annual_mileage: float = Field(20000, description="Annual mileage in km", gt=0, le=200000)
    
    # ✅ FIX 3: fuel_price must be > 0
    fuel_price: float = Field(200, description="Fuel price in KES per litre", gt=0, le=500)
    
    # ✅ FIX 6: Use Literal for string fields
    trip_type: Literal["urban", "highway", "mixed", "offroad"] = Field(
        "mixed", description="Trip type"
    )
    driving_style: Literal["eco", "normal", "aggressive"] = Field(
        "normal", description="Driving style"
    )
    usage_type: Literal["private", "commercial", "fleet", "taxi"] = Field(
        "private", description="Usage type"
    )
    location: str = Field("nairobi", description="Location for cost adjustment")
    condition: Literal["poor", "fair", "good", "excellent"] = Field(
        "good", description="Vehicle condition"
    )
    
    # ✅ FIX 4: year validation
    year: int = Field(2024, description="Vehicle year of manufacture", ge=1980)
    
    financed: bool = Field(False, description="Whether the vehicle is financed")
    down_payment: float = Field(30, description="Down payment percentage", ge=0, le=100)
    interest_rate: float = Field(16, description="Interest rate percentage", ge=0, le=50)
    
    # ✅ FIX 5: years should be between 1 and 10
    loan_term: int = Field(4, description="Loan term in years", ge=1, le=7)
    years: int = Field(5, description="Number of years for projection", ge=1, le=10)
    
    include_insurance: bool = Field(True, description="Include insurance in calculation")
    include_maintenance: bool = Field(True, description="Include maintenance in calculation")
    include_tyres: bool = Field(True, description="Include tyres in calculation")
    include_depreciation: bool = Field(True, description="Include depreciation in calculation")
    
    # ✅ FIX 4: Custom validator for year
    @field_validator('year')
    @classmethod
    def validate_year(cls, v: int) -> int:
        """Validate year is not in the future"""
        current_year = datetime.now(timezone.utc).year
        if v > current_year + 1:
            raise ValueError(f"Year cannot be more than {current_year + 1}")
        return v
    
    # ✅ FIX 2: Additional validation for annual_mileage
    @field_validator('annual_mileage')
    @classmethod
    def validate_annual_mileage(cls, v: float) -> float:
        """Validate annual mileage is reasonable"""
        if v < 100:
            raise ValueError("Annual mileage must be at least 100 km")
        return v


# ─── RESPONSE MODEL ─────────────────────────────────────────────────

class RunningCostResponse(BaseModel):
    """Response for running cost calculation"""
    
    # ─── Trip Summary ──────────────────────────────────────────────
    trip: dict = Field(..., description="Trip summary with distance, running_cost, cost_per_km")
    
    # ─── Cost Breakdown ────────────────────────────────────────────
    costs: dict = Field(..., description="Cost breakdown for the trip")
    
    # ─── Per KM Costs ─────────────────────────────────────────────
    per_km: dict = Field(..., description="Cost per kilometer breakdown")
    
    # ─── Monthly Costs ────────────────────────────────────────────
    monthly: dict = Field(..., description="Monthly cost breakdown")
    
    # ─── Annual Costs ─────────────────────────────────────────────
    annual: dict = Field(..., description="Annual cost breakdown")
    
    # ─── 5-Year Projection ────────────────────────────────────────
    projection: dict = Field(..., description="5-year projection data")
    
    # ─── Vehicle Info ─────────────────────────────────────────────
    vehicle: dict = Field(..., description="Vehicle information")
    
    # ─── Timestamp ────────────────────────────────────────────────
    calculated_at: str = Field(..., description="ISO timestamp of calculation")


# ─── LEGACY RESPONSE (for backward compatibility) ──────────────────

class LegacyRunningCostResponse(BaseModel):
    """Legacy response format for backward compatibility"""
    
    # ─── Trip Summary ──────────────────────────────────────────────
    tripTotal: float = Field(..., description="Total running cost for the trip")
    tripCostPerKm: float = Field(..., description="Cost per kilometer")
    distance: float = Field(..., description="Trip distance in km")
    
    # ─── Trip Cost Breakdown ──────────────────────────────────────
    fuelCostTrip: float = Field(..., description="Fuel cost for the trip")
    serviceTrip: float = Field(..., description="Service cost for the trip")
    tyreTrip: float = Field(..., description="Tyre cost for the trip")
    insuranceTrip: float = Field(..., description="Insurance cost for the trip")
    depreciationTrip: float = Field(..., description="Depreciation cost for the trip")
    
    # ─── Per KM Costs ─────────────────────────────────────────────
    fuelCostPerKm: float = Field(..., description="Fuel cost per kilometer")
    servicePerKm: float = Field(..., description="Service cost per kilometer")
    tyrePerKm: float = Field(..., description="Tyre cost per kilometer")
    insurancePerKm: float = Field(..., description="Insurance cost per kilometer")
    depreciationPerKm: float = Field(..., description="Depreciation cost per kilometer")
    
    # ─── Monthly Costs ────────────────────────────────────────────
    monthlyFuel: float = Field(..., description="Monthly fuel cost")
    monthlyService: float = Field(..., description="Monthly service cost")
    monthlyTyre: float = Field(..., description="Monthly tyre cost")
    monthlyInsurance: float = Field(..., description="Monthly insurance cost")
    monthlyDepreciation: float = Field(..., description="Monthly depreciation cost")
    
    # ─── Annual Costs ─────────────────────────────────────────────
    annualFuel: float = Field(..., description="Annual fuel cost")
    annualService: float = Field(..., description="Annual service cost")
    annualTyre: float = Field(..., description="Annual tyre cost")
    annualInsurance: float = Field(..., description="Annual insurance cost")
    annualDepreciation: float = Field(..., description="Annual depreciation cost")
    
    # ─── 5-Year Projection ────────────────────────────────────────
    fiveYearData: List[ProjectionYear] = Field(..., description="5-year projection data")
    total5YearCost: float = Field(..., description="Total 5-year cost")
    
    # ─── Vehicle Info ─────────────────────────────────────────────
    originalCost: float = Field(..., description="Original purchase price")
    ageAdjustedCost: float = Field(..., description="Age-adjusted current value")
    current_value: float = Field(..., description="Current vehicle value")
    remainingValue: float = Field(..., description="Remaining value after projection")
    resale_value: float = Field(..., description="Estimated resale value")
    fuelTypeDisplay: str = Field(..., description="Fuel type display name")
    fuelConsumption: float = Field(..., description="Fuel consumption in km/l")
    
    # ─── Timestamp ────────────────────────────────────────────────
    calculated_at: datetime = Field(..., description="Calculation timestamp")
    
    # ─── Helper method to convert from new response ──────────────
    @classmethod
    def from_new_response(cls, data: dict) -> "LegacyRunningCostResponse":
        """Convert new response format to legacy format"""
        return cls(
            tripTotal=data["trip"]["running_cost"],
            tripCostPerKm=data["trip"]["cost_per_km"],
            distance=data["trip"]["distance"],
            fuelCostTrip=data["costs"]["fuel"],
            serviceTrip=data["costs"]["service"],
            tyreTrip=data["costs"]["tyres"],
            insuranceTrip=data["costs"]["insurance"],
            depreciationTrip=data["costs"]["depreciation"],
            fuelCostPerKm=data["per_km"]["fuel"],
            servicePerKm=data["per_km"]["service"],
            tyrePerKm=data["per_km"]["tyres"],
            insurancePerKm=data["per_km"]["insurance"],
            depreciationPerKm=data["per_km"]["depreciation"],
            monthlyFuel=data["monthly"]["fuel"],
            monthlyService=data["monthly"]["service"],
            monthlyTyre=data["monthly"]["tyres"],
            monthlyInsurance=data["monthly"]["insurance"],
            monthlyDepreciation=data["monthly"]["depreciation"],
            annualFuel=data["annual"]["fuel"],
            annualService=data["annual"]["service"],
            annualTyre=data["annual"]["tyres"],
            annualInsurance=data["annual"]["insurance"],
            annualDepreciation=data["annual"]["depreciation"],
            fiveYearData=[ProjectionYear(**y) for y in data["projection"]["years"]],
            total5YearCost=data["projection"]["total_5_year_cost"],
            originalCost=data["vehicle"]["purchase_price"],
            ageAdjustedCost=data["vehicle"]["current_value"],
            current_value=data["vehicle"]["current_value"],
            remainingValue=data["vehicle"]["resale_value"],
            resale_value=data["vehicle"]["resale_value"],
            fuelTypeDisplay=data["vehicle"]["fuel_type"],
            fuelConsumption=data["vehicle"]["fuel_efficiency"],
            calculated_at=datetime.fromisoformat(data["calculated_at"])
        )
