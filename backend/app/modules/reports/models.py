# app/modules/reports/models.py
# ================================================================
# Auto-D Kenya - Reports Models
# ================================================================

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Report model."""
    
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID = Field(..., description="User who generated the report")
    report_number: str = Field(..., description="Unique report number")
    report_type: str = Field(..., description="Report type: valuation, vehicle, payment")
    title: str = Field(..., max_length=200, description="Report title")
    description: Optional[str] = Field(None, max_length=500, description="Report description")
    
    # Content
    data: Dict[str, Any] = Field(default_factory=dict, description="Report data")
    file_url: Optional[str] = Field(None, description="Report file URL")
    file_name: Optional[str] = Field(None, description="File name")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    
    # Format
    format: str = Field("pdf", description="Report format: pdf, html, json")
    include_charts: bool = Field(True, description="Whether charts are included")
    
    # Status
    status: str = Field("generating", description="Report status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Expiration
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    generated_at: Optional[datetime] = Field(None, description="Generation completion timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ReportTemplate(BaseModel):
    """Report template model."""
    
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., max_length=100, description="Template name")
    template_type: str = Field(..., description="Template type")
    description: Optional[str] = Field(None, max_length=500, description="Template description")
    
    # Template content
    template_data: Dict[str, Any] = Field(..., description="Template data")
    variables: Dict[str, str] = Field(default_factory=dict, description="Template variables")
    
    # Settings
    is_default: bool = Field(False, description="Whether this is the default template")
    is_active: bool = Field(True, description="Whether template is active")
    version: str = Field("1.0", description="Template version")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReportQueue(BaseModel):
    """Report generation queue model."""
    
    id: UUID = Field(default_factory=uuid4)
    report_id: UUID = Field(..., description="Foreign key to Report")
    
    # Queue status
    status: str = Field("pending", description="Queue status")
    priority: int = Field(0, description="Queue priority")
    
    # Attempts
    attempts: int = Field(0, description="Number of generation attempts")
    max_attempts: int = Field(3, description="Maximum attempts")
    last_error: Optional[str] = Field(None, description="Last error message")
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(None, description="Processing start time")
    completed_at: Optional[datetime] = Field(None, description="Processing completion time")
    locked_until: Optional[datetime] = Field(None, description="Queue lock expiration")


__all__ = [
    "Report",
    "ReportTemplate",
    "ReportQueue",
]
