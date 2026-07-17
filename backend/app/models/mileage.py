# backend/app/models/mileage.py
"""
Mileage Models - Mileage report and calculations
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class MileageReport(BaseModel):
    """Mileage report model"""
    id: Optional[str] = None
    user_id: str = Field(..., description="User who generated the report")
    vehicle_id: str = Field(..., description="Vehicle variant ID")
    trip_distance: float = Field(..., gt=0, description="Distance in km")
    trip_type: str = Field("mixed", description="urban, highway, mixed, offroad")
    driving_style: str = Field("normal", description="eco, normal, aggressive")
    annual_mileage: float = Field(20000, gt=0, description="Annual km")
    fuel_price: Optional[float] = Field(None, gt=0, description="Fuel price used")
    
    # Results
    total_cost: float = Field(..., gt=0, description="Total trip cost")
    cost_per_km: float = Field(..., gt=0, description="Cost per km")
    components: Dict[str, float] = Field(default_factory=dict, description="Cost breakdown")
    fuel_consumption: Optional[float] = None
    co2_emissions: Optional[float] = None
    
    # Status
    status: str = "completed"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('trip_type')
    def validate_trip_type(cls, v):
        valid_types = ['urban', 'highway', 'mixed', 'offroad']
        if v.lower() not in valid_types:
            raise ValueError(f'Trip type must be one of: {", ".join(valid_types)}')
        return v.lower()
    
    @validator('driving_style')
    def validate_driving_style(cls, v):
        valid_styles = ['eco', 'normal', 'aggressive']
        if v.lower() not in valid_styles:
            raise ValueError(f'Driving style must be one of: {", ".join(valid_styles)}')
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "vehicle_id": "prado_tx_2019",
                "trip_distance": 150,
                "trip_type": "mixed",
                "driving_style": "normal",
                "annual_mileage": 20000,
                "total_cost": 6493,
                "cost_per_km": 43.29,
                "components": {
                    "fuel": 2140,
                    "service": 350,
                    "tyres": 240,
                    "insurance": 520,
                    "depreciation": 1305,
                    "repairs": 180,
                    "financing": 0,
                    "misc": 160
                }
            }
        }


class MileageRequest(BaseModel):
    """Mileage calculation request"""
    variant_id: str
    distance: float = Field(..., gt=0, description="Distance in km")
    annual_mileage: Optional[float] = Field(20000, gt=0)
    trip_type: str = "mixed"
    driving_style: str = "normal"
    fuel_price: Optional[float] = None


class MileageResponse(BaseModel):
    """Mileage calculation response"""
    variant_id: str
    distance: float
    trip_type: str
    driving_style: str
    total_cost: float
    cost_per_km: float
    components: Dict[str, float]
    fuel_consumption: Optional[float] = None
    co2_emissions: Optional[float] = None
    
    class Config:
        from_attributes = True
