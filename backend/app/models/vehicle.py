# backend/app/models/vehicle.py
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

class VehicleMake(BaseModel):
    id: str
    name: str
    country: Optional[str] = None
    founded_year: Optional[int] = None
    logo_url: Optional[str] = None
    created_at: Optional[datetime] = None

class VehicleModel(BaseModel):
    id: str
    make_id: str
    name: str
    body_type: Optional[str] = None
    class_type: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    created_at: Optional[datetime] = None

class VehicleVariant(BaseModel):
    id: str
    model_id: str
    name: str
    year: int
    engine_cc: float
    fuel_type: str
    transmission: str
    drive_type: Optional[str] = None
    fuel_consumption: float  # L/100km
    insurance_group: int
    service_interval: int  # km
    tyre_size: Optional[str] = None
    tyre_cost: float  # KES per tyre
    service_cost: float  # KES per service
    market_value: float  # KES
    depreciation_class: str
    vehicle_class: Optional[str] = None
    created_at: Optional[datetime] = None
