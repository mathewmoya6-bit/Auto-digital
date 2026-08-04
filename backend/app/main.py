# main.py
# ================================================================
# Auto-D Kenya - Main Application Entry Point
# ================================================================

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.database import get_supabase, init_db
from app.core.middleware import LoggingMiddleware
from app.modules.scraper.service import ScraperService
from app.modules.scraper.worker import ScraperWorker

# ─── LOGGING ─────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ─── MODELS ─────────────────────────────────────────────────────

class ScraperRunRequest(BaseModel):
    """Request model for running a scraper."""
    source: str = "all"
    pages: int = 3
    limit_per_page: int = 20

class SourceUpdateRequest(BaseModel):
    """Request model for updating a source."""
    name: str
    active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None

class SettingsUpdateRequest(BaseModel):
    """Request model for updating engine settings."""
    key: str
    value: float

# ─── LIFESPAN ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Auto-D Kenya API...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    # Initialize services
    app.state.scraper_service = ScraperService()
    app.state.worker = ScraperWorker()
    
    logger.info("API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Auto-D Kenya API...")

# ─── APP CREATION ─────────────────────────────────────────────

app = FastAPI(
    title="Auto-D Kenya API",
    description="Vehicle scraper and valuation API for the Kenyan car market",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── MIDDLEWARE ───────────────────────────────────────────────

app.add_middleware(LoggingMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── HEALTH ENDPOINTS ────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint.
    """
    service = app.state.scraper_service
    result = await service.health_check()
    
    if result.get("success") and result.get("data", {}).get("status") == "healthy":
        return JSONResponse(
            status_code=200,
            content=result
        )
    else:
        return JSONResponse(
            status_code=503,
            content=result
        )

@app.get("/api/status")
async def get_status():
    """
    Get the current status of the scraper system.
    """
    service = app.state.scraper_service
    return await service.get_status()

# ─── SOURCE ENDPOINTS ─────────────────────────────────────────

@app.get("/api/sources")
async def get_sources():
    """
    Get all available scraper sources.
    """
    service = app.state.scraper_service
    result = await service.get_sources()
    
    return {
        "sources": result.get("sources", []),
        "count": result.get("count", 0)
    }

@app.post("/api/sources")
async def create_source(request: SourceUpdateRequest):
    """
    Create a new scraper source.
    """
    try:
        supabase = get_supabase()
        
        data = {"name": request.name}
        if request.active is not None:
            data["active"] = request.active
        if request.config is not None:
            data["config"] = request.config
        
        response = (
            supabase.table("market_sources")
            .insert(data)
            .execute()
        )
        
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create source")
        
        return {
            "success": True,
            "source": response.data[0]
        }
        
    except Exception as e:
        logger.exception("Failed to create source")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/sources/{source_id}")
async def update_source(source_id: int, request: SourceUpdateRequest):
    """
    Update an existing scraper source.
    """
    try:
        supabase = get_supabase()
        
        data = {}
        if request.active is not None:
            data["active"] = request.active
        if request.config is not None:
            data["config"] = request.config
        
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        response = (
            supabase.table("market_sources")
            .update(data)
            .eq("id", source_id)
            .execute()
        )
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Source not found")
        
        return {
            "success": True,
            "source": response.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update source")
        raise HTTPException(status_code=500, detail=str(e))

# ─── SCRAPER ENDPOINTS ────────────────────────────────────────

@app.post("/api/scraper/run")
async def run_scraper(request: ScraperRunRequest, background_tasks: BackgroundTasks):
    """
    Run the scraper for a specific source or all sources.
    """
    try:
        service = app.state.scraper_service
        
        # Validate source
        valid_sources = service.worker.get_sources()
        if request.source != "all" and request.source not in valid_sources:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source. Available sources: {', '.join(valid_sources)}"
            )
        
        if request.source == "all":
            # Run all scrapers
            logger.info("Running all scrapers")
            result = await service.worker.run_all(
                pages=request.pages,
                limit_per_page=request.limit_per_page
            )
            return {
                "success": True,
                "source": "all",
                "result": result
            }
        else:
            # Run a single scraper
            job_id = await service.start_scraper(
                source=request.source,
                pages=request.pages,
                limit_per_page=request.limit_per_page
            )
            
            # Run in background
            background_tasks.add_task(
                service.run_scraper_background,
                job_id=job_id,
                source=request.source,
                pages=request.pages,
                limit_per_page=request.limit_per_page
            )
            
            return {
                "success": True,
                "job_id": job_id,
                "source": request.source,
                "status": "pending",
                "message": f"Scraper job {job_id} started for {request.source}"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to run scraper")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scraper/jobs")
async def get_job_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get scraper job history with pagination.
    """
    try:
        service = app.state.scraper_service
        return await service.get_job_history(limit=limit, offset=offset)
        
    except Exception as e:
        logger.exception("Failed to get job history")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scraper/jobs/{job_id}")
async def get_job_status(job_id: int):
    """
    Get the status of a specific scraper job.
    """
    try:
        service = app.state.scraper_service
        job = await service.get_job_status(job_id)
        
        if "error" in job:
            raise HTTPException(status_code=404, detail=job["error"])
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get job {job_id} status")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/scraper/jobs/{job_id}")
async def cancel_job(job_id: int):
    """
    Cancel a pending or running scraper job.
    """
    try:
        service = app.state.scraper_service
        job = await service.get_job_status(job_id)
        
        if "error" in job:
            raise HTTPException(status_code=404, detail=job["error"])
        
        # Only pending or running jobs can be cancelled
        if job.get("status") not in ["pending", "running"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job with status: {job.get('status')}"
            )
        
        # Update job status
        supabase = get_supabase()
        response = (
            supabase.table("scraper_jobs")
            .update({
                "status": "cancelled",
                "completed_at": datetime.now(timezone.utc).isoformat()
            })
            .eq("id", job_id)
            .execute()
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "cancelled",
            "message": f"Job {job_id} cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to cancel job {job_id}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── SETTINGS ENDPOINTS ───────────────────────────────────────

@app.get("/api/settings")
async def get_settings():
    """
    Get all engine settings.
    """
    try:
        supabase = get_supabase()
        response = (
            supabase.table("engine_settings")
            .select("*")
            .execute()
        )
        
        return {
            "settings": response.data or []
        }
        
    except Exception as e:
        logger.exception("Failed to get settings")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings/{key}")
async def get_setting(key: str):
    """
    Get a specific engine setting.
    """
    try:
        supabase = get_supabase()
        response = (
            supabase.table("engine_settings")
            .select("*")
            .eq("key", key)
            .execute()
        )
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
        
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get setting '{key}'")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings")
async def create_setting(request: SettingsUpdateRequest):
    """
    Create a new engine setting.
    """
    try:
        supabase = get_supabase()
        
        response = (
            supabase.table("engine_settings")
            .insert({
                "key": request.key,
                "value": request.value
            })
            .execute()
        )
        
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create setting")
        
        return {
            "success": True,
            "setting": response.data[0]
        }
        
    except Exception as e:
        logger.exception("Failed to create setting")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/settings/{key}")
async def update_setting(key: str, request: SettingsUpdateRequest):
    """
    Update an existing engine setting.
    """
    try:
        supabase = get_supabase()
        
        response = (
            supabase.table("engine_settings")
            .update({"value": request.value})
            .eq("key", key)
            .execute()
        )
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
        
        return {
            "success": True,
            "setting": response.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update setting '{key}'")
        raise HTTPException(status_code=500, detail=str(e))

# ─── LISTINGS ENDPOINTS ───────────────────────────────────────

@app.get("/api/listings")
async def get_listings(
    source: Optional[str] = None,
    make: Optional[str] = None,
    model: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    Get vehicle listings with filters.
    """
    try:
        supabase = get_supabase()
        
        # Start building the query
        query = supabase.table("market_listings").select("*")
        
        # Apply filters
        if source:
            # Get source ID first
            source_response = (
                supabase.table("market_sources")
                .select("id")
                .eq("name", source)
                .execute()
            )
            if source_response.data:
                query = query.eq("source_id", source_response.data[0]["id"])
        
        if make:
            query = query.ilike("make", f"%{make}%")
        if model:
            query = query.ilike("model", f"%{model}%")
        if min_price is not None:
            query = query.gte("price", min_price)
        if max_price is not None:
            query = query.lte("price", max_price)
        if min_year is not None:
            query = query.gte("year", min_year)
        if max_year is not None:
            query = query.lte("year", max_year)
        
        # Get total count
        count_response = query.execute()
        total = len(count_response.data) if count_response.data else 0
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        query = query.order("created_at", desc=True)
        
        response = query.execute()
        
        return {
            "listings": response.data or [],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total
        }
        
    except Exception as e:
        logger.exception("Failed to get listings")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/listings/{listing_id}")
async def get_listing(listing_id: str):
    """
    Get a specific listing by ID.
    """
    try:
        supabase = get_supabase()
        response = (
            supabase.table("market_listings")
            .select("*")
            .eq("listing_id", listing_id)
            .execute()
        )
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get listing {listing_id}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── ROOT ──────────────────────────────────────────────────────

@app.get("/")
async def root():
    """
    Root endpoint - API information.
    """
    return {
        "name": "Auto-D Kenya API",
        "version": "1.0.0",
        "description": "Vehicle scraper and valuation API",
        "endpoints": {
            "health": "/api/health",
            "status": "/api/status",
            "sources": "/api/sources",
            "scraper": "/api/scraper/run",
            "jobs": "/api/scraper/jobs",
            "settings": "/api/settings",
            "listings": "/api/listings"
        },
        "documentation": "/docs",
        "redoc": "/redoc"
    }

# ─── ERROR HANDLING ───────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """
    Custom HTTP exception handler.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """
    General exception handler.
    """
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

# ─── RUN SERVER ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info")
    )
