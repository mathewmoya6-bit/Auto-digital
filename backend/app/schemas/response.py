"""
Response Schemas for API
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
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Fuel",
                "amount": 120000,
                "percentage": 45.5,
                "description": "Annual fuel cost based on 20,000km/year"
            }
        }


class ValuationResponse(BaseModel):
    """Vehicle valuation response"""
    status: str = Field(..., description="Response status: success, error")
    data: Dict[str, Any] = Field(..., description="Valuation data")
    timestamp: str = Field(..., description="Response timestamp")
    message: Optional[str] = Field(None, description="Additional message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data": {
                    "market_value": 3500000,
                    "trade_value": 2975000,
                    "retail_value": 4200000,
                    "dealer_value": 3850000,
                    "quick_sale": 2800000,
                    "insurance_value": 4375000,
                    "base_value": 5000000,
                    "depreciation_rate": 30.0,
                    "estimated_life": 12,
                    "confidence_score": 82.5,
                    "recommendations": [
                        "✅ Excellent value retention!",
                        "📊 With 45,000 km, this vehicle has below-average mileage"
                    ],
                    "market_adjustments": {
                        "age": -30.0,
                        "mileage": 5.0,
                        "condition": 6.0,
                        "location": 5.0,
                        "owners": -2.0
                    },
                    "valuation_date": "2026-07-19T10:30:00",
                    "age_years": 3,
                    "value_retained": 70.0
                },
                "timestamp": "2026-07-19T10:30:00",
                "message": "Valuation calculated successfully"
            }
        }


# ─── VEHICLE RESPONSE SCHEMAS ─────────────────────────────────────

class VehicleMakeResponse(BaseModel):
    """Vehicle make response"""
    id: str
    name: str
    country: Optional[str] = None
    founded_year: Optional[int] = None
    logo_url: Optional[str] = None
    
    class Config:
        from_attributes = True


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
    
    class Config:
        from_attributes = True


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
    
    class Config:
        from_attributes = True


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
    
    class Config:
        from_attributes = True


class VehicleSearchResponse(BaseModel):
    """Vehicle search response"""
    items: List[VehicleVariantResponse]
    total: int
    limit: int
    offset: int


# ─── RUNNING COST RESPONSE SCHEMAS ────────────────────────────────

class RunningCostResponse(BaseModel):
    """Running cost calculation response"""
    total_annual_cost: float = Field(..., description="Total annual cost in KES")
    cost_per_km: float = Field(..., description="Cost per kilometer in KES")
    cost_per_month: float = Field(..., description="Cost per month in KES")
    breakdown: Dict[str, float] = Field(..., description="Cost breakdown by category")
    components: List[CostComponent] = Field(..., description="Detailed cost components")
    projection: List[Dict[str, Any]] = Field(default=[], description="Cost projection over years")
    currency: str = Field("KES", description="Currency code")
    recommendations: List[str] = Field(default=[], description="Cost saving recommendations")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_annual_cost": 265000,
                "cost_per_km": 13.25,
                "cost_per_month": 22083.33,
                "breakdown": {
                    "fuel": 120000,
                    "insurance": 50000,
                    "maintenance": 30000,
                    "tyres": 15000,
                    "depreciation": 50000
                },
                "components": [
                    {
                        "name": "Fuel",
                        "amount": 120000,
                        "percentage": 45.28,
                        "description": "Annual fuel cost based on 20,000km/year"
                    },
                    {
                        "name": "Insurance",
                        "amount": 50000,
                        "percentage": 18.87,
                        "description": "Annual comprehensive insurance premium"
                    }
                ],
                "projection": [],
                "currency": "KES",
                "recommendations": [
                    "Consider diesel variant for lower fuel costs",
                    "Regular servicing can reduce maintenance costs"
                ]
            }
        }


# ─── MILEAGE RESPONSE SCHEMAS ─────────────────────────────────────

class MileageResponse(BaseModel):
    """Mileage adjustment response"""
    adjusted_value: float
    adjustment_percentage: float
    expected_mileage: float
    current_mileage: float
    recommendation: str


# ─── ADD MISSING SCHEMA ──────────────────────────────────────────

class MileageRateResponse(BaseModel):
    """Mileage rate calculation response"""
    total_cost_per_km: float = Field(..., description="Total cost per kilometer in KES")
    total_annual_cost: float = Field(..., description="Total annual cost in KES")
    monthly_cost: float = Field(..., description="Monthly cost in KES")
    breakdown: Dict[str, float] = Field(..., description="Cost breakdown by category")
    fuel_cost_per_km: float = Field(..., description="Fuel cost per kilometer")
    depreciation_per_km: float = Field(..., description="Depreciation cost per kilometer")
    insurance_per_km: float = Field(..., description="Insurance cost per kilometer")
    maintenance_per_km: float = Field(..., description="Maintenance cost per kilometer")
    tyre_per_km: float = Field(..., description="Tyre cost per kilometer")
    annual_mileage: float = Field(..., description="Annual mileage in km")
    currency: str = Field("KES", description="Currency code")
    recommendations: List[str] = Field(default=[], description="Cost saving recommendations")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_cost_per_km": 12.50,
                "total_annual_cost": 250000,
                "monthly_cost": 20833.33,
                "breakdown": {
                    "fuel": 120000,
                    "depreciation": 60000,
                    "insurance": 50000,
                    "maintenance": 30000,
                    "tyres": 15000
                },
                "fuel_cost_per_km": 6.00,
                "depreciation_per_km": 3.00,
                "insurance_per_km": 2.50,
                "maintenance_per_km": 1.50,
                "tyre_per_km": 0.75,
                "annual_mileage": 20000,
                "currency": "KES",
                "recommendations": [
                    "Fuel cost is high. Consider a more fuel-efficient vehicle."
                ]
            }
        }


# ─── OTHER RESPONSE SCHEMAS ───────────────────────────────────────

class OwnershipResponse(BaseModel):
    """Ownership cost response"""
    total_cost: float
    monthly_payment: float
    total_interest: float
    breakdown: Dict[str, float]
    affordability_score: int
    recommendations: List[str]


class FuelResponse(BaseModel):
    """Fuel cost response"""
    monthly_cost: float
    annual_cost: float
    cost_per_km: float
    fuel_consumption: float
    total_km_per_month: float


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
    "MileageRateResponse",  # ← Added
    "OwnershipResponse",
    "FuelResponse",
    "MarketTrendsResponse",
    "ErrorResponse",
]
