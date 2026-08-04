# Auto-D Kenya - Mileage Schemas
# ================================================================
# TYPE: MODULE - Mileage Pydantic schemas

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator


# ================================================================
# REQUEST SCHEMAS
# ================================================================


class MileageCreate(BaseModel):
    """
    Create mileage record.
    """

    vehicle_id: str = Field(
        ...,
        description="Vehicle ID"
    )

    mileage: int = Field(
        ...,
        gt=0,
        description="Current mileage KM"
    )

    location: Optional[str] = None

    notes: Optional[str] = Field(
        None,
        max_length=500
    )

    is_manual: bool = True

    source: Optional[str] = "app"


    @field_validator("mileage")
    @classmethod
    def validate_mileage(cls, value):

        if value < 0:
            raise ValueError(
                "Mileage cannot be negative"
            )

        return value



class MileageUpdate(BaseModel):
    """
    Update mileage record.
    """

    mileage: Optional[int] = Field(
        None,
        gt=0
    )

    location: Optional[str] = None

    notes: Optional[str] = Field(
        None,
        max_length=500
    )

    is_verified: Optional[bool] = None

    is_manual: Optional[bool] = None


    @field_validator("mileage")
    @classmethod
    def validate_mileage(cls, value):

        if value is not None and value < 0:

            raise ValueError(
                "Mileage cannot be negative"
            )

        return value



class MileageBulkCreate(BaseModel):

    records: List[MileageCreate]

    overwrite: bool = False



class MileageValidationRequest(BaseModel):

    vehicle_id: str

    mileage: int

    previous_mileage: Optional[int] = None



class MileageAnalyticsRequest(BaseModel):

    vehicle_id: str

    start_date: Optional[datetime] = None

    end_date: Optional[datetime] = None

    period: str = "month"



class MileageAlertRequest(BaseModel):

    vehicle_id: str

    current_mileage: int

    service_interval: int = 15000



# ================================================================
# RESPONSE SCHEMAS
# ================================================================


class MileageResponse(BaseModel):

    id: str

    vehicle_id: str

    user_id: str

    mileage: int

    previous_mileage: Optional[int] = None

    date_recorded: datetime

    location: Optional[str] = None

    notes: Optional[str] = None

    is_verified: bool = False

    verified_by: Optional[str] = None

    verified_at: Optional[datetime] = None

    is_manual: bool = True

    source: Optional[str] = None

    created_at: datetime

    updated_at: datetime


    class Config:

        from_attributes = True



class MileageListResponse(BaseModel):

    items: List[MileageResponse]

    total: int

    page: int

    limit: int

    pages: int


    class Config:

        from_attributes = True



class MileageAnalytics(BaseModel):

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

    mileage_growth_rate: float = 0

    service_alerts: List[Dict[str, Any]] = Field(
        default_factory=list
    )

    mileage_by_period: List[Dict[str, Any]] = Field(
        default_factory=list
    )


    class Config:

        from_attributes = True



class MileageValidationResponse(BaseModel):

    is_valid: bool

    message: str

    expected_range: Optional[
        Dict[str, int]
    ] = None

    anomaly_detected: bool = False

    anomaly_score: Optional[float] = None

    suggestions: List[str] = Field(
        default_factory=list
    )



class MileageAlertResponse(BaseModel):

    vehicle_id: str

    current_mileage: int

    next_service_mileage: int

    kilometers_to_service: int

    service_due: bool

    alert_level: str

    message: str

    estimated_service_date: Optional[str] = None



class MileageSummaryResponse(BaseModel):

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
