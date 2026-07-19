"""
Response Schemas for API - COMPLETE
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ─── BASE RESPONSE SCHEMAS ─────────────────────────────────────────

class CostComponent(BaseModel):
    """Individual cost component for running cost calculations"""
    name: str = Field(..., description="Name of the cost component")
    amount: float = Field(..., description="Cost amount in KES")
    percentage: float = Field(..., description="Percentage of total cost")
    description: Optional[str] = Field(None, description="Additional description")


class ValuationResponse(BaseModel):
    """Vehicle valuation response"""
    status: str = Field(..., description="Response status: success, error")
    data: Dict[str, Any] = Field(..., description="Valuation data")
    timestamp: str = Field(..., description="Response timestamp")
    message: Optional[str] = Field(None, description="Additional message")


# ─── VEHICLE RESPONSE SCHEMAS ─────────────────────────────────────

class VehicleMakeResponse(BaseModel):
    """Vehicle make response"""
    id: str
    name: str
    country: Optional[str] = None
    founded_year: Optional[int] = None
    logo_url: Optional[str] = None


class VehicleModelResponse(BaseModel):
    """Vehicle model response"""
    id: str
    make_id: str
    name: str
    body_type: Optional[str] = None
    class_type: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    make: Optional[VehicleMakeResponse] = None


class VehicleVariantResponse(BaseModel):
    """Vehicle variant response"""
    id: str
    model_id: str
    name: str
    year: int
    engine_cc: float
    fuel_type: str
    transmission: str
    drive_type: Optional[str] = None
    fuel_consumption: float
    insurance_group: int
    service_interval: int
    tyre_size: Optional[str] = None
    tyre_cost: float
    service_cost: float
    market_value: float
    depreciation_class: str
    vehicle_class: Optional[str] = None
    model: Optional[VehicleModelResponse] = None


class VehicleDetailResponse(BaseModel):
    """Detailed vehicle response with all information"""
    id: str
    name: str
    year: int
    engine_cc: float
    fuel_type: str
    transmission: str
    drive_type: Optional[str] = None
    fuel_consumption: float
    insurance_group: int
    service_interval: int
    tyre_size: Optional[str] = None
    tyre_cost: float
    service_cost: float
    market_value: float
    depreciation_class: str
    vehicle_class: Optional[str] = None
    model: Optional[VehicleModelResponse] = None
    make: Optional[VehicleMakeResponse] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class VehicleSearchResponse(BaseModel):
    """Vehicle search response"""
    items: List[VehicleVariantResponse]
    total: int
    limit: int
    offset: int


# ─── RUNNING COST RESPONSE SCHEMAS ────────────────────────────────

class RunningCostResponse(BaseModel):
    """Running cost calculation response"""
    total_annual_cost: float
    cost_per_km: float
    cost_per_month: float
    breakdown: Dict[str, float]
    components: List[CostComponent]
    projection: List[Dict[str, Any]] = Field(default=[])
    currency: str = "KES"
    recommendations: List[str] = Field(default=[])


# ─── MILEAGE RESPONSE SCHEMAS ─────────────────────────────────────

class MileageResponse(BaseModel):
    """Mileage adjustment response"""
    adjusted_value: float
    adjustment_percentage: float
    expected_mileage: float
    current_mileage: float
    recommendation: str


class MileageRateResponse(BaseModel):
    """Mileage rate calculation response"""
    total_cost_per_km: float
    total_annual_cost: float
    monthly_cost: float
    breakdown: Dict[str, float]
    fuel_cost_per_km: float
    depreciation_per_km: float
    insurance_per_km: float
    maintenance_per_km: float
    tyre_per_km: float
    annual_mileage: float
    currency: str = "KES"
    recommendations: List[str] = Field(default=[])


# ─── OWNERSHIP RESPONSE SCHEMAS ───────────────────────────────────

class OwnershipResponse(BaseModel):
    """Ownership cost response (paired with OwnershipRequest)"""
    total_cost: float
    monthly_payment: float
    total_interest: float
    breakdown: Dict[str, float]
    affordability_score: int
    recommendations: List[str]


class OwnershipCostResponse(BaseModel):
    """
    Ownership cost response (paired with OwnershipCostRequest).

    This was previously missing from response.py even though the request
    schema (OwnershipCostRequest) and the service (ownership_service.py)
    both already reference it — that mismatch is what caused:
    ImportError: cannot import name 'OwnershipCostResponse' from
    'app.schemas.response'.

    Fields are intentionally Optional with safe defaults beyond the core
    totals, so this stays compatible even if ownership_service.py doesn't
    populate every single one on every call.
    """
    # Core totals
    total_cost: float = Field(..., description="Total cost of ownership over the projection period")
    monthly_payment: float = Field(0, description="Estimated monthly loan payment")
    monthly_cost: Optional[float] = Field(None, description="Estimated total monthly cost (loan + running costs)")
    total_interest: Optional[float] = Field(None, description="Total interest paid over the loan term")

    # Cost breakdown
    breakdown: Dict[str, float] = Field(default_factory=dict, description="Cost breakdown by category")
    components: Optional[List[CostComponent]] = Field(default=None, description="Detailed cost components")

    # Individual cost drivers (optional, for UIs that want granular figures)
    depreciation_cost: Optional[float] = Field(None, description="Total depreciation cost")
    insurance_cost: Optional[float] = Field(None, description="Total insurance cost")
    maintenance_cost: Optional[float] = Field(None, description="Total maintenance cost")
    tyre_cost: Optional[float] = Field(None, description="Total tyre replacement cost")
    fuel_cost: Optional[float] = Field(None, description="Total fuel cost")

    # Projection / metadata
    projection: List[Dict[str, Any]] = Field(default_factory=list, description="Year-by-year cost projection")
    loan_term_years: Optional[int] = Field(None, description="Loan term in years, echoed from the request")
    annual_mileage: Optional[float] = Field(None, description="Annual mileage used in the calculation")
    affordability_score: Optional[int] = Field(None, description="Affordability score (0-100)")
    currency: str = "KES"
    recommendations: List[str] = Field(default_factory=list, description="Ownership recommendations")


# ─── FUEL RESPONSE SCHEMAS ────────────────────────────────────────

class FuelResponse(BaseModel):
    """Fuel cost response"""
    monthly_cost: float
    annual_cost: float
    cost_per_km: float
    fuel_consumption: float
    total_km_per_month: float


# ─── MARKET RESPONSE SCHEMAS ──────────────────────────────────────

class MarketTrendsResponse(BaseModel):
    """Market trends response"""
    status: str
    data: Dict[str, Any]
    timestamp: str


class ErrorResponse(BaseModel):
    """Error response"""
    status: str = "error"
    message: str
    errors: Optional[List[Dict[str, Any]]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── EXPORT ALL ─────────────────────────────────────────────────────

__all__ = [
    "CostComponent",
    "ValuationResponse",
    "VehicleMakeResponse",
    "VehicleModelResponse",
    "VehicleVariantResponse",
    "VehicleDetailResponse",
    "VehicleSearchResponse",
    "RunningCostResponse",
    "MileageResponse",
    "MileageRateResponse",
    "OwnershipResponse",
    "OwnershipCostResponse",
    "FuelResponse",
    "MarketTrendsResponse",
    "ErrorResponse",
]
