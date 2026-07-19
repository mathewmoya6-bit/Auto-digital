"""
Response Schemas for API
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ValuationResponse(BaseModel):
    """Vehicle valuation response"""
    status: str = Field(..., description="Response status: success, error")
    data: Dict[str, Any] = Field(..., description="Valuation data")
    timestamp: str = Field(..., description="Response timestamp")
    message: Optional[str] = Field(None, description="Additional message")
    
    class Config:
        schema_extra = {
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


class ErrorResponse(BaseModel):
    """Error response"""
    status: str = "error"
    message: str
    errors: Optional[List[Dict[str, Any]]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class VehicleVariantResponse(BaseModel):
    """Vehicle variant details"""
    id: str
    name: str
    model_name: Optional[str] = None
    make_name: Optional[str] = None
    year: Optional[int] = None
    engine_cc: Optional[float] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    market_value: float
    depreciation_class: str
    body_type: Optional[str] = None
    fuel_consumption: Optional[float] = None
    insurance_group: Optional[int] = None


class MarketTrendsResponse(BaseModel):
    """Market trends response"""
    status: str
    data: Dict[str, Any]
    timestamp: str
