# app/modules/scraper/schemas.py
# Auto-D Kenya - Scraper Schemas
# ================================================================
# TYPE: MODULE - Scraper Pydantic schemas
# ================================================================

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


# ================================================================
# ENUMS
# ================================================================

class ScraperSource(str, Enum):
    """Valid scraper sources."""
    ALL = "all"
    JIJI = "jiji"
    CHEKI = "cheki"
    AUTOCHEK = "autochek"
    BEEPBEEP = "beepbeep"


class JobStatus(str, Enum):
    """Valid job statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"


class ScraperCondition(str, Enum):
    """Vehicle condition."""
    NEW = "New"
    USED = "Used"
    CERTIFIED_PRE_OWNED = "Certified Pre-Owned"


class FuelType(str, Enum):
    """Vehicle fuel types."""
    PETROL = "Petrol"
    DIESEL = "Diesel"
    ELECTRIC = "Electric"
    HYBRID = "Hybrid"
    CNG = "CNG"
    LPG = "LPG"


class TransmissionType(str, Enum):
    """Vehicle transmission types."""
    MANUAL = "Manual"
    AUTOMATIC = "Automatic"
    CVT = "CVT"
    AMT = "AMT"
    DSG = "DSG"


class DriveType(str, Enum):
    """Vehicle drive types."""
    FWD = "FWD"
    RWD = "RWD"
    AWD = "AWD"
    _4WD = "4WD"
    _2WD = "2WD"


class BodyType(str, Enum):
    """Vehicle body types."""
    SUV = "SUV"
    SEDAN = "Sedan"
    HATCHBACK = "Hatchback"
    STATION_WAGON = "Station Wagon"
    DOUBLE_CAB = "Double Cab"
    SINGLE_CAB = "Single Cab"
    PICKUP = "Pickup"
    VAN = "Van"
    MINIBUS = "Minibus"
    BUS = "Bus"
    TRUCK = "Truck"
    TIPPER = "Tipper"
    TRAILER = "Trailer"
    COUPE = "Coupe"
    CONVERTIBLE = "Convertible"
    CROSSOVER = "Crossover"


# ================================================================
# SCRAPED LISTING SCHEMA
# ================================================================

class ScrapedListing(BaseModel):
    """Schema for a scraped vehicle listing."""
    
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "listing_id": "123456789",
                "title": "Toyota Land Cruiser Prado 2020",
                "url": "https://jiji.co.ke/cars/toyota-land-cruiser-prado-2020",
                "price": 8500000,
                "currency": "KES",
                "make": "Toyota",
                "model": "Land Cruiser Prado",
                "variant": "VX",
                "year": 2020,
                "mileage": 45000,
                "engine_size": 4.0,
                "engine_code": "1KD",
                "fuel_type": "Diesel",
                "transmission": "Automatic",
                "drive_type": "4WD",
                "body_type": "SUV",
                "color": "White",
                "condition": "Used",
                "description": "Well maintained Toyota Land Cruiser Prado",
                "seller_name": "Auto World Ltd",
                "seller_phone": "+254712345678",
                "seller_type": "Dealer",
                "location": "Nairobi",
                "images": [
                    "https://jiji.co.ke/images/car1.jpg",
                    "https://jiji.co.ke/images/car2.jpg"
                ],
                "scraped_at": "2026-01-15T10:30:00Z"
            }
        }
    )
    
    listing_id: str = Field(
        ...,
        description="Unique listing identifier",
        min_length=1,
        max_length=100
    )
    title: str = Field(
        ...,
        description="Vehicle listing title",
        min_length=1,
        max_length=500
    )
    url: str = Field(
        ...,
        description="Full listing URL",
        max_length=1000
    )
    
    price: Optional[int] = Field(
        None,
        description="Vehicle price in KES",
        ge=0
    )
    currency: str = Field(
        default="KES",
        description="Currency code",
        max_length=10
    )
    
    make: Optional[str] = Field(
        None,
        description="Vehicle make",
        max_length=100
    )
    model: Optional[str] = Field(
        None,
        description="Vehicle model",
        max_length=100
    )
    variant: Optional[str] = Field(
        None,
        description="Vehicle variant/trim",
        max_length=100
    )
    
    year: Optional[int] = Field(
        None,
        description="Year of manufacture",
        ge=1900,
        le=datetime.now(timezone.utc).year + 1
    )
    mileage: Optional[int] = Field(
        None,
        description="Odometer reading in km",
        ge=0
    )
    
    engine_size: Optional[float] = Field(
        None,
        description="Engine size in litres",
        ge=0
    )
    engine_code: Optional[str] = Field(
        None,
        description="Engine code (e.g., 1KD, 2TR)",
        max_length=20
    )
    fuel_type: Optional[str] = Field(
        None,
        description="Fuel type",
        max_length=50
    )
    transmission: Optional[str] = Field(
        None,
        description="Transmission type",
        max_length=50
    )
    drive_type: Optional[str] = Field(
        None,
        description="Drive type (2WD, 4WD, AWD, FWD, RWD)",
        max_length=10
    )
    body_type: Optional[str] = Field(
        None,
        description="Vehicle body type",
        max_length=50
    )
    color: Optional[str] = Field(
        None,
        description="Vehicle color",
        max_length=50
    )
    
    condition: Optional[str] = Field(
        None,
        description="Vehicle condition (New, Used, Certified Pre-Owned)",
        max_length=50
    )
    description: Optional[str] = Field(
        None,
        description="Vehicle description",
        max_length=5000
    )
    
    seller_name: Optional[str] = Field(
        None,
        description="Seller name",
        max_length=200
    )
    seller_phone: Optional[str] = Field(
        None,
        description="Seller phone number",
        max_length=20
    )
    seller_type: Optional[str] = Field(
        None,
        description="Seller type (Dealer, Private)",
        max_length=50
    )
    
    location: Optional[str] = Field(
        None,
        description="Vehicle location",
        max_length=255
    )
    
    images: List[str] = Field(
        default_factory=list,
        description="List of image URLs",
        max_length=20
    )
    
    scraped_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when scraped"
    )


# ================================================================
# SCRAPER RESULT SCHEMA
# ================================================================

class ScraperResult(BaseModel):
    """Schema for scraper execution result."""
    
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )
    
    source: str = Field(
        ...,
        description="Scraper source name",
        examples=["jiji", "cheki", "autochek", "beepbeep"]
    )
    status: str = Field(
        ...,
        description="Execution status",
        examples=["success", "failed", "partial"]
    )
    
    listings_found: int = Field(
        default=0,
        description="Total listings found",
        ge=0
    )
    listings_saved: int = Field(
        default=0,
        description="Total listings saved",
        ge=0
    )
    duplicates_skipped: int = Field(
        default=0,
        description="Duplicates skipped",
        ge=0
    )
    failed_urls: int = Field(
        default=0,
        description="Failed URLs",
        ge=0
    )
    
    pages_scraped: int = Field(
        default=0,
        description="Pages successfully scraped",
        ge=0
    )
    pages_failed: int = Field(
        default=0,
        description="Pages that failed",
        ge=0
    )
    
    listings: List[ScrapedListing] = Field(
        default_factory=list,
        description="Scraped listings"
    )
    
    error: Optional[str] = Field(
        None,
        description="Error message if failed",
        max_length=500
    )
    
    completed_at: Optional[datetime] = Field(
        None,
        description="UTC timestamp when completed"
    )
    duration_seconds: float = Field(
        default=0,
        description="Duration in seconds",
        ge=0
    )


# ================================================================
# RUN REQUEST
# ================================================================

class ScraperRunRequest(BaseModel):
    """
    Start scraper job request.
    """
    
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "source": "all",
                "pages": 3,
                "limit_per_page": 20,
                "parallel": True,
                "max_concurrent": 4
            }
        }
    )
    
    source: ScraperSource = Field(
        default=ScraperSource.ALL,
        description="Scraper source to run"
    )
    
    pages: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of pages to scrape"
    )
    
    limit_per_page: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Listings per page"
    )
    
    parallel: bool = Field(
        default=True,
        description="Run scrapers in parallel"
    )
    
    max_concurrent: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Maximum concurrent scrapers"
    )


# ================================================================
# RUN RESPONSE
# ================================================================

class ScraperRunResponse(BaseModel):
    """
    Response after starting a scraper job.
    """
    
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "job_id": 12345,
                "source": "jiji",
                "status": "running",
                "message": "Scraper job started successfully"
            }
        }
    )
    
    job_id: int = Field(
        ...,
        description="Job ID",
        example=12345
    )
    source: str = Field(
        ...,
        description="Scraper source",
        example="jiji"
    )
    status: JobStatus = Field(
        ...,
        description="Job status"
    )
    message: str = Field(
        ...,
        description="Status message",
        example="Scraper job started successfully"
    )


# ================================================================
# JOB RESPONSE
# ================================================================

class ScraperJobResponse(BaseModel):
    """
    Detailed scraper job response.
    """
    
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "id": 12345,
                "source": "jiji",
                "status": "completed",
                "started_at": "2026-01-15T10:00:00Z",
                "completed_at": "2026-01-15T10:05:00Z",
                "duration_seconds": 300.5,
                "pages_requested": 3,
                "pages_completed": 3,
                "listings_found": 65,
                "listings_saved": 60,
                "duplicates_skipped": 12,
                "failed_urls": 2,
                "progress": 100,
                "error": None,
                "result": None
            }
        }
    )
    
    id: int = Field(
        ...,
        description="Job ID",
        example=12345
    )
    source: str = Field(
        ...,
        description="Scraper source",
        example="jiji"
    )
    status: JobStatus = Field(
        ...,
        description="Job status"
    )
    
    started_at: datetime = Field(
        ...,
        description="UTC timestamp when job started"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="UTC timestamp when job completed"
    )
    duration_seconds: float = Field(
        default=0,
        description="Duration in seconds",
        ge=0
    )
    
    pages_requested: int = Field(
        default=0,
        description="Number of pages requested",
        ge=0
    )
    pages_completed: int = Field(
        default=0,
        description="Number of pages completed",
        ge=0
    )
    
    listings_found: int = Field(
        default=0,
        description="Total listings found",
        ge=0
    )
    listings_saved: int = Field(
        default=0,
        description="Total listings saved",
        ge=0
    )
    duplicates_skipped: int = Field(
        default=0,
        description="Duplicates skipped",
        ge=0
    )
    failed_urls: int = Field(
        default=0,
        description="Failed URLs",
        ge=0
    )
    
    progress: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Progress percentage"
    )
    
    error: Optional[str] = Field(
        None,
        description="Error message if failed",
        max_length=500
    )
    
    result: Optional[ScraperResult] = Field(
        None,
        description="Scraper result if completed"
    )


# ================================================================
# STATUS RESPONSE
# ================================================================

class ScraperStatusResponse(BaseModel):
    """
    Current scraper system status.
    """
    
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "is_running": True,
                "queue_size": 3,
                "active_workers": 2,
                "running_jobs": ["jiji", "cheki"],
                "last_job_id": 12344,
                "last_success": "2026-01-15T10:00:00Z",
                "sources": ["jiji", "cheki", "autochek", "beepbeep"],
                "jobs_total": 150,
                "jobs_pending": 5,
                "jobs_running": 2,
                "jobs_completed": 140,
                "jobs_failed": 3
            }
        }
    )
    
    is_running: bool = Field(
        default=False,
        description="Whether a scraper is currently running"
    )
    queue_size: int = Field(
        default=0,
        description="Number of jobs in queue",
        ge=0
    )
    active_workers: int = Field(
        default=0,
        description="Number of active workers",
        ge=0
    )
    running_jobs: List[str] = Field(
        default_factory=list,
        description="Currently running jobs"
    )
    
    last_job_id: Optional[int] = Field(
        None,
        description="Last job ID"
    )
    last_success: Optional[datetime] = Field(
        None,
        description="UTC timestamp of last successful run"
    )
    
    sources: List[str] = Field(
        default_factory=list,
        description="Available sources"
    )
    
    jobs_total: int = Field(
        default=0,
        description="Total jobs",
        ge=0
    )
    jobs_pending: int = Field(
        default=0,
        description="Pending jobs",
        ge=0
    )
    jobs_running: int = Field(
        default=0,
        description="Running jobs",
        ge=0
    )
    jobs_completed: int = Field(
        default=0,
        description="Completed jobs",
        ge=0
    )
    jobs_failed: int = Field(
        default=0,
        description="Failed jobs",
        ge=0
    )


# ================================================================
# SOURCES RESPONSE
# ================================================================

class ScraperSourceResponse(BaseModel):
    """
    Available scraper sources.
    """
    
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "sources": ["jiji", "cheki", "autochek", "beepbeep"],
                "total_sources": 4,
                "active_sources": 4,
                "status": {
                    "jiji": "ready",
                    "cheki": "ready",
                    "autochek": "ready",
                    "beepbeep": "degraded"
                }
            }
        }
    )
    
    sources: List[str] = Field(
        default_factory=list,
        description="List of source names"
    )
    total_sources: int = Field(
        default=0,
        description="Total number of sources",
        ge=0
    )
    active_sources: int = Field(
        default=0,
        description="Active sources",
        ge=0
    )
    status: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of each source"
    )


# ================================================================
# HEALTH RESPONSE
# ================================================================

class ScraperHealthResponse(BaseModel):
    """
    Scraper system health status.
    """
    
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2026-01-15T10:30:00Z",
                "version": "1.0.0",
                "worker": "scraper-worker-1",
                "uptime_seconds": 3600,
                "database_connected": True,
                "scheduler_running": True,
                "last_successful_run": "2026-01-15T10:00:00Z",
                "jobs_pending": 0,
                "jobs_running": 0
            }
        }
    )
    
    status: str = Field(
        ...,
        description="Health status",
        examples=["healthy", "degraded", "unhealthy"]
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of health check"
    )
    version: str = Field(
        default="1.0.0",
        description="Service version"
    )
    worker: str = Field(
        default="scraper-worker",
        description="Worker identifier"
    )
    uptime_seconds: int = Field(
        default=0,
        description="Worker uptime in seconds",
        ge=0
    )
    database_connected: bool = Field(
        default=False,
        description="Database connection status"
    )
    scheduler_running: bool = Field(
        default=False,
        description="Scheduler running status"
    )
    last_successful_run: Optional[datetime] = Field(
        None,
        description="UTC timestamp of last successful run"
    )
    jobs_pending: int = Field(
        default=0,
        description="Pending jobs",
        ge=0
    )
    jobs_running: int = Field(
        default=0,
        description="Running jobs",
        ge=0
    )


# ================================================================
# HISTORY RESPONSE
# ================================================================

class ScraperHistoryResponse(BaseModel):
    """
    Paginated scraper job history.
    """
    
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "jobs": [],
                "total": 150,
                "limit": 20,
                "offset": 0,
                "page": 1,
                "pages": 8,
                "has_next": True,
                "has_previous": False
            }
        }
    )
    
    jobs: List[ScraperJobResponse] = Field(
        default_factory=list,
        description="List of jobs"
    )
    
    total: int = Field(
        default=0,
        description="Total number of jobs",
        ge=0
    )
    limit: int = Field(
        default=20,
        description="Items per page",
        ge=1,
        le=100
    )
    offset: int = Field(
        default=0,
        description="Offset for pagination",
        ge=0
    )
    page: int = Field(
        default=1,
        description="Current page number",
        ge=1
    )
    pages: int = Field(
        default=0,
        description="Total number of pages",
        ge=0
    )
    has_next: bool = Field(
        default=False,
        description="Whether there is a next page"
    )
    has_previous: bool = Field(
        default=False,
        description="Whether there is a previous page"
    )


# ================================================================
# RECOVER REQUEST
# ================================================================

class ScraperRecoverRequest(BaseModel):
    """
    Request to recover stuck jobs.
    """
    
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "max_age_minutes": 60,
                "sources": ["jiji", "cheki"]
            }
        }
    )
    
    max_age_minutes: int = Field(
        default=60,
        ge=5,
        le=1440,
        description="Maximum age in minutes for a job to be considered stuck"
    )
    sources: List[str] = Field(
        default_factory=list,
        description="Specific sources to recover (empty = all)"
    )


# ================================================================
# RECOVER RESPONSE
# ================================================================

class ScraperRecoverResponse(BaseModel):
    """
    Response after recovering stuck jobs.
    """
    
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "status": "success",
                "recovered": 3,
                "total_stuck": 5,
                "recovered_ids": [12345, 12346, 12347],
                "table_used": "scraper_runs"
            }
        }
    )
    
    status: str = Field(
        ...,
        description="Recovery status",
        examples=["success", "failed", "partial"]
    )
    recovered: int = Field(
        default=0,
        description="Number of jobs recovered",
        ge=0
    )
    total_stuck: int = Field(
        default=0,
        description="Total stuck jobs found",
        ge=0
    )
    recovered_ids: List[int] = Field(
        default_factory=list,
        description="IDs of recovered jobs"
    )
    table_used: Optional[str] = Field(
        None,
        description="Table used for recovery"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if failed"
    )


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    # Enums
    "ScraperSource",
    "JobStatus",
    "ScraperCondition",
    "FuelType",
    "TransmissionType",
    "DriveType",
    "BodyType",
    
    # Core schemas
    "ScrapedListing",
    "ScraperResult",
    
    # Request schemas
    "ScraperRunRequest",
    "ScraperRecoverRequest",
    
    # Response schemas
    "ScraperRunResponse",
    "ScraperJobResponse",
    "ScraperStatusResponse",
    "ScraperSourceResponse",
    "ScraperHealthResponse",
    "ScraperHistoryResponse",
    "ScraperRecoverResponse",
]
