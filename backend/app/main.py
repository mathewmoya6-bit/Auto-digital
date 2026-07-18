# backend/app/main.py
"""
Auto-D Kenya - FastAPI Application
Vehicle cost analysis and valuation system
"""

import os
import sys
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.database import supabase

# Import routers directly from their modules
from app.api.v1.auth import router as auth_router
from app.api.v1.vehicles import router as vehicles_router
from app.api.v1.valuation import router as valuation_router
from app.api.v1.mileage import router as mileage_router
from app.api.v1.ownership import router as ownership_router
from app.api.v1.fuel import router as fuel_router
from app.api.v1.admin import router as admin_router
from app.api.v1.reports import router as reports_router
from app.api.v1.running_cost import router as running_cost_router

# ─── Configure Logging ─────────────────────────────────────────────
# Safely get log level from settings with fallback
try:
    log_level_name = getattr(settings, "LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
except Exception:
    log_level = logging.INFO

# Get log format from settings or use default
log_format = getattr(settings, "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Log startup info
logger.info("=" * 60)
logger.info("🚀 Auto-D Kenya API Starting...")
logger.info(f"📋 Log Level: {logging.getLevelName(log_level)}")
logger.info("=" * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    logger.info(f"🚀 Starting {settings.PROJECT_NAME}...")
    logger.info(f"📍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔗 Supabase URL: {settings.SUPABASE_URL}")
    
    # Check Supabase connection
    try:
        response = supabase.table("vehicle_makes").select("count", count="exact").limit(1).execute()
        logger.info("✅ Supabase connection successful")
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {e}")
    
    yield
    
    logger.info(f"🛑 Shutting down {settings.PROJECT_NAME}...")


# Initialize FastAPI app
app = FastAPI(
    title=getattr(settings, "PROJECT_NAME", "Auto-D Kenya API"),
    description="Vehicle cost analysis and valuation system for Kenya",
    version=getattr(settings, "API_VERSION", "4.0.0"),
    docs_url=getattr(settings, "API_DOCS_URL", "/docs") if getattr(settings, "ENABLE_DOCS", False) else None,
    redoc_url=getattr(settings, "API_REDOC_URL", "/redoc") if getattr(settings, "ENABLE_DOCS", False) else None,
    lifespan=lifespan,
)

# ─── CORS Configuration ────────────────────────────────────────────
# Safely get CORS origins
try:
    cors_origins = settings.BACKEND_CORS_ORIGINS
except Exception:
    cors_origins = ["*"]

# Handle both list and string formats
if isinstance(cors_origins, str):
    import json
    try:
        cors_origins = json.loads(cors_origins)
    except json.JSONDecodeError:
        cors_origins = [origin.strip() for origin in cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=getattr(settings, "CORS_ALLOW_CREDENTIALS", True),
    allow_methods=getattr(settings, "CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS,PATCH"),
    allow_headers=getattr(settings, "CORS_ALLOW_HEADERS", "Authorization,Content-Type,Accept,Origin,X-Requested-With"),
    max_age=getattr(settings, "CORS_MAX_AGE", 86400),
)


# ─── Exception Handlers ────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "message": "Validation error",
            "errors": exc.errors(),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ─── Include Routers ───────────────────────────────────────────────
api_prefix = getattr(settings, "API_V1_PREFIX", "/api/v1")

app.include_router(auth_router, prefix=api_prefix + "/auth", tags=["Authentication"])
app.include_router(vehicles_router, prefix=api_prefix + "/vehicles", tags=["Vehicles"])
app.include_router(valuation_router, prefix=api_prefix + "/valuation", tags=["Valuation"])
app.include_router(mileage_router, prefix=api_prefix + "/mileage", tags=["Mileage"])
app.include_router(ownership_router, prefix=api_prefix + "/ownership", tags=["Ownership"])
app.include_router(running_cost_router, prefix=api_prefix + "/running-cost", tags=["Running Cost"])
app.include_router(fuel_router, prefix=api_prefix + "/fuel", tags=["Fuel"])
app.include_router(admin_router, prefix=api_prefix + "/admin", tags=["Admin"])
app.include_router(reports_router, prefix=api_prefix + "/reports", tags=["Reports"])

logger.info("✅ All routers registered")


# ─── Root Endpoints ────────────────────────────────────────────────
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": getattr(settings, "PROJECT_NAME", "Auto-D Kenya API"),
        "version": getattr(settings, "API_VERSION", "4.0.0"),
        "environment": getattr(settings, "ENVIRONMENT", "production"),
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "supabase": "connected"
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/live")
async def liveness_check():
    """Liveness check endpoint"""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


# ─── Main Entry Point ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    debug = getattr(settings, "DEBUG", False)
    
    logger.info(f"🚀 Starting server on port {port}")
    logger.info(f"🐛 Debug mode: {debug}")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug",
    )
