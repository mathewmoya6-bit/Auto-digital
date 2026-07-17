# backend/app/models/ownership.py
"""
Ownership Models - Total cost of ownership calculations
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class OwnershipReport(BaseModel):
    """Ownership cost report model"""
    id: Optional[str] = None
    user_id: str = Field(..., description="User who generated the report")
    vehicle_id: str = Field(..., description="Vehicle variant ID")
    years_owned: int = Field(..., ge=1, le=20, description="Years of ownership")
    annual_mileage: float = Field(20000, gt=0, description="Annual km")
    usage_type: str = Field("private", description="private, commercial, fleet, taxi")
    condition: str = Field("good", description="excellent, good, fair, poor")
    financed: bool = False
    
    # Financials
    purchase_price: float = Field(..., gt=0, description="Initial purchase price")
    resale_value: float = Field(..., gt=0, description="Estimated resale value")
    total_cost: float = Field(..., gt=0, description="Total ownership cost")
    cost_per_km: float = Field(..., gt=0, description="Cost per km")
    cost_per_month: float = Field(..., gt=0, description="Cost per month")
    value_retained: float = Field(..., ge=0, le=100, description="Percentage retained")
    
    # Breakdowns
    yearly_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    component_breakdown: Dict[str, float] = Field(default_factory=dict)
    
    # Environment
    co2_total: Optional[float] = None
    trees_to_offset: Optional[float] = None
    
    status: str = "completed"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('usage_type')
    def validate_usage_type(cls, v):
        valid_types = ['private', 'commercial', 'fleet', 'taxi', 'rental']
        if v.lower() not in valid_types:
            raise ValueError(f'Usage type must be one of: {", ".join(valid_types)}')
        return v.lower()
    
    @validator('condition')
    def validate_condition(cls, v):
        valid_conditions = ['excellent', 'very_good', 'good', 'fair', 'poor']
        if v.lower() not in valid_conditions:
            raise ValueError(f'Condition must be one of: {", ".join(valid_conditions)}')
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "vehicle_id": "prado_tx_2019",
                "years_owned": 5,
                "annual_mileage": 20000,
                "usage_type": "private",
                "condition": "good",
                "financed": False,
                "purchase_price": 5200000,
                "resale_value": 2600000,
                "total_cost": 9850000,
                "cost_per_km": 98.50,
                "cost_per_month": 164167,
                "value_retained": 50
            }
        }


class OwnershipRequest(BaseModel):
    """Ownership calculation request"""
    variant_id: str
    years_owned: int = Field(..., ge=1, le=20)
    annual_mileage: float = Field(20000, gt=0)
    usage_type: str = "private"
    condition: str = "good"
    financed: bool = False
    down_payment_percent: Optional[float] = Field(None, ge=0, le=100)
    interest_rate: Optional[float] = Field(None, ge=0, le=100)
    loan_term: Optional[int] = Field(None, ge=1, le=7)
    fuel_price: Optional[float] = None
    
    @validator('usage_type')
    def validate_usage_type(cls, v):
        valid_types = ['private', 'commercial', 'fleet', 'taxi', 'rental']
        if v.lower() not in valid_types:
            raise ValueError(f'Usage type must be one of: {", ".join(valid_types)}')
        return v.lower()


class OwnershipResponse(BaseModel):
    """Ownership calculation response"""
    variant_id: str
    vehicle_name: str
    years_owned: int
    annual_mileage: float
    usage_type: str
    condition: str
    
    purchase_price: float
    resale_value: float
    total_cost: float
    cost_per_km: float
    cost_per_month: float
    value_retained: float
    
    yearly_breakdown: List[Dict[str, Any]]
    component_breakdown: Dict[str, float]
    recommendations: List[Dict[str, Any]]
    
    co2_total: Optional[float] = None
    trees_to_offset: Optional[float] = None
    
    class Config:
        from_attributes = True


class YearlyCostBreakdown(BaseModel):
    """Yearly breakdown model"""
    year: int
    total: float
    depreciation: float
    financing: float
    insurance: float
    fuel: float
    maintenance: float
    tyres: float
    licensing: float
    vehicle_value: float
    components: Dict[str, float] = Field(default_factory=dict)
