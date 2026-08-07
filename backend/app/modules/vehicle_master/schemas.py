"""
Auto-D Kenya
Vehicle Master Schemas

Pydantic models for Vehicle Master Admin API.
"""

from typing import Optional, Dict, Any

from pydantic import BaseModel, Field



# ==========================================================
# COMPLETE VEHICLE UPDATE
# ==========================================================

class VehicleMasterUpdate(BaseModel):
    """
    Complete vehicle update payload.

    Example:

    {
        "vehicle": {
            "make": "Toyota",
            "model": "Corolla"
        },

        "specification": {
            "fuel": "PETROL"
        },

        "pricing": {
            "crsp_kes": 3500000
        }
    }
    """

    vehicle: Optional[Dict[str, Any]] = None

    specification: Optional[Dict[str, Any]] = None

    pricing: Optional[Dict[str, Any]] = None



# ==========================================================
# VEHICLE BASIC UPDATE
# ==========================================================

class VehicleUpdate(BaseModel):
    """
    Vehicle identity fields.
    """

    make: Optional[str] = Field(
        None,
        max_length=100
    )

    model: Optional[str] = Field(
        None,
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
    Technical vehicle specifications.
    """

    transmission: Optional[str] = None

    drive_configuration: Optional[str] = None

    engine_capacity: Optional[str] = None

    body_type: Optional[str] = None

    gvw: Optional[str] = None

    seating: Optional[str] = None

    fuel: Optional[str] = None



# ==========================================================
# PRICE UPDATE
# ==========================================================

class BasePriceUpdate(BaseModel):
    """
    Vehicle valuation prices.
    """

    crsp_kes: Optional[float] = Field(
        None,
        gt=0
    )

    market_value: Optional[float] = Field(
        None,
        gt=0
    )

    insurance_value: Optional[float] = Field(
        None,
        gt=0
    )

    forced_sale_value: Optional[float] = Field(
        None,
        gt=0
    )

    trade_in_value: Optional[float] = Field(
        None,
        gt=0
    )



# ==========================================================
# RESPONSE SCHEMA
# ==========================================================

class VehicleMasterResponse(BaseModel):
    """
    Vehicle master response.
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

    is_active: bool = True
