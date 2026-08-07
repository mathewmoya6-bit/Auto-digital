"""
Auto-D Kenya
Vehicle Master Schemas

Pydantic models for Vehicle Master Admin API.
"""

from typing import Optional, Dict, Any

from pydantic import BaseModel, Field



# ==========================================================
# SEARCH PARAMETERS
# ==========================================================

class VehicleSearchParams(BaseModel):
    """
    Vehicle master search filters.
    """

    make: Optional[str] = None

    model: Optional[str] = None

    year: Optional[int] = None

    fuel: Optional[str] = None

    transmission: Optional[str] = None

    body_type: Optional[str] = None

    page: int = Field(
        default=1,
        ge=1
    )

    per_page: int = Field(
        default=20,
        ge=1,
        le=100
    )



# ==========================================================
# COMPLETE VEHICLE UPDATE
# ==========================================================

class VehicleMasterUpdate(BaseModel):
    """
    Complete vehicle update payload.

    Example:

    {
        "vehicle":{
            "make":"TOYOTA",
            "model":"COROLLA"
        },

        "specification":{
            "fuel":"PETROL"
        },

        "pricing":{
            "market_value":2800000
        }
    }
    """

    vehicle: Optional[Dict[str, Any]] = None

    specification: Optional[Dict[str, Any]] = None

    pricing: Optional[Dict[str, Any]] = None



# ==========================================================
# VEHICLE BASIC INFORMATION UPDATE
# ==========================================================

class VehicleUpdate(BaseModel):
    """
    Update vehicle identification fields.
    """

    make: Optional[str] = Field(
        default=None,
        max_length=100
    )

    model: Optional[str] = Field(
        default=None,
        max_length=150
    )

    model_number: Optional[str] = None

    currency: Optional[str] = "KES"

    source: Optional[str] = None



# ==========================================================
# SPECIFICATION UPDATE
# ==========================================================

class SpecificationUpdate(BaseModel):
    """
    Vehicle technical specification update.
    """

    transmission: Optional[str] = None

    drive_configuration: Optional[str] = None

    engine_capacity: Optional[str] = None

    body_type: Optional[str] = None

    gvw: Optional[str] = None

    seating: Optional[str] = None

    fuel: Optional[str] = None



# ==========================================================
# BASE PRICE UPDATE
# ==========================================================

class BasePriceUpdate(BaseModel):
    """
    Vehicle pricing update.
    """

    crsp_kes: Optional[float] = Field(
        default=None,
        gt=0
    )

    market_value: Optional[float] = Field(
        default=None,
        gt=0
    )

    insurance_value: Optional[float] = Field(
        default=None,
        gt=0
    )

    forced_sale_value: Optional[float] = Field(
        default=None,
        gt=0
    )

    trade_in_value: Optional[float] = Field(
        default=None,
        gt=0
    )



# ==========================================================
# VEHICLE RESPONSE
# ==========================================================

class VehicleMasterResponse(BaseModel):
    """
    Vehicle master database response.
    """

    id: int

    make: str

    model: str

    model_number: Optional[str] = None

    transmission: Optional[str] = None

    drive_configuration: Optional[str] = None

    engine_capacity: Optional[str] = None

    body_type: Optional[str] = None

    gvw: Optional[str] = None

    seating: Optional[str] = None

    fuel: Optional[str] = None

    crsp_kes: Optional[float] = None

    market_value: Optional[float] = None

    insurance_value: Optional[float] = None

    forced_sale_value: Optional[float] = None

    trade_in_value: Optional[float] = None

    currency: Optional[str] = "KES"

    source: Optional[str] = None

    is_active: Optional[bool] = True



# ==========================================================
# DASHBOARD RESPONSE
# ==========================================================

class VehicleMasterDashboardResponse(BaseModel):
    """
    Dashboard statistics response.
    """

    total_vehicles: int

    active_vehicles: int

    inactive_vehicles: int

    total_changes: int



# ==========================================================
# BULK PRICE UPDATE
# ==========================================================

class BulkPriceUpdate(BaseModel):
    """
    Bulk vehicle price update.
    """

    variant_id: int

    crsp_kes: float = Field(
        gt=0
    )
