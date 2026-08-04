# app/modules/vehicles/schemas.py
# Auto-D Kenya - Vehicle Schemas
# ================================================================
# TYPE: MODULE - Vehicle Pydantic schemas


from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator



# ================================================================
# REQUEST
# ================================================================


class VehicleRequest(BaseModel):
    """
    Vehicle creation/update request.
    """

    plate: str = Field(
        ...,
        max_length=20,
        description="Vehicle registration number"
    )


    make_model: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Vehicle make and model"
    )


    vin: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Vehicle VIN/chassis number"
    )


    year: Optional[int] = Field(
        default=None,
        ge=1980,
        description="Manufacturing year"
    )


    mileage: int = Field(
        default=0,
        ge=0,
        description="Current mileage KM"
    )


    @field_validator("plate")
    @classmethod
    def validate_plate(cls, value: str) -> str:
        """
        Normalize vehicle registration.
        """

        value = value.strip().upper()

        if len(value) < 3:
            raise ValueError(
                "Invalid vehicle plate number"
            )

        return value



    @field_validator("mileage")
    @classmethod
    def validate_mileage(cls, value: int) -> int:

        if value < 0:
            raise ValueError(
                "Mileage cannot be negative"
            )

        return value



# ================================================================
# RESPONSE
# ================================================================


class VehicleResponse(BaseModel):
    """
    Vehicle response.
    """

    model_config = ConfigDict(
        from_attributes=True
    )


    id: str

    plate: str


    make_model: Optional[str] = None

    vin: Optional[str] = None


    year: Optional[int] = None


    mileage: int = 0


    value: float = 0.0


    verified: bool = False


    created_at: datetime
