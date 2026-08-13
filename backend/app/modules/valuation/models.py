"""
models.py

Internal domain models mapped 1:1 onto database shapes: rows from
`vehicle_crsp` (or the `vehicle_crsp_lookup` view the frontend already
queries directly) and the row returned by the `calculate_vehicle_valuation`
SQL function. These are intentionally separate from `schemas.py` (the
public API contract) so a column rename in Postgres doesn't ripple
straight into the API response.

Field names mirror the Postgres columns exactly, based on the tested
output of calculate_vehicle_valuation:

    valuation_id, vehicle_crsp_id, make, model, manufacture_year,
    vehicle_age, crsp_value, depreciation_rate, depreciation_value,
    value_after_depreciation, mileage_adjustment, condition_adjustment,
    accident_adjustment, location_adjustment, market_adjustment,
    final_market_value, profit_margin_percent, profit_margin_value,
    recommended_selling_price, confidence_score, valuation_reference
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class CRSPRecord(BaseModel):
    """One row from vehicle_crsp / vehicle_crsp_lookup used to resolve
    a vehicle_crsp_id before calling the valuation function."""

    model_config = ConfigDict(extra="ignore")

    crsp_id: int
    make: str
    model: str
    trim_level: Optional[str] = None
    manufacture_year: Optional[int] = None
    crsp_year: Optional[int] = None
    crsp_kes: Optional[float] = None

    @property
    def year(self) -> Optional[int]:
        return self.manufacture_year or self.crsp_year


class ValuationResultRow(BaseModel):
    """One row returned by calculate_vehicle_valuation(...)."""

    model_config = ConfigDict(extra="ignore")

    valuation_id: Optional[int] = None
    vehicle_crsp_id: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    manufacture_year: Optional[int] = None
    vehicle_age: Optional[int] = None
    crsp_value: Optional[float] = None
    depreciation_rate: Optional[float] = None          # percent, e.g. 60.0000
    depreciation_value: Optional[float] = None
    value_after_depreciation: Optional[float] = None
    mileage_adjustment: Optional[float] = None
    condition_adjustment: Optional[float] = None
    accident_adjustment: Optional[float] = None
    location_adjustment: Optional[float] = None
    market_adjustment: Optional[float] = None
    final_market_value: Optional[float] = None
    profit_margin_percent: Optional[float] = None
    profit_margin_value: Optional[float] = None
    recommended_selling_price: Optional[float] = None
    confidence_score: Optional[float] = None
    valuation_reference: Optional[str] = None
