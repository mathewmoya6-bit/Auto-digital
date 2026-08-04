# app/modules/running_cost/schemas.py
# ================================================================
# Auto-D Kenya - Running Cost Schemas
# ================================================================
# TYPE: MODULE - Running Cost Pydantic schemas
# ================================================================

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator


# ================================================================
# REQUEST SCHEMAS
# ================================================================

class RunningCostRequest(BaseModel):
    """
    Running cost calculation request.
    
    Calculates:
    - Fuel cost
    - Service cost
    - Insurance cost
    - Depreciation cost
    - Total running cost
    """
    
    variant_id: int = Field(
        ...,
        gt=0,
        description="Vehicle variant database ID"
    )
    
    annual_mileage: int = Field(
        20000,
        ge=0,
        description="Annual mileage in KM"
    )
    
    fuel_price_per_liter: Optional[float] = Field(
        None,
        ge=0,
        description="Fuel price per liter (auto-detect if not provided)"
    )
    
    fuel_type: Optional[str] = Field(
        None,
        description="Fuel type (auto-detect if not provided)"
    )
    
    insurance_rate: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Insurance rate as percentage"
    )
    
    service_cost_per_km: Optional[float] = Field(
        None,
        ge=0,
        description="Service cost per KM (auto-calculate if not provided)"
    )
    
    ownership_years: int = Field(
        5,
        ge=1,
        description="Number of years of ownership"
    )
    
    include_depreciation: bool = Field(
        True,
        description="Include depreciation in calculation"
    )
    
    include_financing: bool = Field(
        False,
        description="Include financing costs"
    )
    
    interest_rate: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Financing interest rate"
    )
    
    down_payment_percent: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Down payment percentage"
    )


# ================================================================
# RESPONSE SCHEMAS
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


class RunningCostSummary(BaseModel):
    """Running cost summary."""
    
    total_annual_cost: float = Field(..., description="Total annual running cost")
    total_monthly_cost: float = Field(..., description="Total monthly running cost")
    total_weekly_cost: float = Field(..., description="Total weekly running cost")
    total_cost_per_km: float = Field(..., description="Total cost per kilometer")
    total_ownership_cost: float = Field(..., description="Total cost over ownership period")
    
    # Breakdown by category
    fuel: FuelCostBreakdown
    service: ServiceCostBreakdown
    insurance: InsuranceCostBreakdown
    depreciation: Optional[DepreciationBreakdown] = None
    financing: Optional[FinancingBreakdown] = None


class RunningCostResponse(BaseModel):
    """Running cost response."""
    
    vehicle: Dict[str, Any] = Field(..., description="Vehicle details")
    annual_mileage: int = Field(..., description="Annual mileage used")
    currency: str = Field("KES", description="Currency code")
    summary: RunningCostSummary = Field(..., description="Cost summary")
    breakdown_by_category: Dict[str, float] = Field(..., description="Cost breakdown by category")
    comparison: Optional[Dict[str, Any]] = Field(None, description="Comparison with average costs")
    recommendations: List[str] = Field(default_factory=list, description="Cost reduction recommendations")
    calculated_at: str = Field(..., description="Calculation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "vehicle": {
                    "make": "Toyota",
                    "model": "Corolla",
                    "variant": "1.8 GL",
                    "year": 2020
                },
                "annual_mileage": 20000,
                "currency": "KES",
                "summary": {
                    "total_annual_cost": 450000,
                    "total_monthly_cost": 37500,
                    "total_weekly_cost": 8653.85,
                    "total_cost_per_km": 22.50,
                    "total_ownership_cost": 2250000,
                    "fuel": {
                        "annual_cost": 150000,
                        "monthly_cost": 12500,
                        "weekly_cost": 2884.62,
                        "cost_per_km": 7.50,
                        "fuel_efficiency": 14.0,
                        "fuel_price": 214.03,
                        "liters_per_year": 700
                    },
                    "service": {
                        "annual_cost": 50000,
                        "monthly_cost": 4166.67,
                        "weekly_cost": 961.54,
                        "cost_per_km": 2.50,
                        "service_interval": 5000,
                        "services_per_year": 4,
                        "average_service_cost": 12500
                    },
                    "insurance": {
                        "annual_cost": 100000,
                        "monthly_cost": 8333.33,
                        "weekly_cost": 1923.08,
                        "cost_per_km": 5.00,
                        "premium_rate": 0.045,
                        "insured_value": 3500000
                    }
                },
                "breakdown_by_category": {
                    "fuel": 150000,
                    "service": 50000,
                    "insurance": 100000,
                    "depreciation": 150000
                },
                "recommendations": [
                    "Consider diesel variant for better fuel economy",
                    "Regular servicing can reduce maintenance costs"
                ],
                "calculated_at": "2024-01-15T10:30:00"
            }
        }


# ================================================================
# LEGACY RESPONSE SCHEMA
# ================================================================

class LegacyRunningCostResponse(BaseModel):
    """
    Legacy running cost response for backward compatibility.
    
    Used by the /running-cost/calculate-legacy endpoint.
    """
    
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
    
    class Config:
        json_schema_extra = {
            "example": {
                "vehicle_make": "Toyota",
                "vehicle_model": "Corolla",
                "vehicle_variant": "1.8 GL",
                "vehicle_year": 2020,
                "annual_cost": 450000,
                "monthly_cost": 37500,
                "weekly_cost": 8653.85,
                "cost_per_km": 22.50,
                "total_ownership_cost": 2250000,
                "fuel_cost": 150000,
                "service_cost": 50000,
                "insurance_cost": 100000,
                "depreciation_cost": 150000,
                "currency": "KES",
                "annual_mileage": 20000,
                "fuel_efficiency": 14.0,
                "fuel_price": 214.03,
                "insurance_rate": 0.045,
                "service_interval": 5000,
                "recommendations": [
                    "Consider diesel variant for better fuel economy"
                ],
                "calculated_at": "2024-01-15T10:30:00"
            }
        }


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
    
    # Response schemas
    "RunningCostResponse",
    "LegacyRunningCostResponse",
    "RunningCostComparisonResponse",
    "RunningCostHistoryResponse",
    "RunningCostHealthResponse",
    
    # Component schemas
    "FuelCostBreakdown",
    "ServiceCostBreakdown",
    "InsuranceCostBreakdown",
    "DepreciationBreakdown",
    "FinancingBreakdown",
    "RunningCostSummary",
    "RunningCostComparisonItem",
    "RunningCostHistoryItem",
]
