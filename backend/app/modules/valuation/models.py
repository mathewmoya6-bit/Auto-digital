"""
app/modules/valuation/models.py

Internal domain models for the valuation module.

These models mirror the ACTUAL PostgreSQL structures used by the
valuation system.

Important:
- vehicle_crsp provides CRSP matching information.
- vehicle_valuation_results stores the persisted valuation result.
- calculate_vehicle_valuation() remains the valuation calculation
  source of truth.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class CRSPRecord(BaseModel):
    """
    CRSP vehicle record used to resolve vehicle_crsp_id.

    Matches the actual vehicle_crsp columns used by the repository.
    """

    model_config = ConfigDict(extra="ignore")

    crsp_id: int
    make: str
    model: str

    trim_level: Optional[str] = None
    manufacture_year: Optional[int] = None
    crsp_kes: Optional[float] = None

    @property
    def year(self) -> Optional[int]:
        return self.manufacture_year


class ValuationResultRow(BaseModel):
    """
    Persisted valuation result.

    Matches public.vehicle_valuation_results.
    """

    model_config = ConfigDict(extra="ignore")

    id: Optional[int] = None

    vehicle_crsp_id: Optional[int] = None
    model_id: Optional[int] = None

    manufacture_year: Optional[int] = None
    mileage_km: Optional[int] = None

    vehicle_type: Optional[str] = None
    condition_name: Optional[str] = None
    accident_status: Optional[str] = None
    location_name: Optional[str] = None

    crsp_value: Optional[float] = None

    depreciation_rate: Optional[float] = None
    depreciation_value: Optional[float] = None

    mileage_adjustment: Optional[float] = None
    condition_adjustment: Optional[float] = None
    accident_adjustment: Optional[float] = None
    location_adjustment: Optional[float] = None

    final_market_value: Optional[float] = None
    confidence_score: Optional[float] = None

    valuation_reference: Optional[str] = None

    profit_margin_percent: Optional[float] = None
    profit_margin_value: Optional[float] = None
    recommended_selling_price: Optional[float] = None
