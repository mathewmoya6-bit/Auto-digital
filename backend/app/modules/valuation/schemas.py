# app/modules/vehicles/schemas.py
# ================================================================
# Auto-D Kenya - Vehicle Schemas
# ================================================================
# TYPE: MODULE - Vehicle management Pydantic schemas
# Compatible with Pydantic v2
# ================================================================

from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, field_validator


# ================================================================
# CATEGORY SCHEMAS
# ================================================================

class CategoryResponse(BaseModel):
    """Vehicle category response."""
    
    id: int = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    icon: Optional[str] = Field(None, description="Category icon")
    vehicle_count: int = Field(0, description="Number of vehicles in category")


# ================================================================
# MAKE SCHEMAS
# ================================================================

class MakeResponse(BaseModel):
    """Vehicle make response."""
    
    id: int = Field(..., description="Make ID")
    name: str = Field(..., description="Make name")
    country: Optional[str] = Field(None, description="Country of origin")
    logo_url: Optional[str] = Field(None, description="Make logo URL")
    vehicle_count: int = Field(0, description="Number of vehicles")
    category_id: Optional[int] = Field(None, description="Category ID")


# ================================================================
# MODEL SCHEMAS
# ================================================================

class ModelResponse(BaseModel):
    """Vehicle model response."""
    
    id: int = Field(..., description="Model ID")
    name: str = Field(..., description="Model name")
    body_type: Optional[str] = Field(None, description="Body type")
    vehicle_count: int = Field(0, description="Number of vehicles")
    make_id: int = Field(..., description="Make ID")
    make_name: Optional[str] = Field(None, description="Make name")
    start_year: Optional[int] = Field(None, description="Production start year")
    end_year: Optional[int] = Field(None, description="Production end year")


# ================================================================
# GENERATION SCHEMAS
# ================================================================

class GenerationResponse(BaseModel):
    """Vehicle generation response."""
    
    id: int = Field(..., description="Generation ID")
    code: Optional[str] = Field(None, description="Generation code")
    start_year: Optional[int] = Field(None, description="Start year")
    end_year: Optional[int] = Field(None, description="End year")
    model_id: int = Field(..., description="Model ID")
    model_name: Optional[str] = Field(None, description="Model name")
    variant_count: int = Field(0, description="Number of variants")


# ================================================================
# VARIANT SCHEMAS
# ================================================================

class VariantResponse(BaseModel):
    """Vehicle variant response."""
    
    variant_id: int = Field(..., description="Variant ID")
    variant_name: Optional[str] = Field(None, description="Variant name")
    trim_level: Optional[str] = Field(None, description="Trim level")
    engine_size_cc: Optional[int] = Field(None, description="Engine size in CC")
    power_hp: Optional[int] = Field(None, description="Power in HP")
    torque_nm: Optional[int] = Field(None, description="Torque in Nm")
    fuel_consumption_combined: Optional[float] = Field(None, description="Fuel consumption combined")
    co2_emissions: Optional[int] = Field(None, description="CO2 emissions")
    seats: Optional[int] = Field(5, description="Number of seats")
    doors: Optional[int] = Field(4, description="Number of doors")
    fuel_type_name: Optional[str] = Field(None, description="Fuel type")
    transmission_type_name: Optional[str] = Field(None, description="Transmission type")
    drive_type_name: Optional[str] = Field(None, description="Drive type")
    body_type_name: Optional[str] = Field(None, description="Body type")
    generation_id: Optional[int] = Field(None, description="Generation ID")
    make_name: Optional[str] = Field(None, description="Make name")
    model_name: Optional[str] = Field(None, description="Model name")
    
    # Price fields
    estimated_value: Optional[float] = Field(None, description="Estimated value")
    market_value: Optional[float] = Field(None, description="Market value")
    price: Optional[float] = Field(None, description="Price")
    retail_price: Optional[float] = Field(None, description="Retail price")
    base_price: Optional[float] = Field(None, description="Base price")
    dealer_price: Optional[float] = Field(None, description="Dealer price")
    crsp_kes: Optional[float] = Field(None, description="CRSP price in KES")


# ================================================================
# VEHICLE MASTER SCHEMAS (merged from vehicle_master)
# ================================================================

class VehicleMasterResponse(BaseModel):
    """Comprehensive vehicle master data."""
    
    variant_id: int = Field(..., description="Variant ID")
    make_id: Optional[int] = Field(None, description="Make ID")
    make_name: Optional[str] = Field(None, description="Make name")
    model_id: Optional[int] = Field(None, description="Model ID")
    model_name: Optional[str] = Field(None, description="Model name")
    variant_name: Optional[str] = Field(None, description="Variant name")
    trim_level: Optional[str] = Field(None, description="Trim level")
    generation_id: Optional[int] = Field(None, description="Generation ID")
    generation_code: Optional[str] = Field(None, description="Generation code")
    engine_size_cc: Optional[int] = Field(None, description="Engine size in CC")
    power_hp: Optional[int] = Field(None, description="Power in HP")
    torque_nm: Optional[int] = Field(None, description="Torque in Nm")
    fuel_type_name: Optional[str] = Field(None, description="Fuel type")
    transmission_type_name: Optional[str] = Field(None, description="Transmission type")
    drive_type_name: Optional[str] = Field(None, description="Drive type")
    body_type_name: Optional[str] = Field(None, description="Body type")
    seats: Optional[int] = Field(5, description="Number of seats")
    doors: Optional[int] = Field(4, description="Number of doors")
    fuel_consumption_combined: Optional[float] = Field(None, description="Fuel consumption combined")
    co2_emissions: Optional[int] = Field(None, description="CO2 emissions")
    estimated_value: Optional[float] = Field(None, description="Estimated value")
    market_value: Optional[float] = Field(None, description="Market value")
    crsp_kes: Optional[float] = Field(None, description="CRSP price in KES")
    created_at: Optional[datetime] = Field(None, description="Created at")
    updated_at: Optional[datetime] = Field(None, description="Updated at")


class VehicleSearchResponse(BaseModel):
    """Vehicle search response."""
    
    variant_id: int = Field(..., description="Variant ID")
    make_name: str = Field(..., description="Make name")
    model_name: str = Field(..., description="Model name")
    variant_name: Optional[str] = Field(None, description="Variant name")
    year: Optional[int] = Field(None, description="Year")
    engine_size_cc: Optional[int] = Field(None, description="Engine size in CC")
    fuel_type_name: Optional[str] = Field(None, description="Fuel type")
    body_type_name: Optional[str] = Field(None, description="Body type")
    estimated_value: Optional[float] = Field(None, description="Estimated value")
    similarity_score: Optional[float] = Field(None, description="Search similarity score")


# ================================================================
# BASE PRICE SCHEMAS
# ================================================================

class BasePriceResponse(BaseModel):
    """Base price response."""
    
    variant_id: int = Field(..., description="Variant ID")
    make_name: str = Field(..., description="Make name")
    model_name: str = Field(..., description="Model name")
    variant_name: Optional[str] = Field(None, description="Variant name")
    base_price: float = Field(..., description="Base price in KES")
    currency: str = Field("KES", description="Currency code")
    source: Optional[str] = Field(None, description="Price source")
    last_updated: Optional[datetime] = Field(None, description="Last updated")
    year: Optional[int] = Field(None, description="Year")


# ================================================================
# STATISTICS SCHEMAS
# ================================================================

class VehicleStatisticsResponse(BaseModel):
    """Vehicle statistics response."""
    
    total_vehicles: int = Field(0, description="Total vehicles")
    total_makes: int = Field(0, description="Total makes")
    total_models: int = Field(0, description="Total models")
    total_variants: int = Field(0, description="Total variants")
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
    vehicles_by_body_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Vehicles by body type"
    )
    average_price: float = Field(0, description="Average price")
    min_price: float = Field(0, description="Minimum price")
    max_price: float = Field(0, description="Maximum price")
    last_updated: Optional[datetime] = Field(None, description="Last updated")


# ================================================================
# HEALTH SCHEMAS
# ================================================================

class VehicleHealthResponse(BaseModel):
    """Vehicle service health response."""
    
    status: str = Field(..., description="Service health status")
    service: str = Field("vehicles", description="Service name")
    version: str = Field("1.0", description="Service version")
    timestamp: str = Field(..., description="Health check timestamp")
    database: Optional[str] = Field(None, description="Database health status")
    error: Optional[str] = Field(None, description="Error message if any")


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    "CategoryResponse",
    "MakeResponse",
    "ModelResponse",
    "GenerationResponse",
    "VariantResponse",
    "VehicleMasterResponse",
    "VehicleSearchResponse",
    "BasePriceResponse",
    "VehicleStatisticsResponse",
    "VehicleHealthResponse",
]
