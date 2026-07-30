# app/modules/scraper/schemas.py
# Auto-D Kenya - Scraper Schemas
# ================================================================
# TYPE: MODULE - Scraper Pydantic schemas

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ScraperRunRequest(BaseModel):
    source: str = Field("all", description="Source to scrape (all, jiji, cheki, autochek)")
    pages: int = Field(3, ge=1, le=10, description="Number of pages to scrape")
    limit_per_page: int = Field(20, ge=1, le=50, description="Items per page")


class ScraperRunResponse(BaseModel):
    job_id: str
    source: str
    status: str
    message: str


class ScraperStatusResponse(BaseModel):
    is_running: bool
    last_run: Optional[str] = None
    current_job: Optional[str] = None
    jobs: int
    sources: List[str]


class ScraperSourceResponse(BaseModel):
    sources: List[str]
    status: Dict[str, Any]
    total_sources: int


class ScraperHealthResponse(BaseModel):
    status: str
    timestamp: str
    worker: str
    jobs_pending: int
    jobs_running: int


class ScraperJobResponse(BaseModel):
    id: str
    source: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    listings_found: Optional[int] = 0
    listings_saved: Optional[int] = 0
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class ScraperHistoryResponse(BaseModel):
    jobs: List[ScraperJobResponse]
    total: int
    limit: int
    offset: int
