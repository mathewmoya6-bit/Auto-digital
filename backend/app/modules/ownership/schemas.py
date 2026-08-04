# app/modules/ownership/schemas.py
# Auto-D Kenya - TCO / Ownership Schemas
# ================================================================
# TYPE: MODULE - Total Cost of Ownership Pydantic schemas


from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator



# ================================================================
# REQUEST SCHEMA
# ================================================================


class TCORequest(BaseModel):
    """
    Total Cost of Ownership calculation request.
    """

    variant_id: int = Field(
        ...,
        gt=0,
        description="Vehicle variant ID"
    )

    vehicle_year: int = Field(
        2020,
        ge=1980,
        description="Vehicle manufacturing year"
    )

    vehicle_type: str = "ice"

    vehicle_condition: str = "new"

    fuel_type: str = "petrol"


    # Financial

    purchase_type: str = "cash"

    purchase_price: float = Field(
        4500000,
        ge=100000
    )

    down_payment: float = Field(
        1000000,
        ge=0
    )

    loan_term_years: int = Field(
        3,
        ge=1,
        le=7
    )

    interest_rate: float = Field(
        14.0,
        ge=0,
        le=50
    )


    # Usage

    annual_mileage: float = Field(
        20000,
        ge=0,
        le=200000
    )

    fuel_price: float = Field(
        200,
        ge=0
    )

    insurance_rate: float = Field(
        3.0,
        ge=0
    )

    maintenance_cost_per_km: float = Field(
        1.5,
        ge=0
    )

    tyre_cost_per_km: float = Field(
        0.8,
        ge=0
    )


    # Options

    include_depreciation: bool = True
    include_insurance: bool = True
    include_maintenance: bool = True
    include_tyres: bool = True
    include_inflation: bool = True



    @field_validator(
        "fuel_type"
    )
    @classmethod
    def validate_fuel(cls, value: str):

        allowed = {
            "petrol",
            "diesel",
            "hybrid",
            "electric",
            "lpg",
            "cng"
        }

        value = value.lower()

        if value not in allowed:
            raise ValueError(
                "Invalid fuel type"
            )

        return value



    @field_validator(
        "vehicle_type"
    )
    @classmethod
    def validate_vehicle_type(cls, value: str):

        allowed = {
            "ice",
            "hybrid",
            "ev"
        }

        value = value.lower()

        if value not in allowed:
            raise ValueError(
                "Invalid vehicle type"
            )

        return value



    @field_validator(
        "vehicle_condition"
    )
    @classmethod
    def validate_condition(cls, value: str):

        allowed = {
            "new",
            "used"
        }

        value = value.lower()

        if value not in allowed:
            raise ValueError(
                "Invalid vehicle condition"
            )

        return value



    @field_validator(
        "purchase_type"
    )
    @classmethod
    def validate_purchase_type(cls, value: str):

        allowed = {
            "cash",
            "finance"
        }

        value = value.lower()

        if value not in allowed:
            raise ValueError(
                "Invalid purchase type"
            )

        return value



# ================================================================
# RESPONSE COMPONENTS
# ================================================================


class MonthlyBreakdown(BaseModel):

    loan_payment: float

    fuel: float

    maintenance: float

    tyres: float

    insurance: float

    total: float



class TCOComponent(BaseModel):

    name: str

    amount: float

    percentage: float



class LoanDetails(BaseModel):

    principal: float

    interest_rate: float

    term_years: int

    term_months: int

    total_payment: float

    purchase_type: str



class VehicleDetails(BaseModel):

    variant_id: int

    make: str

    model: str

    variant: str

    fuel_type: str

    fuel_type_display: str

    vehicle_condition: str

    purchase_type: str

    vehicle_year: int

    vehicle_type: str = "ice"



class YearlyBreakdownItem(BaseModel):

    year: int

    total_cost: float

    depreciation: float

    running_cost: float

    insurance: float

    loan_payment: float

    fuel: float

    maintenance: float

    tyres: float

    vehicle_value: float



# ================================================================
# MAIN RESPONSE
# ================================================================


class TCOResponse(BaseModel):

    total_cost: float

    monthly_cost: float

    monthly_payment: float

    total_interest: float

    cost_per_km: float

    total_depreciation: float

    resale_value: float


    monthly_breakdown: MonthlyBreakdown

    components: List[TCOComponent]

    yearly_breakdown: List[YearlyBreakdownItem]

    loan_details: LoanDetails

    vehicle_details: VehicleDetails


    currency: str = "KES"

    calculated_at: str



# ================================================================
# STATIC OPTION RESPONSES
# ================================================================


class HealthResponse(BaseModel):

    status: str

    service: str

    version: str = "1.0"

    timestamp: str



class FuelTypeItem(BaseModel):

    value: str

    label: str

    price: float

    description: str



class FuelTypesResponse(BaseModel):

    fuel_types: List[FuelTypeItem]



class VehicleConditionItem(BaseModel):

    value: str

    label: str

    factor: float

    description: str



class VehicleConditionsResponse(BaseModel):

    conditions: List[VehicleConditionItem]



class PurchaseTypeItem(BaseModel):

    value: str

    label: str

    description: str



class PurchaseTypesResponse(BaseModel):

    purchase_types: List[PurchaseTypeItem]



class DefaultsResponse(BaseModel):

    defaults: Dict[str, Any]



# ================================================================
# FACTORY
# ================================================================


def create_tco_response(
    total_cost: float,
    monthly_cost: float,
    monthly_payment: float,
    total_interest: float,
    cost_per_km: float,
    total_depreciation: float,
    resale_value: float,
    monthly_breakdown: Dict[str, float],
    components: List[Dict[str, Any]],
    yearly_breakdown: List[Dict[str, Any]],
    loan_details: Dict[str, Any],
    vehicle_details: Dict[str, Any],
    currency: str = "KES"
) -> TCOResponse:


    return TCOResponse(

        total_cost=round(total_cost,2),
        monthly_cost=round(monthly_cost,2),
        monthly_payment=round(monthly_payment,2),
        total_interest=round(total_interest,2),
        cost_per_km=round(cost_per_km,2),
        total_depreciation=round(total_depreciation,2),
        resale_value=round(resale_value,2),

        monthly_breakdown=MonthlyBreakdown(
            **monthly_breakdown
        ),

        components=[
            TCOComponent(**item)
            for item in components
        ],

        yearly_breakdown=[
            YearlyBreakdownItem(**item)
            for item in yearly_breakdown
        ],

        loan_details=LoanDetails(
            **loan_details
        ),

        vehicle_details=VehicleDetails(
            **vehicle_details
        ),

        currency=currency,

        calculated_at=datetime.utcnow().isoformat()
    )
