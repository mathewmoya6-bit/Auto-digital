# app/modules/running_cost/schemas.py
"""Running Cost schemas for Auto-D Kenya"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
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


# ─── DEPRECIATION BREAKDOWN ────────────────────────────────────────

class DepreciationBreakdown(BaseModel):
    """Yearly depreciation breakdown"""
    year: int = Field(..., description="Year number")
    rate: float = Field(..., description="Depreciation rate for the year")
    amount: float = Field(..., description="Depreciation amount for the year")
    remaining_value: float = Field(..., description="Remaining value after depreciation")


# ─── VEHICLE INFO ──────────────────────────────────────────────────

class VehicleInfo(BaseModel):
    """Vehicle information"""
    initial_vehicle_cost: float = Field(..., description="Initial vehicle cost")
    purchase_price: float = Field(..., description="Purchase price")
    market_value: float = Field(..., description="Current market value")
    insurance_value: float = Field(..., description="Insurance value")
    current_value: float = Field(..., description="Current depreciated value")
    resale_value: float = Field(..., description="Estimated resale value")
    depreciation_rate: float = Field(..., description="Current depreciation rate")
    fuel_type: str = Field(..., description="Fuel type")
    fuel_efficiency: float = Field(..., description="Fuel efficiency in km/L")
    engine_size: float = Field(..., description="Engine size in litres")
    year: int = Field(..., description="Vehicle year")
    age: int = Field(..., description="Vehicle age in years")
    category: Optional[str] = Field(None, description="Vehicle category")
    body_type: Optional[str] = Field(None, description="Body type")
    trim_level: Optional[str] = Field(None, description="Trim level")
    power_hp: Optional[int] = Field(None, description="Power in HP")
    transmission: Optional[str] = Field(None, description="Transmission type")
    drive_type: Optional[str] = Field(None, description="Drive type")


# ─── TRIP COSTS ────────────────────────────────────────────────────

class TripCosts(BaseModel):
    """Trip cost breakdown"""
    distance: float = Field(..., description="Trip distance in km")
    running_cost: float = Field(..., description="Total running cost for trip")
    cost_per_km: float = Field(..., description="Cost per kilometer")


class CostBreakdown(BaseModel):
    """Individual cost breakdown"""
    fuel: float = Field(..., description="Fuel cost")
    service: float = Field(..., description="Service cost")
    tyres: float = Field(..., description="Tyre cost")
    insurance: float = Field(..., description="Insurance cost")
    depreciation: float = Field(..., description="Depreciation cost")


class PerKmBreakdown(BaseModel):
    """Per kilometer cost breakdown"""
    fuel: float = Field(..., description="Fuel cost per km")
    service: float = Field(..., description="Service cost per km")
    tyres: float = Field(..., description="Tyre cost per km")
    insurance: float = Field(..., description="Insurance cost per km")
    depreciation: float = Field(..., description="Depreciation cost per km")


# ─── MONTHLY & ANNUAL COSTS ──────────────────────────────────────

class MonthlyCosts(BaseModel):
    """Monthly cost breakdown"""
    fuel: float = Field(..., description="Monthly fuel cost")
    service: float = Field(..., description="Monthly service cost")
    tyres: float = Field(..., description="Monthly tyre cost")
    insurance: float = Field(..., description="Monthly insurance cost")
    depreciation: float = Field(..., description="Monthly depreciation cost")
    total: float = Field(..., description="Total monthly cost")


class AnnualCosts(BaseModel):
    """Annual cost breakdown"""
    fuel: float = Field(..., description="Annual fuel cost")
    service: float = Field(..., description="Annual service cost")
    tyres: float = Field(..., description="Annual tyre cost")
    insurance: float = Field(..., description="Annual insurance cost")
    depreciation: float = Field(..., description="Annual depreciation cost")
    total: float = Field(..., description="Total annual cost")


# ─── PROJECTION ────────────────────────────────────────────────────

class ProjectionData(BaseModel):
    """5-year projection data"""
    years: List[ProjectionYear] = Field(..., description="Year by year projection")
    total_5_year_cost: float = Field(..., description="Total 5-year cost")
    total_5_year_running_cost: float = Field(..., description="Total 5-year running cost")


# ─── FINANCE ──────────────────────────────────────────────────────

class FinanceData(BaseModel):
    """Finance calculation data"""
    financed: bool = Field(..., description="Whether vehicle is financed")
    loan_amount: Optional[float] = Field(None, description="Total loan amount")
    down_payment: Optional[float] = Field(None, description="Down payment amount")
    interest_rate: Optional[float] = Field(None, description="Annual interest rate")
    loan_term: Optional[int] = Field(None, description="Loan term in months")
    monthly_payment: Optional[float] = Field(None, description="Monthly payment amount")
    total_interest: Optional[float] = Field(None, description="Total interest paid")
    total_cost: Optional[float] = Field(None, description="Total cost including interest")


# ─── OPTIONS ──────────────────────────────────────────────────────

class CalculationOptions(BaseModel):
    """Calculation options"""
    include_insurance: bool = Field(..., description="Include insurance in calculation")
    include_tyres: bool = Field(..., description="Include tyres in calculation")
    include_maintenance: bool = Field(..., description="Include maintenance in calculation")
    include_depreciation: bool = Field(..., description="Include depreciation in calculation")
    financed: bool = Field(..., description="Whether vehicle is financed")


# ─── DRIVING FACTORS ─────────────────────────────────────────────

class DrivingFactors(BaseModel):
    """Driving factors"""
    driving_style: str = Field(..., description="Driving style")
    trip_type: str = Field(..., description="Trip type")
    usage_type: str = Field(..., description="Usage type")
    condition: str = Field(..., description="Vehicle condition")
    location: str = Field(..., description="Location")
    factor: float = Field(..., description="Combined driving factor multiplier")


# ─── REQUEST MODEL ──────────────────────────────────────────────────

class RunningCostRequest(BaseModel):
    """Request for running cost calculation"""
    
    variant_id: int = Field(..., description="Vehicle variant ID", gt=0)
    
    distance: float = Field(150, description="Trip distance in km", gt=0, le=100000)
    annual_mileage: float = Field(20000, description="Annual mileage in km", gt=0, le=200000)
    
    fuel_price: float = Field(200, description="Fuel price in KES per litre", gt=0, le=500)
    
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
    
    year: int = Field(2024, description="Vehicle year of manufacture", ge=1980)
    
    financed: bool = Field(False, description="Whether the vehicle is financed")
    down_payment: float = Field(30, description="Down payment percentage", ge=0, le=100)
    interest_rate: float = Field(16, description="Interest rate percentage", ge=0, le=50)
    
    loan_term: int = Field(4, description="Loan term in years", ge=1, le=7)
    years: int = Field(5, description="Number of years for projection", ge=1, le=10)
    
    include_insurance: bool = Field(True, description="Include insurance in calculation")
    include_maintenance: bool = Field(True, description="Include maintenance in calculation")
    include_tyres: bool = Field(True, description="Include tyres in calculation")
    include_depreciation: bool = Field(True, description="Include depreciation in calculation")
    
    insurance_type: str = Field("comprehensive", description="Insurance type: comprehensive, third_party")
    
    @field_validator('year')
    @classmethod
    def validate_year(cls, v: int) -> int:
        """Validate year is not in the future"""
        current_year = datetime.now(timezone.utc).year
        if v > current_year + 1:
            raise ValueError(f"Year cannot be more than {current_year + 1}")
        return v
    
    @field_validator('annual_mileage')
    @classmethod
    def validate_annual_mileage(cls, v: float) -> float:
        """Validate annual mileage is reasonable"""
        if v < 100:
            raise ValueError("Annual mileage must be at least 100 km")
        return v


# ─── RESPONSE MODEL ─────────────────────────────────────────────────

class RunningCostResponse(BaseModel):
    """Complete response for running cost calculation"""
    
    # ─── Trip Summary ──────────────────────────────────────────────
    tripTotal: float = Field(..., description="Total running cost for the trip")
    tripCostPerKm: float = Field(..., description="Cost per kilometer")
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
    
    # ─── Legacy Fields ─────────────────────────────────────────────
    distance: float = Field(..., description="Trip distance in km")
    cost_per_km: float = Field(..., description="Cost per kilometer")
    fuel_cost: float = Field(..., description="Fuel cost for the trip")
    service_cost: float = Field(..., description="Service cost for the trip")
    tyre_cost: float = Field(..., description="Tyre cost for the trip")
    insurance_cost: float = Field(..., description="Insurance cost for the trip")
    depreciation_cost: float = Field(..., description="Depreciation cost for the trip")
    purchase_price: float = Field(..., description="Purchase price")
    market_value: float = Field(..., description="Current market value")
    insurance_value: float = Field(..., description="Insurance value")
    current_value: float = Field(..., description="Current depreciated value")
    resale_value: float = Field(..., description="Estimated resale value")
    fuel_type: str = Field(..., description="Fuel type")
    fuel_consumption: float = Field(..., description="Fuel consumption in km/L")
    fiveYearData: List[ProjectionYear] = Field(..., description="5-year projection data")
    five_year_total: float = Field(..., description="Total 5-year cost")
    
    # ─── Structured Response ──────────────────────────────────────
    trip: TripCosts = Field(..., description="Trip cost details")
    costs: CostBreakdown = Field(..., description="Cost breakdown")
    per_km: PerKmBreakdown = Field(..., description="Per kilometer breakdown")
    monthly: MonthlyCosts = Field(..., description="Monthly costs")
    annual: AnnualCosts = Field(..., description="Annual costs")
    projection: ProjectionData = Field(..., description="5-year projection")
    vehicle: VehicleInfo = Field(..., description="Vehicle information")
    finance: FinanceData = Field(..., description="Finance calculation")
    options: CalculationOptions = Field(..., description="Calculation options")
    driving_factors: DrivingFactors = Field(..., description="Driving factors")
    depreciation_breakdown: List[DepreciationBreakdown] = Field(..., description="Yearly depreciation breakdown")
    
    # ─── Timestamp ────────────────────────────────────────────────
    calculated_at: str = Field(..., description="ISO timestamp of calculation")
    
    # ─── Legacy CamelCase Fields ──────────────────────────────────
    total5YearCost: float = Field(..., description="Total 5-year cost")
    originalCost: float = Field(..., description="Original purchase price")
    ageAdjustedCost: float = Field(..., description="Age-adjusted current value")
    remainingValue: float = Field(..., description="Remaining value after projection")
    fuelTypeDisplay: str = Field(..., description="Fuel type display name")
    fuelConsumption: float = Field(..., description="Fuel consumption in km/L")


# ─── LEGACY RESPONSE (for backward compatibility) ──────────────────

class LegacyRunningCostResponse(BaseModel):
    """Legacy response format for backward compatibility"""
    
    tripTotal: float
    tripCostPerKm: float
    distance: float
    
    fuelCostTrip: float
    serviceTrip: float
    tyreTrip: float
    insuranceTrip: float
    depreciationTrip: float
    
    fuelCostPerKm: float
    servicePerKm: float
    tyrePerKm: float
    insurancePerKm: float
    depreciationPerKm: float
    
    monthlyFuel: float
    monthlyService: float
    monthlyTyre: float
    monthlyInsurance: float
    monthlyDepreciation: float
    
    annualFuel: float
    annualService: float
    annualTyre: float
    annualInsurance: float
    annualDepreciation: float
    
    fiveYearData: List[ProjectionYear]
    total5YearCost: float
    
    originalCost: float
    ageAdjustedCost: float
    current_value: float
    remainingValue: float
    resale_value: float
    
    fuelTypeDisplay: str
    fuelConsumption: float
    
    calculated_at: datetime
    
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


# ─── SIMPLE RESPONSE (for quick calculations) ──────────────────────

class SimpleRunningCostResponse(BaseModel):
    """Simple response for quick calculations"""
    trip_total: float = Field(..., description="Total trip cost")
    cost_per_km: float = Field(..., description="Cost per kilometer")
    fuel_cost: float = Field(..., description="Fuel cost")
    service_cost: float = Field(..., description="Service cost")
    tyre_cost: float = Field(..., description="Tyre cost")
    insurance_cost: float = Field(..., description="Insurance cost")
    depreciation_cost: float = Field(..., description="Depreciation cost")
    vehicle_name: str = Field(..., description="Vehicle name")
    fuel_type: str = Field(..., description="Fuel type")
    fuel_efficiency: float = Field(..., description="Fuel efficiency in km/L")
    calculated_at: str = Field(..., description="Calculation timestamp")
