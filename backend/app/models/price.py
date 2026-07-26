# app/models/price.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

class VehicleCondition(str, Enum):
    NEW = "new"
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"

class PriceSource(str, Enum):
    JIJI = "jiji.co.ke"
    CHEKI = "cheki.co.ke"
    AUTOCHEK = "autochek.co.ke"
    BEEPBEEP = "beepbeep.co.ke"
    PIGIAME = "pigiame.co.ke"
    MARKET_AVERAGE = "market_average"
    AI_ESTIMATE = "ai_estimate"
    MANUAL = "manual"

class MarketPrice(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    variant_id: UUID
    year: int
    price_kes: int
    source: PriceSource
    source_url: Optional[str] = None
    condition: VehicleCondition = VehicleCondition.GOOD
    mileage_km: Optional[int] = None
    recorded_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True

class LocationPriceFactor(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    county: str
    factor: float
    created_at: datetime = Field(default_factory=datetime.now)

class PriceAnalysis(BaseModel):
    """Market price analysis with multiple metrics"""
    variant_id: UUID
    year: int
    sample_size: int
    median_price: int
    average_price: int
    min_price: int
    max_price: int
    standard_deviation: float
    confidence_score: float
    price_range: Dict[str, int]
    adjusted_price: int
    factors_applied: Dict[str, float]
    source_breakdown: Dict[str, int]  # Count by source

class AlignedPrice(BaseModel):
    """Final aligned price with confidence"""
    variant_id: UUID
    year: int
    base_price: int
    adjusted_price: int
    market_min: int
    market_max: int
    market_median: int
    sample_size: int
    confidence_score: float
    factors_applied: dict
    source_breakdown: dict
    estimated: bool = False
    primary_source: Optional[str] = None
