# app/modules/ownership/router.py
"""
Auto-D Kenya - Ownership (TCO) Routes
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.core.dependencies import get_current_user

router = APIRouter(
    prefix="/ownership",
    tags=["Ownership"],
)


# ============================================================
# SCHEMAS
# ============================================================

class TCORequest(BaseModel):
    """
    Total Cost of Ownership request.
    
    Matches the HTML frontend with all options:
    - Vehicle Type (ICE, Hybrid, EV)
    - Fuel Type (Petrol, Diesel, Hybrid, LPG, Electric)
    - Vehicle Condition (New, Used)
    - Purchase Type (Cash, Financing)
    """
    
    # ─── Vehicle Details ──────────────────────────────────────
    variant_id: int = Field(..., description="Vehicle variant ID", gt=0)
    vehicle_year: int = Field(2020, description="Vehicle year of manufacture", ge=1980, le=2026)
    vehicle_type: str = Field("ice", description="Vehicle type: ice, hybrid, ev")
    vehicle_condition: str = Field("new", description="Vehicle condition: new, used")
    fuel_type: str = Field("petrol", description="Fuel type: petrol, diesel, hybrid, lpg, electric, cng")
    
    # ─── Financial Details ────────────────────────────────────
    purchase_type: str = Field("cash", description="Purchase type: cash, finance")
    purchase_price: float = Field(4500000, description="Purchase price in KES", ge=100000)
    down_payment: float = Field(1000000, description="Down payment in KES", ge=0)
    loan_term_years: int = Field(3, description="Loan term in years", ge=1, le=7)
    interest_rate: float = Field(14.0, description="Annual interest rate percentage", ge=0, le=28)
    
    # ─── Usage Profile ────────────────────────────────────────
    annual_mileage: float = Field(20000, description="Annual mileage in km", ge=0, le=60000)
    fuel_price: float = Field(200, description="Fuel price in KES per litre", ge=0, le=500)
    insurance_rate: float = Field(3.0, description="Insurance rate percentage", ge=0, le=8)
    maintenance_cost_per_km: float = Field(1.5, description="Maintenance cost per km", ge=0, le=5)
    tyre_cost_per_km: float = Field(0.8, description="Tyre cost per km", ge=0, le=2)
    
    # ─── Toggles ──────────────────────────────────────────────
    include_depreciation: bool = Field(True, description="Include depreciation in calculation")
    include_insurance: bool = Field(True, description="Include insurance in calculation")
    include_maintenance: bool = Field(True, description="Include maintenance in calculation")
    include_tyres: bool = Field(True, description="Include tyres in calculation")
    include_inflation: bool = Field(True, description="Include inflation in calculation")
    
    @field_validator('fuel_type')
    @classmethod
    def validate_fuel_type(cls, v: str) -> str:
        allowed = ["petrol", "diesel", "hybrid", "lpg", "electric", "cng"]
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Fuel type must be one of: {', '.join(allowed)}")
        return v
    
    @field_validator('vehicle_type')
    @classmethod
    def validate_vehicle_type(cls, v: str) -> str:
        allowed = ["ice", "hybrid", "ev"]
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Vehicle type must be one of: {', '.join(allowed)}")
        return v
    
    @field_validator('vehicle_condition')
    @classmethod
    def validate_vehicle_condition(cls, v: str) -> str:
        allowed = ["new", "used"]
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Vehicle condition must be one of: {', '.join(allowed)}")
        return v
    
    @field_validator('purchase_type')
    @classmethod
    def validate_purchase_type(cls, v: str) -> str:
        allowed = ["cash", "finance"]
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Purchase type must be one of: {', '.join(allowed)}")
        return v
    
    @field_validator('vehicle_year')
    @classmethod
    def validate_vehicle_year(cls, v: int) -> int:
        current_year = datetime.now().year
        if v < 1980 or v > current_year + 1:
            raise ValueError(f"Vehicle year must be between 1980 and {current_year + 1}")
        return v
    
    @field_validator('annual_mileage')
    @classmethod
    def validate_annual_mileage(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Annual mileage cannot be negative")
        if v > 200000:
            raise ValueError("Annual mileage cannot exceed 200,000 km")
        return v
    
    @field_validator('purchase_price')
    @classmethod
    def validate_purchase_price(cls, v: float) -> float:
        if v < 100000:
            raise ValueError("Purchase price must be at least 100,000 KES")
        return v


# ─── Response Schemas ─────────────────────────────────────────

class TCOComponent(BaseModel):
    """Single cost component with percentage."""
    name: str = Field(..., description="Component name")
    amount: float = Field(..., description="Amount in KES")
    percentage: float = Field(..., description="Percentage of total cost")


class LoanDetails(BaseModel):
    """Loan calculation details."""
    principal: float = Field(..., description="Loan principal amount")
    interest_rate: float = Field(..., description="Annual interest rate")
    term_years: int = Field(..., description="Term in years")
    term_months: int = Field(..., description="Term in months")
    total_payment: float = Field(..., description="Total payment including interest")
    purchase_type: str = Field(..., description="Purchase type: cash or finance")


class VehicleDetails(BaseModel):
    """Vehicle details in response."""
    variant_id: int = Field(..., description="Vehicle variant ID")
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    variant: str = Field(..., description="Vehicle variant name")
    fuel_type: str = Field(..., description="Fuel type display name")
    fuel_type_display: str = Field(..., description="Fuel type display name")
    vehicle_condition: str = Field(..., description="Vehicle condition: new or used")
    purchase_type: str = Field(..., description="Purchase type: cash or finance")
    vehicle_year: int = Field(..., description="Vehicle year")


class TCOResponse(BaseModel):
    """Total Cost of Ownership response."""
    
    # ─── Summary ──────────────────────────────────────────────
    total_cost: float = Field(..., description="Total ownership cost")
    monthly_cost: float = Field(..., description="Average monthly cost")
    monthly_payment: float = Field(..., description="Monthly loan payment")
    total_interest: float = Field(..., description="Total interest paid")
    cost_per_km: float = Field(..., description="Cost per kilometer")
    total_depreciation: float = Field(..., description="Total depreciation over period")
    resale_value: float = Field(..., description="Estimated resale value")
    
    # ─── Components ───────────────────────────────────────────
    components: List[TCOComponent] = Field(..., description="Cost components breakdown")
    
    # ─── Yearly Breakdown ─────────────────────────────────────
    yearly_breakdown: List[dict] = Field(..., description="Year-by-year cost breakdown")
    
    # ─── Loan Details ─────────────────────────────────────────
    loan_details: LoanDetails = Field(..., description="Loan calculation details")
    
    # ─── Vehicle Details ──────────────────────────────────────
    vehicle_details: VehicleDetails = Field(..., description="Vehicle details")
    
    # ─── Metadata ─────────────────────────────────────────────
    currency: str = Field("KES", description="Currency code")
    calculated_at: str = Field(..., description="ISO timestamp of calculation")


# ─── Health Response ─────────────────────────────────────────

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: str = Field("1.0", description="API version")
    timestamp: str = Field(..., description="ISO timestamp")


# ============================================================
# ROUTES
# ============================================================

@router.post("/calculate", response_model=TCOResponse)
async def calculate_tco(
    request: TCORequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Calculate Total Cost of Ownership (TCO).
    
    POST /api/v1/ownership/calculate
    
    Returns a comprehensive TCO report including:
    - Total cost, monthly cost, and loan details
    - Cost component breakdown with percentages
    - Year-by-year cost projection
    - Vehicle details and metadata
    
    Supports:
    - Fuel types: Petrol, Diesel, Hybrid, LPG, Electric, CNG
    - Vehicle condition: New, Used
    - Purchase type: Cash, Financing
    - Toggleable components: Depreciation, Insurance, Maintenance, Tyres, Inflation
    """
    try:
        from app.modules.ownership.service import OwnershipService

        service = OwnershipService()

        result = await service.calculate_tco(
            request=request,
            user_id=current_user.get("id")
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TCO calculation failed: {str(e)}"
        )


@router.post("/calculate-public", response_model=TCOResponse)
async def calculate_tco_public(
    request: TCORequest,
):
    """
    Calculate Total Cost of Ownership (public endpoint).
    
    POST /api/v1/ownership/calculate-public
    
    Same as the authenticated endpoint but without saving history.
    Useful for testing and demo purposes.
    """
    try:
        from app.modules.ownership.service import OwnershipService

        service = OwnershipService()

        result = await service.calculate_tco(
            request=request,
            user_id=None
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TCO calculation failed: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
async def health():
    """
    Health check for ownership service.
    
    GET /api/v1/ownership/health
    """
    return {
        "status": "healthy",
        "service": "ownership",
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/fuel-types")
async def get_fuel_types():
    """
    Get available fuel types with prices and descriptions.
    
    GET /api/v1/ownership/fuel-types
    """
    return {
        "fuel_types": [
            {"value": "petrol", "label": "Petrol", "price": 200, "description": "Standard fuel for most vehicles"},
            {"value": "diesel", "label": "Diesel", "price": 190, "description": "More efficient, higher torque"},
            {"value": "hybrid", "label": "Hybrid", "price": 180, "description": "Combined petrol + electric"},
            {"value": "lpg", "label": "LPG", "price": 150, "description": "Liquefied Petroleum Gas"},
            {"value": "electric", "label": "Electric", "price": 0, "description": "Zero emissions, low running cost"},
            {"value": "cng", "label": "CNG", "price": 140, "description": "Compressed Natural Gas"}
        ]
    }


@router.get("/vehicle-conditions")
async def get_vehicle_conditions():
    """
    Get available vehicle conditions.
    
    GET /api/v1/ownership/vehicle-conditions
    """
    return {
        "conditions": [
            {"value": "new", "label": "New", "factor": 1.0, "description": "Brand new vehicle"},
            {"value": "used", "label": "Used", "factor": 0.85, "description": "Pre-owned vehicle"}
        ]
    }


@router.get("/purchase-types")
async def get_purchase_types():
    """
    Get available purchase types.
    
    GET /api/v1/ownership/purchase-types
    """
    return {
        "purchase_types": [
            {"value": "cash", "label": "Cash Purchase", "description": "Full payment upfront"},
            {"value": "finance", "label": "Financing", "description": "Loan with interest"}
        ]
    }


@router.get("/defaults")
async def get_defaults():
    """
    Get default values for the TCO calculator.
    
    GET /api/v1/ownership/defaults
    """
    return {
        "defaults": {
            "purchase_price": 4500000,
            "down_payment": 1000000,
            "loan_term_years": 3,
            "interest_rate": 14.0,
            "annual_mileage": 20000,
            "fuel_price": 200,
            "insurance_rate": 3.0,
            "maintenance_cost_per_km": 1.5,
            "tyre_cost_per_km": 0.8,
            "years": 5,
            "include_depreciation": True,
            "include_insurance": True,
            "include_maintenance": True,
            "include_tyres": True,
            "include_inflation": True,
            "vehicle_condition": "new",
            "purchase_type": "cash",
            "vehicle_type": "ice",
            "fuel_type": "petrol"
        }
    }
