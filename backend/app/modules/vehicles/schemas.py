# Auto-D Kenya - Vehicles Schemas
# ================================================================

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field



class VehicleRequest(BaseModel):

    plate: str = Field(
        ...,
        max_length=20
    )

    make_model: Optional[str] = None

    vin: Optional[str] = None

    year: Optional[int] = None

    mileage: int = 0



class VehicleResponse(BaseModel):

    id: str

    plate: str

    make_model: Optional[str] = None

    vin: Optional[str] = None

    year: Optional[int] = None

    mileage: int = 0

    value: float = 0

    verified: bool = False

    created_at: datetime


    class Config:

        from_attributes = True
