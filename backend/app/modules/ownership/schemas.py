# app/modules/ownership/schemas.py
"""Ownership (TCO) schemas for Auto-D Kenya"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# ─── REQUEST SCHEMAS ──────────────────────────────────────────────

class TCORequest(BaseModel):
    """
    Total Cost of Ownership request.
    
    Matches the HTML frontend with all options:
    - Vehicle Type (ICE, Hybrid, EV)
    - Fuel Type (Petrol, Diesel, Hybrid, LPG, Electric)
    - Vehicle Condition (New, Used)
    - Purchase Type (Cash, Financing)
    """
    
    # ─── Vehicle Details ──────────────────────────────────────────
    variant_id: int = Field(..., description="Vehicle variant ID", gt=0)
    vehicle_year: int = Field(2020, description="Vehicle year of manufacture", ge=1980, le=2026)
    vehicle_type: str = Field("ice", description="Vehicle type: ice, hybrid, ev")
    vehicle_condition: str = Field("new", description="Vehicle condition: new, used")
    fuel_type: str = Field("petrol", description="Fuel type: petrol, diesel, hybrid, lpg, electric, cng")
    
    # ─── Financial Details ────────────────────────────────────────
    purchase_type: str = Field("cash", description="Purchase type: cash, finance")
    purchase_price: float = Field(4500000, description="Purchase price in KES", ge=100000)
    down_payment: float = Field(1000000, description="Down payment in KES", ge=0)
    loan_term_years: int = Field(3, description="Loan term in years", ge=1, le=7)
    interest_rate: float = Field(14.0, description="Annual interest rate percentage", ge=0, le=28)
    
    # ─── Usage Profile ────────────────────────────────────────────
    annual_mileage: float = Field(20000, description="Annual mileage in km", ge=0, le=60000)
    fuel_price: float = Field(200, description="Fuel price in KES per litre", ge=0, le=500)
    insurance_rate: float = Field(3.0, description="Insurance rate percentage", ge=0, le=8)
    maintenance_cost_per_km: float = Field(1.5, description="Maintenance cost per km", ge=0, le=5)
    tyre_cost_per_km: float = Field(0.8, description="Tyre cost per km", ge=0, le=2)
    
    # ─── Toggles ──────────────────────────────────────────────────
    include_depreciation: bool = Field(True, description="Include depreciation in calculation")
    include_insurance: bool = Field(True, description="Include insurance in calculation")
    include_maintenance: bool = Field(True, description="Include maintenance in calculation")
    include_tyres: bool = Field(True, description="Include tyres in calculation")
    include_inflation: bool = Field(True, description="Include inflation in calculation")
    
    @field_validator('fuel_type')
    @classmethod
    def validate_fuel_type(cls, v: str) -> str:
        allowed = ["petrol", "diesel", "hybrid", "lpg", "electric", "cng"]
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Fuel type must be one of: {', '.join(allowed)}")
        return v
    
    @field_validator('vehicle_type')
    @classmethod
    def validate_vehicle_type(cls, v: str) -> str:
        allowed = ["ice", "hybrid", "ev"]
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Vehicle type must be one of: {', '.join(allowed)}")
        return v
    
    @field_validator('vehicle_condition')
    @classmethod
    def validate_vehicle_condition(cls, v: str) -> str:
        allowed = ["new", "used"]
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Vehicle condition must be one of: {', '.join(allowed)}")
        return v
    
    @field_validator('purchase_type')
    @classmethod
    def validate_purchase_type(cls, v: str) -> str:
        allowed = ["cash", "finance"]
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Purchase type must be one of: {', '.join(allowed)}")
        return v
    
    @field_validator('vehicle_year')
    @classmethod
    def validate_vehicle_year(cls, v: int) -> int:
        current_year = datetime.now().year
        if v < 1980 or v > current_year + 1:
            raise ValueError(f"Vehicle year must be between 1980 and {current_year + 1}")
        return v
    
    @field_validator('annual_mileage')
    @classmethod
    def validate_annual_mileage(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Annual mileage cannot be negative")
        if v > 200000:
            raise ValueError("Annual mileage cannot exceed 200,000 km")
        return v
    
    @field_validator('purchase_price')
    @classmethod
    def validate_purchase_price(cls, v: float) -> float:
        if v < 100000:
            raise ValueError("Purchase price must be at least 100,000 KES")
        return v


# ─── RESPONSE SCHEMAS ─────────────────────────────────────────────

class MonthlyBreakdown(BaseModel):
    """Monthly running cost breakdown."""
    loan_payment: float = Field(..., description="Monthly loan payment")
    fuel: float = Field(..., description="Monthly fuel cost")
    maintenance: float = Field(..., description="Monthly maintenance cost")
    tyres: float = Field(..., description="Monthly tyre cost")
    insurance: float = Field(..., description="Monthly insurance cost")
    total: float = Field(..., description="Total monthly running cost")


class TCOComponent(BaseModel):
    """Single cost component with percentage."""
    name: str = Field(..., description="Component name")
    amount: float = Field(..., description="Amount in KES")
    percentage: float = Field(..., description="Percentage of total cost")


class LoanDetails(BaseModel):
    """Loan calculation details."""
    principal: float = Field(..., description="Loan principal amount")
    interest_rate: float = Field(..., description="Annual interest rate")
    term_years: int = Field(..., description="Term in years")
    term_months: int = Field(..., description="Term in months")
    total_payment: float = Field(..., description="Total payment including interest")
    purchase_type: str = Field(..., description="Purchase type: cash or finance")


class VehicleDetails(BaseModel):
    """Vehicle details in response."""
    variant_id: int = Field(..., description="Vehicle variant ID")
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    variant: str = Field(..., description="Vehicle variant name")
    fuel_type: str = Field(..., description="Fuel type display name")
    fuel_type_display: str = Field(..., description="Fuel type display name")
    vehicle_condition: str = Field(..., description="Vehicle condition: new or used")
    purchase_type: str = Field(..., description="Purchase type: cash or finance")
    vehicle_year: int = Field(..., description="Vehicle year")
    vehicle_type: str = Field("ice", description="Vehicle type: ice, hybrid, ev")


class YearlyBreakdownItem(BaseModel):
    """Single year breakdown item."""
    year: int = Field(..., description="Year number")
    total_cost: float = Field(..., description="Total cost for the year")
    depreciation: float = Field(..., description="Depreciation for the year")
    running_cost: float = Field(..., description="Running cost for the year")
    insurance: float = Field(..., description="Insurance cost for the year")
    loan_payment: float = Field(..., description="Loan payment for the year")
    fuel: float = Field(..., description="Fuel cost for the year")
    maintenance: float = Field(..., description="Maintenance cost for the year")
    tyres: float = Field(..., description="Tyre cost for the year")
    vehicle_value: float = Field(..., description="Vehicle value at year end")


class TCOResponse(BaseModel):
    """Total Cost of Ownership response."""
    
    # ─── Summary ──────────────────────────────────────────────────
    total_cost: float = Field(..., description="Total ownership cost")
    monthly_cost: float = Field(..., description="Average monthly cost")
    monthly_payment: float = Field(..., description="Monthly loan payment")
    total_interest: float = Field(..., description="Total interest paid")
    cost_per_km: float = Field(..., description="Cost per kilometer")
    total_depreciation: float = Field(..., description="Total depreciation over period")
    resale_value: float = Field(..., description="Estimated resale value")
    
    # ─── Monthly Breakdown ───────────────────────────────────────
    monthly_breakdown: MonthlyBreakdown = Field(..., description="Monthly running cost breakdown")
    
    # ─── Components ──────────────────────────────────────────────
    components: List[TCOComponent] = Field(..., description="Cost components breakdown")
    
    # ─── Yearly Breakdown ────────────────────────────────────────
    yearly_breakdown: List[YearlyBreakdownItem] = Field(..., description="Year-by-year cost breakdown")
    
    # ─── Loan Details ────────────────────────────────────────────
    loan_details: LoanDetails = Field(..., description="Loan calculation details")
    
    # ─── Vehicle Details ─────────────────────────────────────────
    vehicle_details: VehicleDetails = Field(..., description="Vehicle details")
    
    # ─── Metadata ────────────────────────────────────────────────
    currency: str = Field("KES", description="Currency code")
    calculated_at: str = Field(..., description="ISO timestamp of calculation")


# ─── HEALTH RESPONSE ──────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: str = Field("1.0", description="API version")
    timestamp: str = Field(..., description="ISO timestamp")


# ─── FUEL TYPES RESPONSE ──────────────────────────────────────────

class FuelTypeItem(BaseModel):
    """Fuel type item."""
    value: str = Field(..., description="Fuel type value")
    label: str = Field(..., description="Fuel type display label")
    price: float = Field(..., description="Default price in KES per litre")
    description: str = Field(..., description="Fuel type description")


class FuelTypesResponse(BaseModel):
    """Fuel types response."""
    fuel_types: List[FuelTypeItem] = Field(..., description="List of fuel types")


# ─── VEHICLE CONDITIONS RESPONSE ──────────────────────────────────

class VehicleConditionItem(BaseModel):
    """Vehicle condition item."""
    value: str = Field(..., description="Condition value")
    label: str = Field(..., description="Condition display label")
    factor: float = Field(..., description="Price adjustment factor")
    description: str = Field(..., description="Condition description")


class VehicleConditionsResponse(BaseModel):
    """Vehicle conditions response."""
    conditions: List[VehicleConditionItem] = Field(..., description="List of vehicle conditions")


# ─── PURCHASE TYPES RESPONSE ──────────────────────────────────────

class PurchaseTypeItem(BaseModel):
    """Purchase type item."""
    value: str = Field(..., description="Purchase type value")
    label: str = Field(..., description="Purchase type display label")
    description: str = Field(..., description="Purchase type description")


class PurchaseTypesResponse(BaseModel):
    """Purchase types response."""
    purchase_types: List[PurchaseTypeItem] = Field(..., description="List of purchase types")


# ─── DEFAULTS RESPONSE ────────────────────────────────────────────

class DefaultsResponse(BaseModel):
    """Default values for TCO calculator."""
    defaults: Dict[str, Any] = Field(..., description="Default values")


# ─── FACTORY FUNCTIONS ────────────────────────────────────────────

def create_tco_response(
    total_cost: float,
    monthly_cost: float,
    monthly_payment: float,
    total_interest: float,
    cost_per_km: float,
    total_depreciation: float,
    resale_value: float,
    monthly_breakdown: Dict[str, float],
    components: List[Dict[str, Any]],
    yearly_breakdown: List[Dict[str, Any]],
    loan_details: Dict[str, Any],
    vehicle_details: Dict[str, Any],
    currency: str = "KES"
) -> TCOResponse:
    """
    Factory function to create a TCO response.
    
    Args:
        total_cost: Total ownership cost
        monthly_cost: Average monthly cost
        monthly_payment: Monthly loan payment
        total_interest: Total interest paid
        cost_per_km: Cost per kilometer
        total_depreciation: Total depreciation
        resale_value: Estimated resale value
        monthly_breakdown: Monthly running cost breakdown
        components: Cost components breakdown
        yearly_breakdown: Year-by-year breakdown
        loan_details: Loan calculation details
        vehicle_details: Vehicle details
        currency: Currency code
        
    Returns:
        TCOResponse: Complete TCO response
    """
    return TCOResponse(
        total_cost=round(total_cost, 2),
        monthly_cost=round(monthly_cost, 2),
        monthly_payment=round(monthly_payment, 2),
        total_interest=round(total_interest, 2),
        cost_per_km=round(cost_per_km, 2),
        total_depreciation=round(total_depreciation, 2),
        resale_value=round(resale_value, 2),
        monthly_breakdown=MonthlyBreakdown(**monthly_breakdown),
        components=[TCOComponent(**comp) for comp in components],
        yearly_breakdown=[YearlyBreakdownItem(**year) for year in yearly_breakdown],
        loan_details=LoanDetails(**loan_details),
        vehicle_details=VehicleDetails(**vehicle_details),
        currency=currency,
        calculated_at=datetime.utcnow().isoformat()
    )
