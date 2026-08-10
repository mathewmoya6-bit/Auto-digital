# app/modules/valuation/schemas.py
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ValuationRequest(BaseModel):
    """Request model for vehicle valuation."""

    crsp_id: Optional[int] = Field(None, description="CRSP vehicle ID")
    make: Optional[str] = Field(None, description="Vehicle make")
    model: Optional[str] = Field(None, description="Vehicle model")
    manufacture_year: Optional[int] = Field(None, description="Manufacture year")
    mileage: int = Field(0, ge=0, description="Mileage in KM")
    condition: str = Field("good", description="Condition: excellent, very_good, good, fair, poor")
    accident_history: str = Field("none", description="Accident history: none, minor, major, total_loss")
    previous_owners: int = Field(0, ge=0, description="Number of previous owners")
    location: Optional[str] = Field(None, description="Location")
    fuel_type: Optional[str] = Field(None, description="Fuel type")
    transmission: Optional[str] = Field(None, description="Transmission type")
    engine_capacity_id: Optional[int] = Field(None, description="Engine capacity ID")
    vehicle_type: Optional[str] = Field(None, description="Vehicle type")
    body_type: Optional[str] = Field(None, description="Body type")

    @field_validator("condition")
    def validate_condition(cls, v: str) -> str:
        valid = ["excellent", "very_good", "very good", "good", "fair", "poor"]
        if v and v.lower() not in valid:
            raise ValueError(f"Condition must be one of: {', '.join(valid)}")
        return v

    @field_validator("accident_history")
    def validate_accident_history(cls, v: str) -> str:
        valid = ["none", "minor", "major", "total_loss", "total loss"]
        if v and v.lower() not in valid:
            raise ValueError(f"Accident history must be one of: {', '.join(valid)}")
        return v


class CRSPSearchRequest(BaseModel):
    """Request model for CRSP search."""

    make: Optional[str] = Field(None, description="Vehicle make")
    model: Optional[str] = Field(None, description="Vehicle model")
    manufacture_year: Optional[int] = Field(None, description="Manufacture year")
    engine_capacity_id: Optional[int] = Field(None, description="Engine capacity ID")
    fuel_type: Optional[str] = Field(None, description="Fuel type")
    transmission: Optional[str] = Field(None, description="Transmission type")
    body_type: Optional[str] = Field(None, description="Body type")
    limit: int = Field(25, ge=1, le=100, description="Results limit")


class ValuationResponse(BaseModel):
    """Response model for vehicle valuation."""

    success: bool
    status: str
    crsp_found: bool
    crsp_id: Optional[int]
    crsp_value: Optional[float]
    estimated_value: Optional[float]
    estimated_value_min: Optional[float]
    estimated_value_max: Optional[float]
    confidence_score: int
    adjustments: Optional[Dict[str, Any]]
    vehicle: Dict[str, Any]
    message: str


class ValuationHistoryItem(BaseModel):
    """Model for a single valuation history item."""

    id: int
    user_id: str
    crsp_id: Optional[int]
    make: Optional[str]
    model: Optional[str]
    manufacture_year: Optional[int]
    mileage: int
    estimated_value: float
    confidence_score: int
    condition: str
    accident_history: str
    location: Optional[str]
    fuel_type: Optional[str]
    transmission: Optional[str]
    body_type: Optional[str]
    adjustments: Optional[Dict[str, Any]]
    created_at: datetime


class ValuationHistoryResponse(BaseModel):
    """Response model for valuation history."""

    items: List[ValuationHistoryItem]
    total: int
    page: int
    limit: int


class ValuationStatsResponse(BaseModel):
    """Response model for valuation statistics."""

    total_valuations: int
    average_value: float
    highest_value: float
    lowest_value: float
    total_value: float
    average_confidence: float
    last_valuation_date: Optional[datetime]
    valuations_by_make: Dict[str, int]
    valuations_by_month: Dict[str, int]


class HealthCheckResponse(BaseModel):
    """Response model for health check."""

    status: str
    service: str
    version: str
    timestamp: datetime
    database: str
