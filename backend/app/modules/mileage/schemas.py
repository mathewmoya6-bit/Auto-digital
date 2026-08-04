# app/modules/mileage/schemas.py

"""
Mileage API Schemas
===================

Request and response schemas for the mileage API endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


# ─── Request Schemas ──────────────────────────────────────────────

class MileageCreate(BaseModel):
    """Schema for creating a new mileage record."""
    
    vehicle_id: str = Field(..., description="Vehicle ID")
    mileage: int = Field(..., gt=0, description="Current mileage in kilometers")
    location: Optional[str] = Field(None, description="Location of recording")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes")
    is_manual: bool = Field(True, description="Whether entered manually")
    source: Optional[str] = Field("app", description="Source of the data")
    
    @validator('mileage')
    def validate_mileage(cls, v):
        if v < 0:
            raise ValueError("Mileage cannot be negative")
        return v


class MileageUpdate(BaseModel):
    """Schema for updating a mileage record."""
    
    mileage: Optional[int] = Field(None, gt=0, description="Updated mileage")
    location: Optional[str] = Field(None, description="Updated location")
    notes: Optional[str] = Field(None, max_length=500, description="Updated notes")
    is_verified: Optional[bool] = Field(None, description="Verification status")
    is_manual: Optional[bool] = Field(None, description="Whether entered manually")
    
    @validator('mileage')
    def validate_mileage(cls, v):
        if v is not None and v < 0:
            raise ValueError("Mileage cannot be negative")
        return v


class MileageBulkCreate(BaseModel):
    """Schema for bulk creating mileage records."""
    
    records: List[MileageCreate]
    overwrite: bool = Field(False, description="Overwrite existing records")


class MileageValidationRequest(BaseModel):
    """Schema for validating mileage data."""
    
    vehicle_id: str
    mileage: int
    previous_mileage: Optional[int] = None


class MileageAnalyticsRequest(BaseModel):
    """Schema for mileage analytics request."""
    
    vehicle_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    period: Optional[str] = Field("month", description="day, week, month, year")


class MileageAlertRequest(BaseModel):
    """Schema for mileage alert request."""
    
    vehicle_id: str
    current_mileage: int
    service_interval: Optional[int] = 15000  # Default 15,000 KM


# ─── Response Schemas ─────────────────────────────────────────────

class MileageResponse(BaseModel):
    """Schema for mileage record response."""
    
    id: str
    vehicle_id: str
    user_id: str
    mileage: int
    previous_mileage: Optional[int] = None
    date_recorded: datetime
    location: Optional[str] = None
    notes: Optional[str] = None
    is_verified: bool
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    is_manual: bool
    source: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MileageListResponse(BaseModel):
    """Schema for paginated mileage list response."""
    
    items: List[MileageResponse]
    total: int
    page: int
    limit: int
    pages: int
    
    class Config:
        from_attributes = True


class MileageAnalytics(BaseModel):
    """Schema for mileage analytics response."""
    
    vehicle_id: str
    total_mileage: int
    average_mileage: float
    max_mileage: int
    min_mileage: int
    mileage_count: int
    daily_average: float
    weekly_average: float
    monthly_average: float
    yearly_average: float
    first_record_date: Optional[datetime] = None
    last_record_date: Optional[datetime] = None
    mileage_growth_rate: float  # Percentage growth
    service_alerts: List[Dict[str, Any]]
    mileage_by_period: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class MileageValidationResponse(BaseModel):
    """Schema for mileage validation response."""
    
    is_valid: bool
    message: str
    expected_range: Optional[Dict[str, int]] = None
    anomaly_detected: bool
    anomaly_score: Optional[float] = None
    suggestions: List[str] = []


class MileageAlertResponse(BaseModel):
    """Schema for mileage alert response."""
    
    vehicle_id: str
    current_mileage: int
    next_service_mileage: int
    kilometers_to_service: int
    service_due: bool
    alert_level: str  # "ok", "warning", "critical"
    message: str
    estimated_service_date: Optional[str] = None


class MileageSummaryResponse(BaseModel):
    """Schema for mileage summary response."""
    
    vehicle_id: str
    current_mileage: int
    total_distance_traveled: int
    average_daily: float
    average_weekly: float
    average_monthly: float
    total_entries: int
    last_updated: datetime
    year_to_date: int
    month_to_date: int
