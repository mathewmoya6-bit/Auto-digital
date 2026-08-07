"""
Auto-D Kenya
Vehicle Master Schemas
"""

from typing import Optional, List, Any
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
    drive_type: Optional[str] = None
    transmission_type: Optional[str] = None
    body_type: Optional[str] = None


class BasePriceUpdate(BaseModel):
    """Update vehicle base price."""
    crsp_kes: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = "KES"
    year: Optional[int] = Field(None, ge=1900, le=2100)
    effective_date: Optional[date] = None
    source: Optional[str] = None


class VehicleMasterUpdate(BaseModel):
    """Complete vehicle update payload."""
    vehicle: Optional[VehicleUpdate] = None
    specification: Optional[SpecificationUpdate] = None
    pricing: Optional[BasePriceUpdate] = None


# ==========================================================
# SEARCH SCHEMAS
# ==========================================================

class VehicleSearchParams(BaseModel):
    """Search parameters."""
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    fuel: Optional[str] = None
    transmission: Optional[str] = None
    body_type: Optional[str] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


# ==========================================================
# RESPONSE SCHEMAS
# ==========================================================

class VehicleMasterSchema(BaseModel):
    """Complete vehicle master view schema."""
    variant_id: int
    variant_name: Optional[str] = None
    make_name: Optional[str] = None
    model_name: Optional[str] = None
    engine_size_cc: Optional[float] = None
    power_hp: Optional[float] = None
    torque_nm: Optional[float] = None
    fuel_type_name: Optional[str] = None
    transmission_type_name: Optional[str] = None
    body_type_name: Optional[str] = None
    seats: Optional[int] = None
    doors: Optional[int] = None
    crsp_kes: Optional[float] = None
    currency: Optional[str] = None
    is_active: bool = True


class VehicleSearchResult(BaseModel):
    """Search result schema."""
    total: int
    page: int
    per_page: int
    results: List[VehicleMasterSchema]


# ==========================================================
# DASHBOARD SCHEMA
# ==========================================================

class VehicleDashboardSchema(BaseModel):
    """Vehicle database dashboard statistics."""
    total_vehicles: int
    total_makes: int
    total_models: int
    total_generations: int
    total_variants: int
    total_base_prices: int
    active_variants: Optional[int] = 0
    last_updated: Optional[datetime] = None
