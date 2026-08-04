# app/modules/running_cost/schemas.py
# ================================================================
# Auto-D Kenya - Running Cost Schemas
# ================================================================
# TYPE: MODULE - Running Cost Pydantic schemas
# ================================================================

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


# ================================================================
# REQUEST SCHEMAS
# ================================================================

class RunningCostRequest(BaseModel):
    """Running cost calculation request."""

    variant_id: int = Field(..., gt=0, description="Vehicle variant database ID")
    annual_mileage: int = Field(20000, ge=0, description="Annual mileage in KM")
    fuel_price_per_liter: Optional[float] = Field(None, ge=0, description="Fuel price per liter")
    fuel_type: Optional[str] = Field(None, description="Fuel type")
    insurance_rate: Optional[float] = Field(None, ge=0, le=1, description="Insurance rate as percentage")
    service_cost_per_km: Optional[float] = Field(None, ge=0, description="Service cost per KM")
    ownership_years: int = Field(5, ge=1, description="Number of years of ownership")
    include_depreciation: bool = Field(True, description="Include depreciation")
    include_financing: bool = Field(False, description="Include financing costs")
    interest_rate: Optional[float] = Field(None, ge=0, le=1, description="Financing interest rate")
    down_payment_percent: Optional[float] = Field(None, ge=0, le=1, description="Down payment percentage")


class RunningCostProjectionRequest(BaseModel):
    """Running cost projection request."""

    variant_id: int = Field(..., gt=0, description="Vehicle variant database ID")
    annual_mileage: int = Field(20000, ge=0, description="Annual mileage in KM")
    years: int = Field(5, ge=1, le=20, description="Number of years to project")
    inflation_rate: float = Field(0.05, ge=0, le=1, description="Annual inflation rate")
    mileage_increase_rate: float = Field(0.02, ge=0, le=1, description="Annual mileage increase rate")
    include_depreciation: bool = Field(True, description="Include depreciation")


# ================================================================
# BREAKDOWN SCHEMAS
# ================================================================

class FuelCostBreakdown(BaseModel):
    """Fuel cost breakdown."""

    annual_cost: float = Field(..., description="Annual fuel cost")
    monthly_cost: float = Field(..., description="Monthly fuel cost")
    weekly_cost: float = Field(..., description="Weekly fuel cost")
    cost_per_km: float = Field(..., description="Cost per kilometer")
    fuel_efficiency: float = Field(..., description="Fuel efficiency in KM/L")
    fuel_price: float = Field(..., description="Fuel price per liter")
    liters_per_year: float = Field(..., description="Liters consumed per year")


class ServiceCostBreakdown(BaseModel):
    """Service cost breakdown."""

    annual_cost: float = Field(..., description="Annual service cost")
    monthly_cost: float = Field(..., description="Monthly service cost")
    weekly_cost: float = Field(..., description="Weekly service cost")
    cost_per_km: float = Field(..., description="Cost per kilometer")
    service_interval: int = Field(..., description="Service interval in KM")
    services_per_year: float = Field(..., description="Number of services per year")
    average_service_cost: float = Field(..., description="Average cost per service")


class InsuranceCostBreakdown(BaseModel):
    """Insurance cost breakdown."""

    annual_cost: float = Field(..., description="Annual insurance cost")
    monthly_cost: float = Field(..., description="Monthly insurance cost")
    weekly_cost: float = Field(..., description="Weekly insurance cost")
    cost_per_km: float = Field(..., description="Cost per kilometer")
    premium_rate: float = Field(..., description="Insurance premium rate")
    insured_value: float = Field(..., description="Insured vehicle value")


class DepreciationBreakdown(BaseModel):
    """Depreciation breakdown."""

    annual_depreciation: float = Field(..., description="Annual depreciation")
    monthly_depreciation: float = Field(..., description="Monthly depreciation")
    weekly_depreciation: float = Field(..., description="Weekly depreciation")
    cost_per_km: float = Field(..., description="Depreciation per kilometer")
    depreciation_rate: float = Field(..., description="Annual depreciation rate")
    initial_value: float = Field(..., description="Initial vehicle value")
    final_value: float = Field(..., description="Final vehicle value after ownership period")


class FinancingBreakdown(BaseModel):
    """Financing cost breakdown."""

    monthly_installment: float = Field(..., description="Monthly installment")
    annual_interest: float = Field(..., description="Annual interest cost")
    total_interest: float = Field(..., description="Total interest over period")
    total_repayment: float = Field(..., description="Total repayment amount")
    down_payment: float = Field(..., description="Down payment amount")
    loan_amount: float = Field(..., description="Total loan amount")
    interest_rate: float = Field(..., description="Interest rate")
    loan_term_months: int = Field(..., description="Loan term in months")


# ================================================================
# PROJECTION SCHEMA
# ================================================================

class ProjectionYear(BaseModel):
    """Single year projection data."""

    year: int = Field(..., description="Year number (1-based)")
    annual_mileage: int = Field(..., description="Annual mileage for this year")
    fuel_cost: float = Field(..., description="Fuel cost for this year")
    service_cost: float = Field(..., description="Service cost for this year")
    insurance_cost: float = Field(..., description="Insurance cost for this year")
    depreciation_cost: Optional[float] = Field(None, description="Depreciation cost")
    total_cost: float = Field(..., description="Total cost for this year")
    cumulative_cost: float = Field(..., description="Cumulative cost up to this year")
    cost_per_km: float = Field(..., description="Cost per kilometer for this year")


# ================================================================
# SUMMARY SCHEMA
# ================================================================

class RunningCostSummary(BaseModel):
    """Running cost summary."""

    total_annual_cost: float = Field(..., description="Total annual running cost")
    total_monthly_cost: float = Field(..., description="Total monthly running cost")
    total_weekly_cost: float = Field(..., description="Total weekly running cost")
    total_cost_per_km: float = Field(..., description="Total cost per kilometer")
    total_ownership_cost: float = Field(..., description="Total cost over ownership period")
    fuel: FuelCostBreakdown = Field(..., description="Fuel cost breakdown")
    service: ServiceCostBreakdown = Field(..., description="Service cost breakdown")
    insurance: InsuranceCostBreakdown = Field(..., description="Insurance cost breakdown")
    depreciation: Optional[DepreciationBreakdown] = Field(None, description="Depreciation breakdown")
    financing: Optional[FinancingBreakdown] = Field(None, description="Financing breakdown")


# ================================================================
# RESPONSE SCHEMAS
# ================================================================

class VehicleSummary(BaseModel):
    """Minimal vehicle identity block used in running-cost responses.

    Prefer this over a bare Dict[str, Any] so callers can't accidentally
    pass a live ORM instance (with circular relationship attributes) into
    the response model.
    """

    id: int = Field(..., description="Variant database ID")
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    variant: str = Field(..., description="Vehicle variant/trim")
    year: Optional[int] = Field(None, description="Model year")


class RunningCostResponse(BaseModel):
    """Running cost response."""

    vehicle: VehicleSummary = Field(..., description="Vehicle details")
    annual_mileage: int = Field(..., description="Annual mileage used")
    currency: str = Field("KES", description="Currency code")
    summary: RunningCostSummary = Field(..., description="Cost summary")
    breakdown_by_category: Dict[str, float] = Field(..., description="Cost breakdown by category")
    comparison: Optional[Dict[str, Any]] = Field(None, description="Comparison with average costs")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    calculated_at: str = Field(..., description="Calculation timestamp")


class RunningCostProjectionResponse(BaseModel):
    """Running cost projection response."""

    vehicle: VehicleSummary = Field(..., description="Vehicle details")
    initial_annual_mileage: int = Field(..., description="Initial annual mileage")
    years: int = Field(..., description="Number of years projected")
    inflation_rate: float = Field(..., description="Inflation rate used")
    mileage_increase_rate: float = Field(..., description="Mileage increase rate used")
    currency: str = Field("KES", description="Currency code")
    yearly_projections: List[ProjectionYear] = Field(..., description="Year-by-year projections")
    total_cost_over_period: float = Field(..., description="Total cost over the projection period")
    average_annual_cost: float = Field(..., description="Average annual cost")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    calculated_at: str = Field(..., description="Calculation timestamp")


# ================================================================
# LEGACY RESPONSE SCHEMA
# ================================================================

class LegacyRunningCostResponse(BaseModel):
    """Legacy running cost response for backward compatibility."""

    vehicle_make: str = Field(..., description="Vehicle make")
    vehicle_model: str = Field(..., description="Vehicle model")
    vehicle_variant: str = Field(..., description="Vehicle variant")
    vehicle_year: int = Field(..., description="Vehicle year")
    annual_cost: float = Field(..., description="Total annual running cost")
    monthly_cost: float = Field(..., description="Total monthly running cost")
    weekly_cost: float = Field(..., description="Total weekly running cost")
    cost_per_km: float = Field(..., description="Cost per kilometer")
    total_ownership_cost: float = Field(..., description="Total cost over ownership period")
    fuel_cost: float = Field(..., description="Annual fuel cost")
    service_cost: float = Field(..., description="Annual service cost")
    insurance_cost: float = Field(..., description="Annual insurance cost")
    depreciation_cost: Optional[float] = Field(None, description="Annual depreciation cost")
    financing_cost: Optional[float] = Field(None, description="Annual financing cost")
    currency: str = Field("KES", description="Currency code")
    annual_mileage: int = Field(..., description="Annual mileage used")
    fuel_efficiency: float = Field(..., description="Fuel efficiency in KM/L")
    fuel_price: float = Field(..., description="Fuel price per liter")
    insurance_rate: float = Field(..., description="Insurance premium rate")
    service_interval: int = Field(..., description="Service interval in KM")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    calculated_at: str = Field(..., description="Calculation timestamp")


# ================================================================
# COMPARISON SCHEMAS
# ================================================================

class RunningCostComparisonItem(BaseModel):
    """Comparison item for running costs."""

    vehicle_name: str = Field(..., description="Vehicle name")
    total_annual_cost: float = Field(..., description="Total annual cost")
    fuel_cost: float = Field(..., description="Fuel cost")
    service_cost: float = Field(..., description="Service cost")
    insurance_cost: float = Field(..., description="Insurance cost")
    cost_per_km: float = Field(..., description="Cost per kilometer")
    vs_average: Optional[float] = Field(None, description="Difference from average")


class RunningCostComparisonResponse(BaseModel):
    """Running cost comparison response."""

    vehicles: List[RunningCostComparisonItem] = Field(..., description="List of vehicle comparisons")
    average_cost: float = Field(..., description="Average annual cost")
    cheapest: str = Field(..., description="Name of cheapest vehicle")
    most_expensive: str = Field(..., description="Name of most expensive vehicle")
    currency: str = Field("KES", description="Currency code")


# ================================================================
# HISTORY SCHEMAS
# ================================================================

class RunningCostHistoryItem(BaseModel):
    """Running cost history item."""

    id: str = Field(..., description="Record ID")
    vehicle_id: str = Field(..., description="Vehicle ID")
    annual_mileage: int = Field(..., description="Annual mileage")
    total_annual_cost: float = Field(..., description="Total annual cost")
    total_monthly_cost: float = Field(..., description="Total monthly cost")
    cost_per_km: float = Field(..., description="Cost per kilometer")
    calculated_at: datetime = Field(..., description="Calculation timestamp")
    currency: str = Field("KES", description="Currency code")


class RunningCostHistoryResponse(BaseModel):
    """Running cost history response."""

    items: List[RunningCostHistoryItem] = Field(default_factory=list, description="History items")
    total: int = Field(0, description="Total number of items")


# ================================================================
# HEALTH SCHEMAS
# ================================================================

class RunningCostHealthResponse(BaseModel):
    """Running cost service health response."""

    status: str = Field(..., description="Service status")
    service: str = "running-cost"
    version: str = "1.0"
    timestamp: str = Field(..., description="Current timestamp")


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    # Request schemas
    "RunningCostRequest",
    "RunningCostProjectionRequest",

    # Response schemas
    "RunningCostResponse",
    "RunningCostProjectionResponse",
    "LegacyRunningCostResponse",
    "RunningCostComparisonResponse",
    "RunningCostHistoryResponse",
    "RunningCostHealthResponse",

    # Component schemas
    "VehicleSummary",
    "FuelCostBreakdown",
    "ServiceCostBreakdown",
    "InsuranceCostBreakdown",
    "DepreciationBreakdown",
    "FinancingBreakdown",
    "RunningCostSummary",
    "ProjectionYear",
    "RunningCostComparisonItem",
    "RunningCostHistoryItem",
]
