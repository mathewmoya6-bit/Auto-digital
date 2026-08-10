# app/modules/vehicles/schemas.py

# ================================================================
# Auto-D Kenya - Vehicle Schemas
# ================================================================
# TYPE: MODULE - CRSP-driven vehicle management Pydantic schemas
# Compatible with Pydantic v2
#
# Architecture:
#
# vehicle_base_prices
#        ↓
#      CRSP
#        ↓
# make / model / engine / fuel / transmission
#        ↓
# valuation / running cost / ownership / reports
#
# vehicle_base_prices is the CRSP source of truth.
# ================================================================

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


# ================================================================
# CRSP VEHICLE SCHEMA
# ================================================================

class CRSPVehicleResponse(BaseModel):
    """
    Complete CRSP vehicle record.

    This represents one row from vehicle_base_prices and is the
    primary vehicle response used throughout Auto-D Kenya.
    """

    model_config = ConfigDict(from_attributes=True)

    crsp_id: int = Field(
        ...,
        description="CRSP vehicle record ID"
    )

    make: str = Field(
        ...,
        description="Vehicle make"
    )

    model: str = Field(
        ...,
        description="Vehicle model"
    )

    crsp_fuel: Optional[str] = Field(
        None,
        description="Fuel type recorded by CRSP"
    )

    engine_capacity_id: Optional[int] = Field(
        None,
        description="Engine capacity reference ID"
    )

    engine_capacity: Optional[str] = Field(
        None,
        description="Engine capacity description"
    )

    engine_code: Optional[str] = Field(
        None,
        description="Engine code"
    )

    engine_capacity_cc: Optional[int] = Field(
        None,
        description="Engine capacity in CC"
    )

    capacity_fuel: Optional[str] = Field(
        None,
        description="Fuel type associated with engine capacity"
    )

    transmission: Optional[str] = Field(
        None,
        description="Transmission type"
    )

    crsp_price: Optional[float] = Field(
        None,
        description="CRSP value in KES"
    )

    year: Optional[int] = Field(
        None,
        description="Vehicle year"
    )

    created_at: Optional[datetime] = Field(
        None,
        description="Record creation timestamp"
    )

    updated_at: Optional[datetime] = Field(
        None,
        description="Record update timestamp"
    )


# ================================================================
# VEHICLE LIST RESPONSE
# ================================================================

class VehicleListResponse(BaseModel):
    """
    Lightweight vehicle response for vehicle lists.
    """

    model_config = ConfigDict(from_attributes=True)

    crsp_id: int = Field(
        ...,
        description="CRSP vehicle ID"
    )

    make: str = Field(
        ...,
        description="Vehicle make"
    )

    model: str = Field(
        ...,
        description="Vehicle model"
    )

    crsp_fuel: Optional[str] = Field(
        None,
        description="CRSP fuel type"
    )

    engine_capacity_cc: Optional[int] = Field(
        None,
        description="Engine capacity in CC"
    )

    engine_code: Optional[str] = Field(
        None,
        description="Engine code"
    )

    transmission: Optional[str] = Field(
        None,
        description="Transmission"
    )

    crsp_price: Optional[float] = Field(
        None,
        description="CRSP price in KES"
    )


# ================================================================
# VEHICLE SEARCH RESPONSE
# ================================================================

class VehicleSearchResponse(BaseModel):
    """
    Vehicle search result based directly on CRSP records.
    """

    model_config = ConfigDict(from_attributes=True)

    crsp_id: int = Field(
        ...,
        description="CRSP vehicle ID"
    )

    make: str = Field(
        ...,
        description="Vehicle make"
    )

    model: str = Field(
        ...,
        description="Vehicle model"
    )

    crsp_fuel: Optional[str] = Field(
        None,
        description="CRSP fuel type"
    )

    engine_capacity: Optional[str] = Field(
        None,
        description="Engine capacity"
    )

    engine_capacity_cc: Optional[int] = Field(
        None,
        description="Engine capacity in CC"
    )

    engine_code: Optional[str] = Field(
        None,
        description="Engine code"
    )

    transmission: Optional[str] = Field(
        None,
        description="Transmission"
    )

    crsp_price: Optional[float] = Field(
        None,
        description="CRSP price in KES"
    )

    similarity_score: Optional[float] = Field(
        None,
        description="Search similarity score"
    )


# ================================================================
# VEHICLE MASTER RESPONSE
# ================================================================

class VehicleMasterResponse(BaseModel):
    """
    Complete vehicle master response.

    CRSP is the master vehicle identity.
    """

    model_config = ConfigDict(from_attributes=True)

    crsp_id: int = Field(
        ...,
        description="CRSP vehicle ID"
    )

    make: Optional[str] = Field(
        None,
        description="Vehicle make"
    )

    model: Optional[str] = Field(
        None,
        description="Vehicle model"
    )

    crsp_fuel: Optional[str] = Field(
        None,
        description="CRSP fuel type"
    )

    engine_capacity_id: Optional[int] = Field(
        None,
        description="Engine capacity ID"
    )

    engine_capacity: Optional[str] = Field(
        None,
        description="Engine capacity description"
    )

    engine_code: Optional[str] = Field(
        None,
        description="Engine code"
    )

    engine_capacity_cc: Optional[int] = Field(
        None,
        description="Engine capacity in CC"
    )

    capacity_fuel: Optional[str] = Field(
        None,
        description="Engine capacity fuel"
    )

    transmission: Optional[str] = Field(
        None,
        description="Transmission type"
    )

    crsp_price: Optional[float] = Field(
        None,
        description="CRSP price in KES"
    )

    # ------------------------------------------------------------
    # Calculated / intelligence fields
    # ------------------------------------------------------------

    estimated_value: Optional[float] = Field(
        None,
        description="Calculated estimated vehicle value"
    )

    market_value: Optional[float] = Field(
        None,
        description="Current market value"
    )

    depreciation_value: Optional[float] = Field(
        None,
        description="Calculated depreciation value"
    )

    created_at: Optional[datetime] = Field(
        None,
        description="Created at"
    )

    updated_at: Optional[datetime] = Field(
        None,
        description="Updated at"
    )


# ================================================================
# CATEGORY RESPONSE
# ================================================================

class CategoryResponse(BaseModel):
    """
    Vehicle category response.

    Category is an application-level classification and is not
    treated as the CRSP vehicle identity.
    """

    id: int = Field(
        ...,
        description="Category ID"
    )

    name: str = Field(
        ...,
        description="Category name"
    )

    description: Optional[str] = Field(
        None,
        description="Category description"
    )

    icon: Optional[str] = Field(
        None,
        description="Category icon"
    )

    vehicle_count: int = Field(
        0,
        description="Number of vehicles"
    )


# ================================================================
# MAKE RESPONSE
# ================================================================

class MakeResponse(BaseModel):
    """
    Make aggregation generated from CRSP data.
    """

    id: Optional[int] = Field(
        None,
        description="Make ID where available"
    )

    name: str = Field(
        ...,
        description="Vehicle make"
    )

    country: Optional[str] = Field(
        None,
        description="Country of origin"
    )

    logo_url: Optional[str] = Field(
        None,
        description="Make logo URL"
    )

    vehicle_count: int = Field(
        0,
        description="Number of CRSP vehicles"
    )

    category_id: Optional[int] = Field(
        None,
        description="Application category ID"
    )


# ================================================================
# MODEL RESPONSE
# ================================================================

class ModelResponse(BaseModel):
    """
    Model aggregation generated from CRSP data.
    """

    id: Optional[int] = Field(
        None,
        description="Model ID where available"
    )

    name: str = Field(
        ...,
        description="Vehicle model"
    )

    make_id: Optional[int] = Field(
        None,
        description="Make ID where available"
    )

    make_name: str = Field(
        ...,
        description="Vehicle make"
    )

    vehicle_count: int = Field(
        0,
        description="Number of CRSP records"
    )

    # Kept optional for compatibility with older API consumers.
    body_type: Optional[str] = Field(
        None,
        description="Body type where available"
    )

    start_year: Optional[int] = Field(
        None,
        description="Production start year where available"
    )

    end_year: Optional[int] = Field(
        None,
        description="Production end year where available"
    )


# ================================================================
# ENGINE CAPACITY RESPONSE
# ================================================================

class EngineCapacityResponse(BaseModel):
    """
    Engine capacity information linked to CRSP.
    """

    id: Optional[int] = Field(
        None,
        description="Engine capacity ID"
    )

    engine_capacity: Optional[str] = Field(
        None,
        description="Engine capacity description"
    )

    engine_capacity_cc: Optional[int] = Field(
        None,
        description="Engine capacity in CC"
    )

    engine_code: Optional[str] = Field(
        None,
        description="Engine code"
    )

    fuel_type: Optional[str] = Field(
        None,
        description="Fuel type"
    )

    vehicle_count: int = Field(
        0,
        description="Number of CRSP vehicles"
    )


# ================================================================
# GENERATION RESPONSE
# ================================================================
# Kept only for backward API compatibility.
# Generation is no longer the CRSP master identity.

class GenerationResponse(BaseModel):
    """
    Legacy-compatible generation response.

    Generation information is optional because the new CRSP
    database does not depend on generation as the master key.
    """

    id: Optional[int] = Field(
        None,
        description="Generation ID"
    )

    code: Optional[str] = Field(
        None,
        description="Generation code"
    )

    start_year: Optional[int] = Field(
        None,
        description="Start year"
    )

    end_year: Optional[int] = Field(
        None,
        description="End year"
    )

    model_id: Optional[int] = Field(
        None,
        description="Model ID"
    )

    model_name: Optional[str] = Field(
        None,
        description="Model name"
    )

    variant_count: int = Field(
        0,
        description="Number of variants"
    )


# ================================================================
# VARIANT RESPONSE
# ================================================================
# Compatibility layer only.
#
# New CRSP architecture should use crsp_id instead of variant_id.

class VariantResponse(BaseModel):
    """
    CRSP-compatible vehicle variant response.

    variant_id is retained as an alias-compatible field for older
    endpoints, but crsp_id is the authoritative identifier.
    """

    crsp_id: int = Field(
        ...,
        description="Authoritative CRSP vehicle ID"
    )

    variant_id: Optional[int] = Field(
        None,
        description="Legacy variant ID"
    )

    variant_name: Optional[str] = Field(
        None,
        description="Vehicle variant description"
    )

    trim_level: Optional[str] = Field(
        None,
        description="Trim level"
    )

    engine_size_cc: Optional[int] = Field(
        None,
        description="Engine size in CC"
    )

    engine_code: Optional[str] = Field(
        None,
        description="Engine code"
    )

    fuel_type_name: Optional[str] = Field(
        None,
        description="Fuel type"
    )

    transmission_type_name: Optional[str] = Field(
        None,
        description="Transmission type"
    )

    body_type_name: Optional[str] = Field(
        None,
        description="Body type"
    )

    make_name: Optional[str] = Field(
        None,
        description="Make"
    )

    model_name: Optional[str] = Field(
        None,
        description="Model"
    )

    generation_id: Optional[int] = Field(
        None,
        description="Legacy generation ID"
    )

    # CRSP
    crsp_kes: Optional[float] = Field(
        None,
        description="CRSP value in KES"
    )

    # Calculated prices
    estimated_value: Optional[float] = Field(
        None,
        description="Estimated value"
    )

    market_value: Optional[float] = Field(
        None,
        description="Market value"
    )

    base_price: Optional[float] = Field(
        None,
        description="Base price"
    )

    dealer_price: Optional[float] = Field(
        None,
        description="Dealer price"
    )


# ================================================================
# BASE PRICE RESPONSE
# ================================================================

class BasePriceResponse(BaseModel):
    """
    CRSP base price response.

    CRSP price is the authoritative reference price.
    """

    crsp_id: int = Field(
        ...,
        description="CRSP vehicle ID"
    )

    make: str = Field(
        ...,
        description="Vehicle make"
    )

    model: str = Field(
        ...,
        description="Vehicle model"
    )

    engine_capacity: Optional[str] = Field(
        None,
        description="Engine capacity"
    )

    engine_capacity_cc: Optional[int] = Field(
        None,
        description="Engine capacity in CC"
    )

    engine_code: Optional[str] = Field(
        None,
        description="Engine code"
    )

    crsp_fuel: Optional[str] = Field(
        None,
        description="CRSP fuel type"
    )

    transmission: Optional[str] = Field(
        None,
        description="Transmission"
    )

    base_price: float = Field(
        ...,
        description="CRSP base price in KES"
    )

    crsp_price: Optional[float] = Field(
        None,
        description="CRSP price in KES"
    )

    currency: str = Field(
        "KES",
        description="Currency code"
    )

    source: str = Field(
        "CRSP",
        description="Price source"
    )

    last_updated: Optional[datetime] = Field(
        None,
        description="Last updated"
    )

    year: Optional[int] = Field(
        None,
        description="Vehicle year"
    )


# ================================================================
# VEHICLE STATISTICS
# ================================================================

class VehicleStatisticsResponse(BaseModel):
    """
    Vehicle statistics derived from CRSP records.
    """

    total_vehicles: int = Field(
        0,
        description="Total CRSP vehicle records"
    )

    total_makes: int = Field(
        0,
        description="Total unique makes"
    )

    total_models: int = Field(
        0,
        description="Total unique models"
    )

    total_engine_capacities: int = Field(
        0,
        description="Total engine capacity records"
    )

    total_fuel_types: int = Field(
        0,
        description="Total fuel types"
    )

    total_transmissions: int = Field(
        0,
        description="Total transmission types"
    )

    makes_by_category: Dict[str, int] = Field(
        default_factory=dict,
        description="Makes by category"
    )

    vehicles_by_year: Dict[str, int] = Field(
        default_factory=dict,
        description="Vehicles by year"
    )

    vehicles_by_fuel_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Vehicles by fuel type"
    )

    vehicles_by_transmission: Dict[str, int] = Field(
        default_factory=dict,
        description="Vehicles by transmission"
    )

    vehicles_by_engine_capacity: Dict[str, int] = Field(
        default_factory=dict,
        description="Vehicles by engine capacity"
    )

    average_crsp_price: float = Field(
        0,
        description="Average CRSP price"
    )

    min_crsp_price: float = Field(
        0,
        description="Minimum CRSP price"
    )

    max_crsp_price: float = Field(
        0,
        description="Maximum CRSP price"
    )

    average_price: float = Field(
        0,
        description="Average vehicle price"
    )

    min_price: float = Field(
        0,
        description="Minimum vehicle price"
    )

    max_price: float = Field(
        0,
        description="Maximum vehicle price"
    )

    last_updated: Optional[datetime] = Field(
        None,
        description="Last update timestamp"
    )


# ================================================================
# VEHICLE HEALTH
# ================================================================

class VehicleHealthResponse(BaseModel):
    """
    Vehicle service health response.
    """

    status: str = Field(
        ...,
        description="Service health status"
    )

    service: str = Field(
        "vehicles",
        description="Service name"
    )

    version: str = Field(
        "2.0",
        description="Service version"
    )

    timestamp: str = Field(
        ...,
        description="Health check timestamp"
    )

    database: Optional[str] = Field(
        None,
        description="Database health status"
    )

    crsp_records: Optional[int] = Field(
        None,
        description="Number of CRSP records"
    )

    error: Optional[str] = Field(
        None,
        description="Error message if any"
    )


# ================================================================
# VEHICLE FILTER / SEARCH PARAMETERS
# ================================================================

class VehicleSearchParams(BaseModel):
    """
    Search parameters for CRSP vehicles.

    This class is intentionally included because the vehicle
    repository/service previously expected VehicleSearchParams.
    """

    make: Optional[str] = Field(
        None,
        description="Filter by make"
    )

    model: Optional[str] = Field(
        None,
        description="Filter by model"
    )

    fuel: Optional[str] = Field(
        None,
        description="Filter by fuel type"
    )

    transmission: Optional[str] = Field(
        None,
        description="Filter by transmission"
    )

    engine_capacity_cc: Optional[int] = Field(
        None,
        description="Filter by engine capacity"
    )

    engine_code: Optional[str] = Field(
        None,
        description="Filter by engine code"
    )

    min_price: Optional[float] = Field(
        None,
        description="Minimum CRSP price"
    )

    max_price: Optional[float] = Field(
        None,
        description="Maximum CRSP price"
    )

    year: Optional[int] = Field(
        None,
        description="Vehicle year"
    )

    search: Optional[str] = Field(
        None,
        description="General vehicle search"
    )

    limit: int = Field(
        50,
        ge=1,
        le=500,
        description="Maximum records"
    )

    offset: int = Field(
        0,
        ge=0,
        description="Pagination offset"
    )


# ================================================================
# CRSP SUMMARY
# ================================================================

class CRSPSummaryResponse(BaseModel):
    """
    CRSP database summary.
    """

    total_records: int = Field(
        0,
        description="Total CRSP records"
    )

    total_makes: int = Field(
        0,
        description="Unique makes"
    )

    total_models: int = Field(
        0,
        description="Unique models"
    )

    total_engine_capacities: int = Field(
        0,
        description="Engine capacity records"
    )

    missing_make: int = Field(
        0,
        description="Records missing make"
    )

    missing_model: int = Field(
        0,
        description="Records missing model"
    )

    missing_crsp: int = Field(
        0,
        description="Records missing CRSP value"
    )

    missing_fuel: int = Field(
        0,
        description="Records missing fuel"
    )

    missing_transmission: int = Field(
        0,
        description="Records missing transmission"
    )

    missing_engine: int = Field(
        0,
        description="Records missing engine information"
    )


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
