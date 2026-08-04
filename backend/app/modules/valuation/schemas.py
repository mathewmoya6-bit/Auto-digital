# app/modules/valuation/schemas.py
# Auto-D Kenya - Valuation Schemas
# ================================================================
# TYPE: MODULE - Vehicle Valuation Pydantic schemas


from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator



# ================================================================
# REQUEST SCHEMA
# ================================================================


class ValuationRequest(BaseModel):
    """
    Vehicle valuation request.
    """

    variant_id: int = Field(
        ...,
        gt=0,
        description="Vehicle variant ID"
    )


    year: Optional[int] = Field(
        default=None,
        ge=1980,
        description="Vehicle manufacturing year"
    )


    mileage: int = Field(
        default=0,
        ge=0,
        description="Current mileage KM"
    )


    location: str = Field(
        default="nairobi",
        description="Vehicle location"
    )


    condition: str = Field(
        default="good",
        description="Vehicle condition"
    )


    ownership_type: Optional[str] = Field(
        default="private",
        description="Private/commercial ownership"
    )


    accident_history: bool = Field(
        default=False,
        description="Previous accident history"
    )


    service_history: bool = Field(
        default=True,
        description="Available service history"
    )


    @field_validator("condition")
    @classmethod
    def validate_condition(
        cls,
        value: str
    ) -> str:

        allowed = {
            "excellent",
            "good",
            "fair",
            "poor"
        }

        value = value.lower()

        if value not in allowed:
            raise ValueError(
                "Invalid vehicle condition"
            )

        return value



    @field_validator("mileage")
    @classmethod
    def validate_mileage(
        cls,
        value: int
    ) -> int:

        if value < 0:
            raise ValueError(
                "Mileage cannot be negative"
            )

        return value



# ================================================================
# VALUATION COMPONENTS
# ================================================================


class VehicleProfile(BaseModel):
    """
    Vehicle information returned in report.
    """

    variant_id: int

    make: str

    model: str

    variant: str

    year: int

    fuel_type: str

    engine_size: Optional[int] = None

    transmission: Optional[str] = None

    body_type: Optional[str] = None



class MarketData(BaseModel):
    """
    Market pricing information.
    """

    base_price: float

    market_low: float

    market_average: float

    market_high: float

    listings_count: int = 0



class ValuationFactors(BaseModel):
    """
    Applied valuation adjustments.
    """

    age_factor: float

    mileage_factor: float

    condition_factor: float

    location_factor: float

    accident_factor: float

    service_factor: float



class PriceRange(BaseModel):

    minimum: float

    maximum: float



# ================================================================
# RESPONSE SCHEMA
# ================================================================


class ValuationResponse(BaseModel):
    """
    Complete vehicle valuation response.
    """


    valuation_id: Optional[str] = None


    vehicle: VehicleProfile


    market_data: MarketData


    factors: ValuationFactors


    estimated_value: float


    price_range: PriceRange


    confidence_score: float = Field(
        default=0,
        ge=0,
        le=100
    )


    currency: str = "KES"


    calculated_at: str



# ================================================================
# REPORT RESPONSE
# ================================================================


class ValuationReportResponse(BaseModel):
    """
    Full valuation report format.
    """

    model_config = ConfigDict(
        from_attributes=True
    )


    report_id: str


    vehicle: VehicleProfile


    valuation: ValuationResponse


    recommendations: List[str] = Field(
        default_factory=list
    )


    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )


    created_at: datetime



# ================================================================
# HISTORY
# ================================================================


class ValuationHistoryItem(BaseModel):

    id: str

    vehicle_name: str

    estimated_value: float

    currency: str = "KES"

    created_at: datetime



class ValuationHistoryResponse(BaseModel):

    valuations: List[
        ValuationHistoryItem
    ] = Field(
        default_factory=list
    )

    total: int = 0
