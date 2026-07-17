# backend/app/models/fuel.py
"""
Fuel Models - Fuel price tracking
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


class FuelPrice(BaseModel):
    """Fuel price model"""
    id: Optional[str] = None
    fuel_type: str = Field(..., description="petrol, diesel, electric, lpg, cng")
    price: float = Field(..., gt=0, description="Price per liter/kWh in KES")
    currency: str = Field("KES", max_length=3)
    region: Optional[str] = Field(None, max_length=50, description="Region/city")
    source: Optional[str] = Field(None, max_length=100, description="Data source")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    @validator('fuel_type')
    def validate_fuel_type(cls, v):
        valid_types = ['petrol', 'diesel', 'electric', 'lpg', 'cng', 'hybrid']
        if v.lower() not in valid_types:
            raise ValueError(f'Fuel type must be one of: {", ".join(valid_types)}')
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "fuel_type": "petrol",
                "price": 214.03,
                "currency": "KES",
                "region": "Nairobi",
                "source": "Auto-D Database"
            }
        }


class FuelPriceUpdate(BaseModel):
    """Fuel price update model"""
    price: float = Field(..., gt=0, description="New price in KES")
    region: Optional[str] = None
    source: Optional[str] = None


class FuelPriceResponse(BaseModel):
    """Fuel price response model"""
    fuel_type: str
    price: float
    currency: str = "KES"
    region: Optional[str] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True
