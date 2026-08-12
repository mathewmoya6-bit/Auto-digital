```python
# ================================================================
# Auto-D Kenya - Vehicle Schemas
# ================================================================
# CRSP-driven vehicle catalogue schemas.
#
# Source of truth:
#     public.vehicle_crsp_lookup
#
# Authoritative vehicle identifier:
#     crsp_id
#
# Confirmed database columns:
#
# crsp_id
# make_id
# make
# model_id
# model
# trim_level
# manufacture_year
# crsp_year
# body_type
# seating_capacity
# engine_capacity
# engine_capacity_cc
# fuel
# transmission
# drive_config
# crsp_kes
# currency
# horsepower
# vehicle_power_type
# battery_capacity_kwh
# powertrain_classification
# crsp_status
# ================================================================

from datetime import datetime
from typing import Optional, List, Dict

from pydantic import BaseModel, Field, ConfigDict


# ================================================================
# CRSP VEHICLE RESPONSE
# ================================================================

class CRSPVehicleResponse(BaseModel):
    """Complete vehicle_crsp_lookup record."""

    model_config = ConfigDict(from_attributes=True)

    crsp_id: int

    make_id: Optional[int] = None
    make: Optional[str] = None

    model_id: Optional[int] = None
    model: Optional[str] = None

    trim_level: Optional[str] = None

    manufacture_year: Optional[int] = None
    crsp_year: Optional[int] = None

    body_type: Optional[str] = None
    seating_capacity: Optional[int] = None

    engine_capacity: Optional[str] = None
    engine_capacity_cc: Optional[float] = None

    fuel: Optional[str] = None
    transmission: Optional[str] = None
    drive_config: Optional[str] = None

    crsp_kes: Optional[float] = None
    currency: Optional[str] = "KES"

    horsepower: Optional[float] = None
    vehicle_power_type: Optional[str] = None
    battery_capacity_kwh: Optional[float] = None
    powertrain_classification: Optional[str] = None

    crsp_status: Optional[str] = None


# ================================================================
# VEHICLE LIST RESPONSE
# ================================================================

class VehicleListResponse(BaseModel):
    """Lightweight CRSP vehicle response."""

    model_config = ConfigDict(from_attributes=True)

    crsp_id: int

    make_id: Optional[int] = None
    make: Optional[str] = None

    model_id: Optional[int] = None
    model: Optional[str] = None

    trim_level: Optional[str] = None

    manufacture_year: Optional[int] = None
    crsp_year: Optional[int] = None

    body_type: Optional[str] = None
    seating_capacity: Optional[int] = None

    engine_capacity: Optional[str] = None
    engine_capacity_cc: Optional[float] = None

    fuel: Optional[str] = None
    transmission: Optional[str] = None
    drive_config: Optional[str] = None

    crsp_kes: Optional[float] = None
    currency: Optional[str] = "KES"

    horsepower: Optional[float] = None
    vehicle_power_type: Optional[str] = None
    battery_capacity_kwh: Optional[float] = None
    powertrain_classification: Optional[str] = None

    crsp_status: Optional[str] = None


# ================================================================
# VEHICLE SEARCH RESPONSE
# ================================================================

class VehicleSearchResponse(BaseModel):
    """CRSP vehicle search result."""

    model_config = ConfigDict(from_attributes=True)

    crsp_id: int

    make_id: Optional[int] = None
    make: Optional[str] = None

    model_id: Optional[int] = None
    model: Optional[str] = None

    trim_level: Optional[str] = None

    manufacture_year: Optional[int] = None
    crsp_year: Optional[int] = None

    body_type: Optional[str] = None
    seating_capacity: Optional[int] = None

    engine_capacity: Optional[str] = None
    engine_capacity_cc: Optional[float] = None

    fuel: Optional[str] = None
    transmission: Optional[str] = None
    drive_config: Optional[str] = None

    crsp_kes: Optional[float] = None
    currency: Optional[str] = "KES"

    horsepower: Optional[float] = None
    vehicle_power_type: Optional[str] = None
    battery_capacity_kwh: Optional[float] = None
    powertrain_classification: Optional[str] = None

    crsp_status: Optional[str] = None

    similarity_score: Optional[float] = None


# ================================================================
# VEHICLE MASTER RESPONSE
# ================================================================

class VehicleMasterResponse(BaseModel):
    """
    Complete CRSP vehicle response.

    CRSP is the authoritative vehicle identity.
    """

    model_config = ConfigDict(from_attributes=True)

    crsp_id: int

    make_id: Optional[int] = None
    make: Optional[str] = None

    model_id: Optional[int] = None
    model: Optional[str] = None

    trim_level: Optional[str] = None

    manufacture_year: Optional[int] = None
    crsp_year: Optional[int] = None

    body_type: Optional[str] = None
    seating_capacity: Optional[int] = None

    engine_capacity: Optional[str] = None
    engine_capacity_cc: Optional[float] = None

    fuel: Optional[str] = None
    transmission: Optional[str] = None
    drive_config: Optional[str] = None

    crsp_kes: Optional[float] = None
    currency: Optional[str] = "KES"

    horsepower: Optional[float] = None
    vehicle_power_type: Optional[str] = None
    battery_capacity_kwh: Optional[float] = None
    powertrain_classification: Optional[str] = None

    crsp_status: Optional[str] = None

    # ------------------------------------------------------------
    # Calculated fields
    # ------------------------------------------------------------

    estimated_value: Optional[float] = None
    market_value: Optional[float] = None
    depreciation_value: Optional[float] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ================================================================
# CATEGORY RESPONSE
# ================================================================

class CategoryResponse(BaseModel):
    """Application vehicle category."""

    id: int
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    vehicle_count: int = 0


# ================================================================
# MAKE RESPONSE
# ================================================================

class MakeResponse(BaseModel):
    """Unique vehicle make derived from CRSP."""

    id: Optional[int] = None
    name: str

    country: Optional[str] = None
    logo_url: Optional[str] = None

    vehicle_count: int = 0

    category_id: Optional[int] = None


# ================================================================
# MODEL RESPONSE
# ================================================================

class ModelResponse(BaseModel):
    """Unique vehicle model derived from CRSP."""

    id: Optional[int] = None
    name: str

    make_id: Optional[int] = None
    make_name: Optional[str] = None

    vehicle_count: int = 0

    body_type: Optional[str] = None

    start_year: Optional[int] = None
    end_year: Optional[int] = None


# ================================================================
# ENGINE CAPACITY RESPONSE
# ================================================================

class EngineCapacityResponse(BaseModel):
    """Engine information derived from CRSP."""

    id: Optional[int] = None

    engine_capacity: Optional[str] = None
    engine_capacity_cc: Optional[float] = None

    engine_code: Optional[str] = None

    fuel_type: Optional[str] = None

    vehicle_count: int = 0


# ================================================================
# GENERATION RESPONSE
# ================================================================
# Legacy compatibility only.
#
# CRSP no longer uses generation as the authoritative vehicle key.

class GenerationResponse(BaseModel):
    """Legacy generation response."""

    id: Optional[int] = None
    code: Optional[str] = None

    start_year: Optional[int] = None
    end_year: Optional[int] = None

    model_id: Optional[int] = None
    model_name: Optional[str] = None

    variant_count: int = 0


# ================================================================
# VARIANT RESPONSE
# ================================================================
# Legacy compatibility only.
#
# crsp_id remains authoritative.

class VariantResponse(BaseModel):
    """Legacy-compatible CRSP variant response."""

    crsp_id: int

    variant_id: Optional[int] = None
    variant_name: Optional[str] = None

    trim_level: Optional[str] = None

    engine_size_cc: Optional[float] = None
    engine_code: Optional[str] = None

    fuel_type_name: Optional[str] = None
    transmission_type_name: Optional[str] = None
    body_type_name: Optional[str] = None

    make_name: Optional[str] = None
    model_name: Optional[str] = None

    generation_id: Optional[int] = None

    crsp_kes: Optional[float] = None

    estimated_value: Optional[float] = None
    market_value: Optional[float] = None
    base_price: Optional[float] = None
    dealer_price: Optional[float] = None


# ================================================================
# BASE PRICE RESPONSE
# ================================================================

class BasePriceResponse(BaseModel):
    """CRSP reference price."""

    crsp_id: int

    make: Optional[str] = None
    model: Optional[str] = None

    engine_capacity: Optional[str] = None
    engine_capacity_cc: Optional[float] = None

    crsp_fuel: Optional[str] = None
    transmission: Optional[str] = None

    base_price: float = 0.0
    crsp_price: Optional[float] = None

    currency: str = "KES"
    source: str = "CRSP"

    last_updated: Optional[datetime] = None

    year: Optional[int] = None


# ================================================================
# VEHICLE STATISTICS
# ================================================================

class VehicleStatisticsResponse(BaseModel):
    """CRSP catalogue statistics."""

    total_vehicles: int = 0
    total_makes: int = 0
    total_models: int = 0

    total_engine_capacities: int = 0
    total_fuel_types: int = 0
    total_transmissions: int = 0

    makes_by_category: Dict[str, int] = Field(
        default_factory=dict
    )

    vehicles_by_year: Dict[str, int] = Field(
        default_factory=dict
    )

    vehicles_by_fuel_type: Dict[str, int] = Field(
        default_factory=dict
    )

    vehicles_by_transmission: Dict[str, int] = Field(
        default_factory=dict
    )

    vehicles_by_engine_capacity: Dict[str, int] = Field(
        default_factory=dict
    )

    average_crsp_price: float = 0.0
    min_crsp_price: float = 0.0
    max_crsp_price: float = 0.0

    average_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0

    last_updated: Optional[datetime] = None


# ================================================================
# VEHICLE HEALTH
# ================================================================

class VehicleHealthResponse(BaseModel):
    """Vehicle catalogue health."""

    status: str

    service: str = "vehicles"
    version: str = "2.0"

    timestamp: str

    database: Optional[str] = None

    crsp_records: Optional[int] = None

    error: Optional[str] = None


# ================================================================
# VEHICLE SEARCH PARAMETERS
# ================================================================

class VehicleSearchParams(BaseModel):
    """Search/filter parameters for CRSP vehicles."""

    make: Optional[str] = None
    model: Optional[str] = None

    make_id: Optional[int] = None
    model_id: Optional[int] = None

    fuel: Optional[str] = None
    transmission: Optional[str] = None

    engine_capacity_cc: Optional[float] = None
    engine_code: Optional[str] = None

    min_price: Optional[float] = None
    max_price: Optional[float] = None

    year: Optional[int] = None

    search: Optional[str] = None

    limit: int = Field(
        default=50,
        ge=1,
        le=500,
    )

    offset: int = Field(
        default=0,
        ge=0,
    )


# ================================================================
# CRSP SUMMARY
# ================================================================

class CRSPSummaryResponse(BaseModel):
    """CRSP database summary."""

    total_records: int = 0
    total_makes: int = 0
    total_models: int = 0

    total_engine_capacities: int = 0

    missing_make: int = 0
    missing_model: int = 0
    missing_crsp: int = 0
    missing_fuel: int = 0
    missing_transmission: int = 0
    missing_engine: int = 0


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    "CRSPVehicleResponse",
    "VehicleListResponse",
    "VehicleSearchResponse",
    "VehicleMasterResponse",
    "CategoryResponse",
    "MakeResponse",
    "ModelResponse",
    "EngineCapacityResponse",
    "GenerationResponse",
    "VariantResponse",
    "BasePriceResponse",
    "VehicleStatisticsResponse",
    "VehicleHealthResponse",
    "VehicleSearchParams",
    "CRSPSummaryResponse",
]
```
