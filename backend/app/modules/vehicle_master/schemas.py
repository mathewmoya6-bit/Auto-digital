"""
Auto-D Kenya
Vehicle Master Schemas
"""

from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, Field


# ==========================================================
# UPDATE SCHEMAS
# ==========================================================

class VehicleUpdate(BaseModel):
    """Update vehicle variant."""
    name: Optional[str] = None
    trim_level: Optional[str] = None
    generation_id: Optional[int] = None
    is_active: Optional[bool] = None


class SpecificationUpdate(BaseModel):
    """Update vehicle specifications."""
    engine_cc: Optional[float] = Field(None, gt=0)
    power_hp: Optional[float] = Field(None, ge=0)
    torque_nm: Optional[float] = Field(None, ge=0)
    fuel_consumption_combined: Optional[float] = Field(None, ge=0)
    seats: Optional[int] = Field(None, ge=1, le=20)
    doors: Optional[int] = Field(None, ge=1, le=6)


class BasePriceUpdate(BaseModel):
    """Update vehicle base price."""
    crsp_kes: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = "KES"
    effective_date: Optional[date] = None


class VehicleMasterUpdate(BaseModel):
    """Complete vehicle update payload."""
    vehicle: Optional[VehicleUpdate] = None
    specification: Optional[SpecificationUpdate] = None
    pricing: Optional[BasePriceUpdate] = None
