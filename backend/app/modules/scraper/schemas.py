# app/modules/scraper/schemas.py
# ================================================================
# Auto-D Kenya - Scraper Schemas
# ================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# RUN REQUEST
# ============================================================

class ScraperRunRequest(BaseModel):
    source: str = Field(
        default="all",
        description="Scraper source (all, jiji, cheki, autochek, beepbeep)",
    )
    pages: int = Field(
        default=3,
        ge=1,
        le=10,
    )
    limit_per_page: int = Field(
        default=20,
        ge=1,
        le=50,
    )


# ============================================================
# RUN RESPONSE
# ============================================================

class ScraperRunResponse(BaseModel):
    job_id: int
    source: str
    status: str
    message: str


# ============================================================
# SCRAPER STATUS
# ============================================================

class ScraperStatusResponse(BaseModel):
    is_running: bool
    last_run: Optional[datetime] = None
    current_job: Optional[int] = None
    jobs: int
    sources: List[str] = Field(default_factory=list)


# ============================================================
# SOURCES
# ============================================================

class ScraperSourceResponse(BaseModel):
    sources: List[str] = Field(default_factory=list)
    status: Dict[str, Any] = Field(default_factory=dict)
    total_sources: int


# ============================================================
# HEALTH
# ============================================================

class ScraperHealthResponse(BaseModel):
    status: str
    timestamp: datetime
    worker: str
    jobs_pending: int
    jobs_running: int


# ============================================================
# JOB
# ============================================================

class ScraperJobResponse(BaseModel):
    id: int
    source: str
    status: str

    started_at: datetime
    completed_at: Optional[datetime] = None

    listings_found: int = 0
    listings_saved: int = 0

    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


# ============================================================
# JOB HISTORY
# ============================================================

class ScraperHistoryResponse(BaseModel):
    jobs: List[ScraperJobResponse] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
