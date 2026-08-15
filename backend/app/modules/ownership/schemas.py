"""
Auto-D Kenya
Ownership / TCO API Schemas

Production request and response models.

Important:
- vehicle_crsp_id is the authoritative vehicle identifier.
- No user_vehicles dependency.
- Numeric inputs are normalized by Pydantic before reaching the engine.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator


class OwnershipCostRequest(BaseModel):
    """
    Production request for vehicle ownership / running-cost calculation.
    """

    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
    )

    vehicle_crsp_id: int = Field(
        ...,
        gt=0,
        description="Authoritative vehicle_crsp.crsp_id",
    )

    distance: float = Field(
        default=150,
        gt=0,
        description="Trip distance in kilometres",
    )

    annual_mileage: float = Field(
        default=20000,
        gt=0,
        description="Expected annual mileage in kilometres",
    )

    fuel_price: Optional[float] = Field(
        default=None,
        ge=0,
        description="Optional fuel price in KES/litre",
    )

    trip_type: str = Field(
        default="mixed",
        description="urban, highway, mixed or offroad",
    )

    driving_style: str = Field(
        default="normal",
        description="eco, normal or aggressive",
    )

    include_insurance: bool = True
    include_maintenance: bool = True
    include_tyres: bool = True
    include_depreciation: bool = True

    @field_validator("vehicle_crsp_id", mode="before")
    @classmethod
    def validate_vehicle_crsp_id(cls, value: Any) -> int:
        if value is None or value == "":
            raise ValueError("vehicle_crsp_id is required")

        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError("vehicle_crsp_id must be an integer")

        if value <= 0:
            raise ValueError("vehicle_crsp_id must be greater than zero")

        return value

    @field_validator(
        "distance",
        "annual_mileage",
        "fuel_price",
        mode="before",
    )
    @classmethod
    def normalize_numeric(cls, value: Any) -> Optional[float]:
        """
        Prevent the production error:

        unsupported operand type(s) for /: 'str' and 'int'
        """

        if value is None or value == "":
            return None

        if isinstance(value, str):
            value = value.replace(",", "").strip()

        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid numeric value: {value}")

    @field_validator("distance")
    @classmethod
    def validate_distance(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("distance must be greater than zero")
        return value

    @field_validator("annual_mileage")
    @classmethod
    def validate_annual_mileage(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("annual_mileage must be greater than zero")
        return value

    @field_validator("fuel_price")
    @classmethod
    def validate_fuel_price(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise ValueError("fuel_price cannot be negative")
        return value

    @field_validator("trip_type", "driving_style")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.lower().strip()


class OwnershipCostResponse(BaseModel):
    """
    Flexible production response.

    The database calculation function returns JSONB and may evolve
    without requiring a breaking response-schema deployment.
    """

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
