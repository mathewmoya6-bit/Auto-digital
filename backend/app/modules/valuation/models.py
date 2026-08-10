# app/modules/valuation/models.py

"""
Auto-D Kenya - Valuation Models

These models are aligned with the current PostgreSQL
calculate_vehicle_valuation() function.

Architecture:

```
PostgreSQL valuation function
          ↓
VehicleValuationResult
          ↓
   ValuationReport
          ↓
Analysis / Comparables / History
```

"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict

# ================================================================

# 1. DATABASE VALUATION RESULT

# ================================================================

class VehicleValuationResult(BaseModel):
"""
Exact application representation of the result returned by:

```
    public.calculate_vehicle_valuation()

PostgreSQL is the single source of truth for the valuation
calculations.
"""

model_config = ConfigDict(
    from_attributes=True
)

# ------------------------------------------------------------
# Identification
# ------------------------------------------------------------

valuation_id: int = Field(
    ...,
    description="Primary valuation result ID"
)

vehicle_crsp_id: int = Field(
    ...,
    gt=0,
    description="CRSP vehicle price ID"
)

# ------------------------------------------------------------
# Vehicle
# ------------------------------------------------------------

make: str = Field(
    ...,
    description="Vehicle manufacturer"
)

model: str = Field(
    ...,
    description="Vehicle model / variant"
)

manufacture_year: int = Field(
    ...,
    ge=1900,
    description="Vehicle manufacture year"
)

vehicle_age: int = Field(
    ...,
    ge=0,
    description="Calculated vehicle age"
)

# ------------------------------------------------------------
# CRSP
# ------------------------------------------------------------

crsp_value: Decimal = Field(
    ...,
    ge=0,
    description="Current CRSP value in KES"
)

# ------------------------------------------------------------
# Depreciation
# ------------------------------------------------------------

depreciation_rate: Decimal = Field(
    ...,
    ge=0,
    le=100,
    description="Depreciation percentage"
)

depreciation_value: Decimal = Field(
    ...,
    ge=0,
    description="Depreciation amount in KES"
)

value_after_depreciation: Decimal = Field(
    ...,
    ge=0,
    description="Value after depreciation in KES"
)

# ------------------------------------------------------------
# Adjustments
# ------------------------------------------------------------

mileage_adjustment: Decimal = Field(
    ...,
    description="Mileage adjustment in KES"
)

condition_adjustment: Decimal = Field(
    ...,
    description="Condition adjustment in KES"
)

accident_adjustment: Decimal = Field(
    ...,
    description="Accident adjustment in KES"
)

location_adjustment: Decimal = Field(
    ...,
    description="Location adjustment in KES"
)

market_adjustment: Decimal = Field(
    ...,
    description="Model market adjustment in KES"
)

# ------------------------------------------------------------
# Final valuation
# ------------------------------------------------------------

final_market_value: Decimal = Field(
    ...,
    ge=0,
    description="Final market value before profit margin"
)

# ------------------------------------------------------------
# Profit margin
# ------------------------------------------------------------

profit_margin_percent: Decimal = Field(
    ...,
    ge=0,
    le=100,
    description="Dealer profit margin percentage"
)

profit_margin_value: Decimal = Field(
    ...,
    ge=0,
    description="Dealer profit margin amount in KES"
)

recommended_selling_price: Decimal = Field(
    ...,
    ge=0,
    description="Recommended selling price including profit"
)

# ------------------------------------------------------------
# Confidence
# ------------------------------------------------------------

confidence_score: Decimal = Field(
    ...,
    ge=0,
    le=100,
    description="Valuation confidence score from 0 to 100"
)

# ------------------------------------------------------------
# Reference
# ------------------------------------------------------------

valuation_reference: str = Field(
    ...,
    description="Unique AUTO-D valuation reference"
)
```

# ================================================================

# 2. VALUATION REQUEST

# ================================================================

class ValuationRequest(BaseModel):
"""
Input accepted by the valuation API.
"""

```
vehicle_crsp_id: int = Field(
    ...,
    gt=0,
    description="CRSP vehicle price ID"
)

manufacture_year: int = Field(
    ...,
    ge=1900,
    description="Vehicle manufacture year"
)

mileage_km: int = Field(
    0,
    ge=0,
    description="Current vehicle mileage in kilometres"
)

vehicle_type: str = Field(
    "SEDAN",
    description="Vehicle type"
)

condition_name: str = Field(
    "GOOD",
    description="Vehicle condition"
)

accident_status: str = Field(
    "NONE",
    description="Accident status"
)

location_name: str = Field(
    "NAIROBI",
    description="Vehicle location"
)

profit_margin_percent: Decimal = Field(
    Decimal("5.00"),
    ge=0,
    le=100,
    description="Dealer profit margin percentage"
)
```

# ================================================================

# 3. VALUATION REPORT

# ================================================================

class ValuationReport(BaseModel):
"""
Higher-level application valuation report.

```
VehicleValuationResult contains the actual calculated values.
This model contains the report-level information around them.
"""

report_id: str = Field(
    ...,
    description="Application valuation report ID"
)

user_id: Optional[str] = Field(
    None,
    description="User who requested the valuation"
)

vehicle_id: Optional[str] = Field(
    None,
    description="User vehicle ID"
)

valuation: VehicleValuationResult = Field(
    ...,
    description="Canonical valuation result"
)

# ------------------------------------------------------------
# Valuation metadata
# ------------------------------------------------------------

valuation_method: str = Field(
    "AUTO-D",
    description="Valuation method"
)

data_points: int = Field(
    0,
    ge=0,
    description="Number of supporting data points"
)

# ------------------------------------------------------------
# Market comparison
# ------------------------------------------------------------

market_average: Optional[Decimal] = Field(
    None,
    description="Market average price"
)

market_low: Optional[Decimal] = Field(
    None,
    description="Lowest comparable market price"
)

market_high: Optional[Decimal] = Field(
    None,
    description="Highest comparable market price"
)

comparable_listings: int = Field(
    0,
    ge=0,
    description="Number of comparable listings"
)

# ------------------------------------------------------------
# Status
# ------------------------------------------------------------

status: str = Field(
    "completed",
    description="Valuation report status"
)

expires_at: Optional[datetime] = Field(
    None,
    description="Report expiration date"
)

# ------------------------------------------------------------
# Additional information
# ------------------------------------------------------------

notes: Optional[str] = Field(
    None,
    description="Additional valuation notes"
)

metadata: Dict[str, Any] = Field(
    default_factory=dict,
    description="Additional report metadata"
)

# ------------------------------------------------------------
# Timestamps
# ------------------------------------------------------------

created_at: datetime = Field(
    default_factory=datetime.utcnow
)

updated_at: datetime = Field(
    default_factory=datetime.utcnow
)
```

# ================================================================

# 4. VALUATION ANALYSIS

# ================================================================

class ValuationAnalysis(BaseModel):
"""
Additional market analysis associated with a valuation report.

```
This does not alter the PostgreSQL valuation calculation.
"""

analysis_id: str = Field(
    ...,
    description="Analysis ID"
)

report_id: str = Field(
    ...,
    description="Parent valuation report ID"
)

# ------------------------------------------------------------
# Market conditions
# ------------------------------------------------------------

market_trend: str = Field(
    "stable",
    description="Current market trend"
)

demand_level: str = Field(
    "medium",
    description="Market demand level"
)

supply_level: str = Field(
    "medium",
    description="Market supply level"
)

# ------------------------------------------------------------
# Key factors
# ------------------------------------------------------------

key_factors: List[str] = Field(
    default_factory=list,
    description="Important valuation factors"
)

factor_weights: Dict[str, float] = Field(
    default_factory=dict,
    description="Relative factor weights"
)

# ------------------------------------------------------------
# Risk
# ------------------------------------------------------------

risk_factors: List[str] = Field(
    default_factory=list,
    description="Identified valuation risks"
)

risk_score: float = Field(
    0.0,
    ge=0,
    le=100,
    description="Risk score from 0 to 100"
)

# ------------------------------------------------------------
# Recommendations
# ------------------------------------------------------------

recommendations: List[str] = Field(
    default_factory=list,
    description="Valuation recommendations"
)

price_suggestion: Optional[Decimal] = Field(
    None,
    ge=0,
    description="Suggested asking price"
)

negotiation_range: Dict[str, Decimal] = Field(
    default_factory=dict,
    description="Negotiation range"
)

# ------------------------------------------------------------
# Market insights
# ------------------------------------------------------------

market_insights: Dict[str, Any] = Field(
    default_factory=dict,
    description="Market intelligence"
)

seasonality_factor: Optional[float] = Field(
    None,
    description="Seasonality factor"
)

created_at: datetime = Field(
    default_factory=datetime.utcnow
)
```

# ================================================================

# 5. VALUATION HISTORY

# ================================================================

class ValuationHistory(BaseModel):
"""
Historical valuation snapshot for a vehicle.
"""

```
history_id: str = Field(
    ...,
    description="History record ID"
)

vehicle_id: str = Field(
    ...,
    description="User vehicle ID"
)

valuation_id: Optional[int] = Field(
    None,
    description="Database valuation ID"
)

valuation_date: datetime = Field(
    default_factory=datetime.utcnow
)

estimated_value: Decimal = Field(
    ...,
    ge=0,
    description="Historical estimated market value"
)

recommended_selling_price: Optional[Decimal] = Field(
    None,
    ge=0,
    description="Historical recommended selling price"
)

confidence_score: Decimal = Field(
    ...,
    ge=0,
    le=100,
    description="Historical confidence score"
)

created_at: datetime = Field(
    default_factory=datetime.utcnow
)
```

# ================================================================

# 6. VALUATION COMPARABLE

# ================================================================

class ValuationComparable(BaseModel):
"""
Comparable vehicle used for market analysis.

```
Comparables support the report but do not replace CRSP
as the primary valuation source.
"""

comparable_id: str = Field(
    ...,
    description="Comparable record ID"
)

report_id: str = Field(
    ...,
    description="Parent valuation report ID"
)

# ------------------------------------------------------------
# Vehicle
# ------------------------------------------------------------

make: str = Field(
    ...,
    description="Vehicle make"
)

model: str = Field(
    ...,
    description="Vehicle model"
)

variant: Optional[str] = Field(
    None,
    description="Vehicle variant"
)

year: int = Field(
    ...,
    ge=1900,
    description="Vehicle manufacture year"
)

mileage: int = Field(
    ...,
    ge=0,
    description="Vehicle mileage"
)

price: Decimal = Field(
    ...,
    ge=0,
    description="Comparable listing price"
)

# ------------------------------------------------------------
# Source
# ------------------------------------------------------------

source: str = Field(
    ...,
    description="Listing source"
)

source_id: Optional[str] = Field(
    None,
    description="Source listing ID"
)

listing_url: Optional[str] = Field(
    None,
    description="Source listing URL"
)

listing_date: Optional[datetime] = Field(
    None,
    description="Listing date"
)

# ------------------------------------------------------------
# Similarity
# ------------------------------------------------------------

similarity_score: float = Field(
    0.0,
    ge=0,
    le=1,
    description="Similarity score from 0 to 1"
)

distance: Optional[float] = Field(
    None,
    ge=0,
    description="Distance from target vehicle in kilometres"
)

created_at: datetime = Field(
    default_factory=datetime.utcnow
)
```

# ================================================================

# 7. COMPLETE REPORT RESPONSE

# ================================================================

class ValuationReportResponse(BaseModel):
"""
Complete API response containing the valuation,
analysis, comparables and vehicle details.
"""

```
report: ValuationReport

analysis: Optional[ValuationAnalysis] = None

comparables: List[ValuationComparable] = Field(
    default_factory=list
)

vehicle_details: Optional[Dict[str, Any]] = None
```

# ================================================================

# EXPORTS

# ================================================================

**all** = [
"VehicleValuationResult",
"ValuationRequest",
"ValuationReport",
"ValuationAnalysis",
"ValuationHistory",
"ValuationComparable",
"ValuationReportResponse",
]
