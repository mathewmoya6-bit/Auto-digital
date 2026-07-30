# app/modules/vehicles/models.py
# Auto-D Kenya - Vehicles Models
# ================================================================
# TYPE: MODULE - Vehicles database models

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Vehicle(BaseModel):
    """Vehicle model."""
    id: str
    user_id: str
    plate: str
    make_model: Optional[str] = None
    vin: Optional[str] = None
    year: Optional[int] = None
    mileage: int = 0
    value: float = 0
    verified: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
