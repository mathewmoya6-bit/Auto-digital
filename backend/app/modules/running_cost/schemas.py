# app/modules/running_cost/schemas.py
# Auto-D Kenya - Running Cost Schemas
# ================================================================
# TYPE: MODULE - Running Cost Pydantic schemas


from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator
from typing_extensions import Literal



# ================================================================
# PROJECTION
# ================================================================


class ProjectionYear(BaseModel):
    """Single year projection."""

    year: int

    fuel: float

    service: float

    tyres: float

    insurance: float

    depreciation: float

    running_cost: float

    total: float

    value: float



class DepreciationBreakdown(BaseModel):

    year: int

    rate: float

    amount: float

    remaining_value: float



# ================================================================
# VEHICLE
# ================================================================


class VehicleInfo(BaseModel):

    initial_vehicle_cost: float

    purchase_price: float

    market_value: float

    insurance_value: float

    current_value: float

    resale_value: float

    depreciation_rate: float


    fuel_type: str

    fuel_efficiency: float

    engine_size: float


    year: int

    age: int


    category: Optional[str] = None

    body_type: Optional[str] = None

    trim_level: Optional[str] = None

    power_hp: Optional[int] = None

    transmission: Optional[str] = None

    drive_type: Optional[str] = None



# ================================================================
# COST COMPONENTS
# ================================================================


class TripCosts(BaseModel):

    distance: float

    running_cost: float

    cost_per_km: float



class CostBreakdown(BaseModel):

    fuel: float

    service: float

    tyres: float

    insurance: float

    depreciation: float



class PerKmBreakdown(BaseModel):

    fuel: float

    service: float

    tyres: float

    insurance: float

    depreciation: float



class MonthlyCosts(BaseModel):

    fuel: float

    service: float

    tyres: float

    insurance: float

    depreciation: float

    total: float



class AnnualCosts(BaseModel):

    fuel: float

    service: float

    tyres: float

    insurance: float

    depreciation: float

    total: float



# ================================================================
# PROJECTION DATA
# ================================================================


class ProjectionData(BaseModel):

    years: List[ProjectionYear]

    total_5_year_cost: float

    total_5_year_running_cost: float



# ================================================================
# FINANCE
# ================================================================


class FinanceData(BaseModel):

    financed: bool

    loan_amount: Optional[float] = None

    down_payment: Optional[float] = None

    interest_rate: Optional[float] = None

    loan_term: Optional[int] = None

    monthly_payment: Optional[float] = None

    total_interest: Optional[float] = None

    total_cost: Optional[float] = None



class CalculationOptions(BaseModel):

    include_insurance: bool

    include_tyres: bool

    include_maintenance: bool

    include_depreciation: bool

    financed: bool



class DrivingFactors(BaseModel):

    driving_style: str

    trip_type: str

    usage_type: str

    condition: str

    location: str

    factor: float



# ================================================================
# REQUEST
# ================================================================


class RunningCostRequest(BaseModel):

    variant_id: int = Field(
        ...,
        gt=0
    )


    distance: float = Field(
        150,
        gt=0
    )

    annual_mileage: float = Field(
        20000,
        gt=0
    )


    fuel_price: float = Field(
        200,
        gt=0
    )


    trip_type: Literal[
        "urban",
        "highway",
        "mixed",
        "offroad"
    ] = "mixed"


    driving_style: Literal[
        "eco",
        "normal",
        "aggressive"
    ] = "normal"


    usage_type: Literal[
        "private",
        "commercial",
        "fleet",
        "taxi"
    ] = "private"


    location: str = "nairobi"


    condition: Literal[
        "poor",
        "fair",
        "good",
        "excellent"
    ] = "good"


    year: int = 2024


    financed: bool = False


    down_payment: float = 30

    interest_rate: float = 16


    loan_term: int = 4

    years: int = 5


    include_insurance: bool = True

    include_maintenance: bool = True

    include_tyres: bool = True

    include_depreciation: bool = True


    insurance_type: str = "comprehensive"



    @field_validator("year")
    @classmethod
    def validate_year(cls,value):

        current = datetime.now(
            timezone.utc
        ).year

        if value > current + 1:
            raise ValueError(
                "Invalid vehicle year"
            )

        return value



# ================================================================
# RESPONSE
# ================================================================


class RunningCostResponse(BaseModel):

    tripTotal: float

    tripCostPerKm: float

    fuelCostTrip: float

    serviceTrip: float

    tyreTrip: float

    insuranceTrip: float

    depreciationTrip: float


    fuelCostPerKm: float

    servicePerKm: float

    tyrePerKm: float

    insurancePerKm: float

    depreciationPerKm: float


    monthlyFuel: float

    monthlyService: float

    monthlyTyre: float

    monthlyInsurance: float

    monthlyDepreciation: float


    annualFuel: float

    annualService: float

    annualTyre: float

    annualInsurance: float

    annualDepreciation: float


    distance: float

    cost_per_km: float


    fuel_cost: float

    service_cost: float

    tyre_cost: float

    insurance_cost: float

    depreciation_cost: float


    purchase_price: float

    market_value: float

    insurance_value: float

    current_value: float

    resale_value: float


    fuel_type: str

    fuel_consumption: float


    fiveYearData: List[ProjectionYear]

    five_year_total: float


    trip: TripCosts

    costs: CostBreakdown

    per_km: PerKmBreakdown

    monthly: MonthlyCosts

    annual: AnnualCosts

    projection: ProjectionData

    vehicle: VehicleInfo

    finance: FinanceData

    options: CalculationOptions

    driving_factors: DrivingFactors


    depreciation_breakdown: List[
        DepreciationBreakdown
    ]


    calculated_at: str


    total5YearCost: float

    originalCost: float

    ageAdjustedCost: float

    remainingValue: float

    fuelTypeDisplay: str

    fuelConsumption: float
