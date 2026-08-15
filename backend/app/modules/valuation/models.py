"""
app/modules/valuation/models.py

Internal domain models for the valuation module.

These models mirror the ACTUAL PostgreSQL structures used by the
valuation system.

Important:
- vehicle_crsp provides CRSP matching information.
- vehicle_valuation_results / calculate_vehicle_valuation() RPC
  provides the persisted / computed valuation result.
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
    Result row returned by the calculate_vehicle_valuation() RPC.

    NOTE: extra="ignore" means any RPC column not declared below is
    silently dropped on parse (not raised as an error). If the SQL
    function's return shape changes, fields must be added here
    explicitly or they will vanish and cause AttributeErrors
    downstream in engine.py.

    Sample raw RPC row (from production logs):

        {
            'valuation_id': 54,
            'vehicle_crsp_id': 219,
            'make': 'BMW',
            'model': 'BMW 3 SERIES 320i',
            'manufacture_year': 2016,
            'vehicle_age': 10,
            'crsp_value': 7565959.28,
            'depreciation_rate': 60.0,
            'depreciation_value': 4539575.57,
            'value_after_depreciation': 3026383.71,
            'mileage_adjustment': 0.0,
            'condition_adjustment': 151319.19,
            'accident_adjustment': 0.0,
            'location_adjustment': 0.0,
            'market_adjustment': 0.0,
            'final_market_value': 3177702.9,
            'profit_margin_percent': 0.0,
            'profit_margin_value': 0.0,
            'recommended_selling_price': 3177702.9,
            'confidence_score': 79.0,
            'valuation_reference': 'AUTO-D-20260815101937-219'
        }
    """

    model_config = ConfigDict(extra="ignore")

    # --- identifiers -----------------------------------------------
    # The RPC returns "valuation_id", not "id". Keep both: "id" is
    # kept for backward compatibility with any code still reading
    # it (e.g. from a direct table select rather than the RPC),
    # and "valuation_id" captures what the RPC actually sends.
    id: Optional[int] = None
    valuation_id: Optional[int] = None
    vehicle_crsp_id: Optional[int] = None
    model_id: Optional[int] = None

    # --- vehicle identity --------------------------------------------
    make: Optional[str] = None
    model: Optional[str] = None
    manufacture_year: Optional[int] = None
    vehicle_age: Optional[int] = None
    mileage_km: Optional[int] = None
    vehicle_type: Optional[str] = None
    condition_name: Optional[str] = None
    accident_status: Optional[str] = None
    location_name: Optional[str] = None

    # --- valuation math -----------------------------------------------
    crsp_value: Optional[float] = None
    depreciation_rate: Optional[float] = None
    depreciation_value: Optional[float] = None
    value_after_depreciation: Optional[float] = None

    mileage_adjustment: Optional[float] = None
    condition_adjustment: Optional[float] = None
    accident_adjustment: Optional[float] = None
    location_adjustment: Optional[float] = None
    market_adjustment: Optional[float] = None

    final_market_value: Optional[float] = None
    confidence_score: Optional[float] = None

    # --- selling price / margin ----------------------------------------
    profit_margin_percent: Optional[float] = None
    profit_margin_value: Optional[float] = None
    recommended_selling_price: Optional[float] = None

    # --- reference -----------------------------------------------------
    valuation_reference: Optional[str] = None


__all__ = [
    "CRSPRecord",
    "ValuationResultRow",
]
