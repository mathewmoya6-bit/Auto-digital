"""
app/modules/valuation/schemas.py

Pydantic v2 schemas for the Valuation domain.

IMPORTANT: The field names/nesting below (`valuation.*`, `vehicle.*`,
`analysis.*`, `report.*`) are locked to what instant-value.html (v6.0)
already parses in `UIController.showValuationResult()`. Do not rename
without updating the frontend's `vFallback()` lookups.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# -------------------------------------------------------------------------
# Enums -- mirror the <select> option values in instant-value.html exactly
# -------------------------------------------------------------------------

class ConditionEnum(str, Enum):
    excellent = "excellent"
    very_good = "very_good"
    good = "good"
    fair = "fair"
    poor = "poor"


class AccidentHistoryEnum(str, Enum):
    none = "none"
    minor = "minor"
    major = "major"
    total_loss = "total_loss"


class FuelTypeEnum(str, Enum):
    petrol = "petrol"
    diesel = "diesel"
    lpg = "lpg"
    electric = "electric"


class TransmissionEnum(str, Enum):
    manual = "manual"
    automatic = "automatic"
    cvt = "cvt"
    amt = "amt"


class VehicleTypeEnum(str, Enum):
    sedan = "sedan"
    suv = "suv"
    hatchback = "hatchback"
    wagon = "wagon"
    pickup = "pickup"
    van = "van"
    truck = "truck"
    coupe = "coupe"
    motorcycle = "motorcycle"
    other = "other"


# -------------------------------------------------------------------------
# Request
# -------------------------------------------------------------------------

class ValuationRequest(BaseModel):
    """Body of POST /valuation/calculate and /calculate-public.

    Field set matches `formData` built in App.calculateValuation() in
    instant-value.html verbatim.
    """

    make: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    trim: Optional[str] = Field(None, max_length=150)
    year: int = Field(..., ge=1980, le=datetime.utcnow().year + 1)

    mileage: float = Field(..., ge=0, le=2_000_000)
    condition: ConditionEnum = ConditionEnum.good
    accident_history: AccidentHistoryEnum = AccidentHistoryEnum.none
    previous_owners: int = Field(1, ge=0, le=20)
    location: str = Field("nairobi", max_length=50)
    fuel_type: FuelTypeEnum = FuelTypeEnum.petrol
    transmission: TransmissionEnum = TransmissionEnum.automatic
    vehicle_type: VehicleTypeEnum = VehicleTypeEnum.sedan
    profit_margin: float = Field(0, ge=0, le=100)

    # Populated client-side from the selected trim's dataset attrs
    # (see trimSelect option.dataset in instant-value.html loadTrims()).
    engine_capacity: Optional[str] = None
    # engine_capacity_id is the FK actually used server-side for the
    # vehicle_crsp_prices lookup (per the Aug CRSP alignment work).
    # The current frontend build (v6.0) does not yet send this -- it only
    # sends the free-text `engine_capacity` string plus a client-computed
    # `crsp_kes`. Until instant-value.html is updated to pass
    # `engine_capacity_id` (mirroring total-cost-ownership.html /
    # mileage-running-cost.html), the repository falls back to a fuzzy
    # make/model/trim/year match. See ValuationRepository.get_crsp_match().
    engine_capacity_id: Optional[int] = None

    # Client already resolved this against the CRSP view during trim
    # selection -- treated as an untrusted hint, never as source of truth.
    # The engine re-derives its own CRSP figure server-side and only uses
    # this for a variance sanity-check / fallback if the server lookup
    # misses.
    crsp_kes: Optional[float] = None

    registration: Optional[str] = Field(None, max_length=15)

    @field_validator("registration")
    @classmethod
    def _upper_reg(cls, v: Optional[str]) -> Optional[str]:
        return v.upper().strip() if v else v


class BulkValuationRequest(BaseModel):
    items: list[ValuationRequest] = Field(..., min_length=1, max_length=50)


class CompareValuationRequest(BaseModel):
    items: list[ValuationRequest] = Field(..., min_length=2, max_length=10)


# -------------------------------------------------------------------------
# Response building blocks
# -------------------------------------------------------------------------

class VehicleBlock(BaseModel):
    make: str
    model: str
    trim: Optional[str] = None
    year: int
    mileage: float
    location: str
    condition: ConditionEnum
    fuel_type: FuelTypeEnum
    transmission: TransmissionEnum
    engine_capacity: Optional[str] = None
    vehicle_type: VehicleTypeEnum


class AdjustmentsBlock(BaseModel):
    """Multiplicative adjustment factors, e.g. 1.05 = +5%, 0.9 = -10%.

    Keys must match the `labels` map in UIController.displayAdjustments().
    Only non-1.0 / non-zero entries get rendered client-side, so it's safe
    to always include the full set here.
    """

    condition: float = 1.0
    accident: float = 1.0
    previous_owners: float = 1.0
    location: float = 1.0
    fuel_type: float = 1.0
    transmission: float = 1.0
    vehicle_type: float = 1.0
    market: float = 1.0


class AnalysisBlock(BaseModel):
    vehicle_age: int
    depreciation_rate: float          # fraction, e.g. 0.12 = 12%
    depreciation_amount: float        # KES, positive magnitude
    mileage_adjustment: float         # fraction, signed
    adjustments: AdjustmentsBlock


class ValuationBlock(BaseModel):
    estimated_vehicle_value: float
    confidence_score: float = Field(..., ge=0, le=100)
    recommended_selling_price: Optional[float] = None


class ReportBlock(BaseModel):
    report_number: str
    report_id: Optional[UUID] = None
    generated_at: datetime


class CRSPMatchBlock(BaseModel):
    matched: bool
    matched_line: Optional[str] = None
    base_price_kes: Optional[float] = None
    reference_value_kes: Optional[float] = None
    variance_pct: Optional[float] = None
    source: Optional[str] = None  # "engine_capacity_id" | "fuzzy_match" | "client_hint"


class ValuationData(BaseModel):
    vehicle: VehicleBlock
    valuation: ValuationBlock
    analysis: AnalysisBlock
    report: ReportBlock
    crsp: Optional[CRSPMatchBlock] = None


class ValuationResponse(BaseModel):
    """Top-level shape returned by /valuation/calculate*.

    instant-value.html checks `result.valuation || result.final_value ||
    result.final_market_value` then reads `result.data || result`, so
    nesting everything under `data` (as done here) is compatible.
    """

    success: bool = True
    data: ValuationData


class BulkValuationResponse(BaseModel):
    success: bool = True
    results: list[ValuationData]
    failed: list[dict] = Field(default_factory=list)


class CompareValuationResponse(BaseModel):
    success: bool = True
    results: list[ValuationData]
    best_value: Optional[int] = None  # index into results


class ValuationHistoryItem(BaseModel):
    report_id: UUID
    report_number: str
    make: str
    model: str
    year: int
    estimated_vehicle_value: float
    created_at: datetime


class ValuationHistoryResponse(BaseModel):
    success: bool = True
    items: list[ValuationHistoryItem]
    total: int
    page: int
    page_size: int


class ValuationStatsResponse(BaseModel):
    total_valuations: int
    avg_confidence_score: float
    avg_estimated_value: float
    top_makes: list[dict]


class HealthResponse(BaseModel):
    status: str
    engine_version: str
    crsp_lookup_available: bool
