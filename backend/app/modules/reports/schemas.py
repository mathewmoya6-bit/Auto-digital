# app/modules/reports/schemas.py
# ================================================================
# Auto-D Kenya - Reports Schemas
# ================================================================

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field


# ─── Request Schemas ──────────────────────────────────────────────

class ReportGenerateRequest(BaseModel):
    """Report generation request."""
    
    report_type: str = Field(..., description="Report type: valuation, vehicle, payment, etc.")
    vehicle_id: Optional[UUID] = Field(None, description="Vehicle ID")
    user_id: Optional[UUID] = Field(None, description="User ID")
    start_date: Optional[datetime] = Field(None, description="Start date for data")
    end_date: Optional[datetime] = Field(None, description="End date for data")
    format: str = Field("pdf", description="Report format: pdf, html, json")
    include_charts: bool = Field(True, description="Include charts in report")
    include_comparables: bool = Field(True, description="Include comparable data")


class ReportListRequest(BaseModel):
    """Report list request."""
    
    report_type: Optional[str] = Field(None, description="Filter by report type")
    status: Optional[str] = Field(None, description="Filter by status")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    offset: int = Field(0, ge=0, description="Pagination offset")


# ─── Response Schemas ─────────────────────────────────────────────

class ReportMetadata(BaseModel):
    """Report metadata."""
    
    id: UUID = Field(..., description="Report ID")
    report_number: str = Field(..., description="Unique report number")
    report_type: str = Field(..., description="Report type")
    title: str = Field(..., description="Report title")
    description: Optional[str] = Field(None, description="Report description")
    status: str = Field(..., description="Report status")
    format: str = Field(..., description="Report format")
    file_url: Optional[str] = Field(None, description="Report file URL")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    generated_by: UUID = Field(..., description="User ID who generated the report")


class ReportData(BaseModel):
    """Report data content."""
    
    vehicle: Optional[Dict[str, Any]] = Field(None, description="Vehicle information")
    valuation: Optional[Dict[str, Any]] = Field(None, description="Valuation data")
    payments: Optional[List[Dict[str, Any]]] = Field(None, description="Payment data")
    statistics: Optional[Dict[str, Any]] = Field(None, description="Statistics")
    charts: Optional[List[Dict[str, Any]]] = Field(None, description="Chart data")
    comparables: Optional[List[Dict[str, Any]]] = Field(None, description="Comparable data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional data")


class ReportGenerateResponse(BaseModel):
    """Report generation response."""
    
    success: bool = Field(..., description="Operation success")
    report_id: UUID = Field(..., description="Generated report ID")
    report_number: str = Field(..., description="Report number")
    file_url: str = Field(..., description="Download URL")
    expires_at: datetime = Field(..., description="Expiration timestamp")
    message: str = Field(..., description="Success message")


class ReportListItem(BaseModel):
    """Report list item."""
    
    id: UUID
    report_number: str
    report_type: str
    title: str
    status: str
    format: str
    file_size: Optional[int] = None
    created_at: datetime
    generated_by: UUID


class ReportListResponse(BaseModel):
    """Report list response."""
    
    items: List[ReportListItem] = Field(default_factory=list)
    total: int = Field(0, description="Total number of reports")
    limit: int = Field(20, description="Items per page")
    offset: int = Field(0, description="Pagination offset")


class ReportDownloadResponse(BaseModel):
    """Report download response."""
    
    file_url: str = Field(..., description="Download URL")
    filename: str = Field(..., description="Filename")
    expires_at: datetime = Field(..., description="Expiration timestamp")


class ReportDeleteResponse(BaseModel):
    """Report delete response."""
    
    success: bool = Field(..., description="Operation success")
    message: str = Field(..., description="Success message")
    report_id: UUID = Field(..., description="Deleted report ID")


# ─── Report Templates ─────────────────────────────────────────────

class ValuationReportTemplate(BaseModel):
    """Valuation report template data."""
    
    report_title: str = Field("Vehicle Valuation Report")
    company_name: str = Field("Auto-D Kenya")
    company_logo: Optional[str] = Field(None)
    vehicle_make: str
    vehicle_model: str
    vehicle_year: int
    vehicle_mileage: int
    estimated_value: Decimal
    value_range: Dict[str, Decimal]
    confidence_score: float
    depreciation_rate: float
    market_trend: str
    comparables: List[Dict[str, Any]]
    valuation_date: datetime
    disclaimer: str = Field(
        "This valuation is an estimate based on market data and should not be considered as a definitive appraisal."
    )


class VehicleReportTemplate(BaseModel):
    """Vehicle report template data."""
    
    report_title: str = Field("Vehicle Details Report")
    company_name: str = Field("Auto-D Kenya")
    vehicle: Dict[str, Any]
    owner: Dict[str, Any]
    maintenance_history: List[Dict[str, Any]]
    valuation_history: List[Dict[str, Any]]
    created_at: datetime


class PaymentReportTemplate(BaseModel):
    """Payment report template data."""
    
    report_title: str = Field("Payment History Report")
    company_name: str = Field("Auto-D Kenya")
    user: Dict[str, Any]
    payments: List[Dict[str, Any]]
    total_amount: Decimal
    payment_summary: Dict[str, Any]
    period: Dict[str, datetime]
    created_at: datetime


__all__ = [
    "ReportGenerateRequest",
    "ReportListRequest",
    "ReportMetadata",
    "ReportData",
    "ReportGenerateResponse",
    "ReportListItem",
    "ReportListResponse",
    "ReportDownloadResponse",
    "ReportDeleteResponse",
    "ValuationReportTemplate",
    "VehicleReportTemplate",
    "PaymentReportTemplate",
]
