# app/modules/ownership/schemas.py
"""Ownership (TCO) schemas for Auto-D Kenya"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class TCORequest(BaseModel):
    """Total Cost of Ownership Request"""
    # Vehicle identification
    crsp_id: Optional[int] = Field(None, description="CRSP ID from vehicle_crsp_lookup")
    variant_id: Optional[int] = Field(None, description="Variant ID")
    
    # Financial details
    purchase_price: float = Field(..., gt=0, description="Purchase price in KES")
    down_payment: float = Field(0, ge=0, description="Down payment in KES")
    loan_term_years: int = Field(3, ge=1, le=10, description="Loan term in years")
    interest_rate: float = Field(14.0, ge=0, le=30, description="Annual interest rate %")
    
    # Usage details
    annual_mileage: float = Field(20000, gt=0, description="Annual mileage in km")
    fuel_price: float = Field(200, gt=0, description="Fuel price in KES/L")
    insurance_rate: float = Field(3.0, ge=0, le=10, description="Insurance rate % of vehicle value")
    maintenance_cost_per_km: float = Field(1.5, ge=0, le=10, description="Maintenance cost per km")
    tyre_cost_per_km: float = Field(0.8, ge=0, le=5, description="Tyre cost per km")
    
    # Options
    include_depreciation: bool = Field(True, description="Include depreciation in calculation")
    include_insurance: bool = Field(True, description="Include insurance in calculation")
    include_maintenance: bool = Field(True, description="Include maintenance in calculation")
    include_tyres: bool = Field(True, description="Include tyres in calculation")
    include_inflation: bool = Field(True, description="Apply inflation to costs")
    
    # Ownership period
    years: int = Field(5, ge=1, le=10, description="Ownership period in years")
    
    # Vehicle details
    vehicle_year: int = Field(2020, description="Vehicle year of manufacture")
    trip_type: Optional[str] = Field("mixed", description="Trip type: urban, highway, mixed, offroad")
    driving_style: Optional[str] = Field("normal", description="Driving style: eco, normal, aggressive")
    usage_type: Optional[str] = Field("private", description="Usage type: private, commercial, fleet, taxi")
    location: Optional[str] = Field("nairobi", description="Location")
    condition: Optional[str] = Field("good", description="Vehicle condition")
    
    # New fields from frontend
    vehicle_type: Optional[str] = Field("ice", description="Vehicle type: ice, hybrid, ev")
    fuel_type: Optional[str] = Field("petrol", description="Fuel type: petrol, diesel, hybrid, lpg, electric")
    vehicle_condition: Optional[str] = Field("new", description="Vehicle condition: new, used")
    purchase_type: Optional[str] = Field("cash", description="Purchase type: cash, finance")


class TCOResponse(BaseModel):
    """Total Cost of Ownership Response"""
    total_cost: float
    monthly_cost: float
    monthly_payment: float
    total_interest: float
    cost_per_km: float
    total_depreciation: float
    resale_value: float
    
    monthly_breakdown: Dict[str, float]
    components: List[Dict[str, Any]]
    yearly_breakdown: List[Dict[str, Any]]
    
    rci: Dict[str, Any]
    
    loan_details: Dict[str, Any]
    vehicle_details: Dict[str, Any]
    crsp_reference: Dict[str, Any]
    
    currency: str
    calculated_at: str
