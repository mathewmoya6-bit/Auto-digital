# app/modules/vehicles/schemas.py
# Auto-D Kenya - Vehicles Schemas
# ================================================================
# TYPE: MODULE - Vehicles Pydantic schemas

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class VehicleRequest(BaseModel):
    plate: str = Field(..., max_length=20)
    make_model: Optional[str] = None
    vin: Optional[str] = None
    year: Optional[int] = None
    mileage: Optional[int] = 0


class VehicleResponse(BaseModel):
    id: str
    plate: str
    make_model: Optional[str]
    vin: Optional[str]
    year: Optional[int]
    mileage: int
    value: float = 0
    verified: bool = False
    created_at: datetime
