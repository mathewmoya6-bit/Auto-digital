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
    """Ownership cost response"""
    total_cost: float
    monthly_payment: float
    total_interest: float
    breakdown: Dict[str, float]
    affordability_score: int
    recommendations: List[str]


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
    "FuelResponse",
    "MarketTrendsResponse",
    "ErrorResponse",
]
