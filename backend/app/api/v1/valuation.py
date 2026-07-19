"""
Request Schemas for API
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class ValuationRequest(BaseModel):
    """Vehicle valuation request model"""
    variant_id: str = Field(..., description="Vehicle variant ID from database")
    year: int = Field(..., ge=1990, le=datetime.now().year, description="Year of manufacture")
    mileage: float = Field(..., ge=0, le=1000000, description="Current odometer reading in km")
    condition: str = Field("good", description="Vehicle condition: excellent, very_good, good, fair, poor")
    accident_history: str = Field("none", description="Accident history: none, minor, major, total_loss")
    previous_owners: int = Field(0, ge=0, le=20, description="Number of previous owners")
    service_history: bool = Field(True, description="Whether service history is available")
    location: str = Field("nairobi", description="Vehicle location/county")
    modifications: Optional[List[str]] = Field(default=[], description="List of modifications")
    custom_adjustments: Optional[Dict[str, float]] = Field(default={}, description="Custom value adjustments")
    images: Optional[List[str]] = Field(None, description="Base64 encoded images for AI analysis")
    
    @validator('condition')
    def validate_condition(cls, v):
        allowed = ['excellent', 'very_good', 'good', 'fair', 'poor']
        if v.lower() not in allowed:
            raise ValueError(f"Condition must be one of: {', '.join(allowed)}")
        return v.lower()
    
    @validator('accident_history')
    def validate_accident(cls, v):
        allowed = ['none', 'minor', 'major', 'total_loss']
        if v.lower() not in allowed:
            raise ValueError(f"Accident history must be one of: {', '.join(allowed)}")
        return v.lower()
    
    @validator('location')
    def validate_location(cls, v):
        # Common Kenyan counties
        allowed = [
            'nairobi', 'mombasa', 'kisumu', 'nakuru', 'eldoret', 'thika',
            'kiambu', 'kajiado', 'machakos', 'meru', 'nyeri', 'embu',
            'malindi', 'nanyuki', 'other'
        ]
        if v.lower() not in allowed:
            # Don't reject, just warn
            pass
        return v.lower()


class BatchValuationRequest(BaseModel):
    """Batch valuation request"""
    requests: List[ValuationRequest] = Field(..., min_items=1, max_items=20)


class VehicleSearchRequest(BaseModel):
    """Vehicle search request"""
    make: Optional[str] = None
    model: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    vehicle_type: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
