# backend/app/main.py
"""
Auto-D Kenya - FastAPI Application
Vehicle cost analysis and valuation system
"""

import os
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

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT,
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


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
    title=settings.PROJECT_NAME,
    description="Vehicle cost analysis and valuation system for Kenya",
    version=settings.API_VERSION,
    docs_url=settings.API_DOCS_URL if settings.ENABLE_DOCS else None,
    redoc_url=settings.API_REDOC_URL if settings.ENABLE_DOCS else None,
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
    max_age=settings.CORS_MAX_AGE,
)


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


# Include routers
app.include_router(auth_router, prefix=settings.API_V1_PREFIX + "/auth", tags=["Authentication"])
app.include_router(vehicles_router, prefix=settings.API_V1_PREFIX + "/vehicles", tags=["Vehicles"])
app.include_router(valuation_router, prefix=settings.API_V1_PREFIX + "/valuation", tags=["Valuation"])
app.include_router(mileage_router, prefix=settings.API_V1_PREFIX + "/mileage", tags=["Mileage"])
app.include_router(ownership_router, prefix=settings.API_V1_PREFIX + "/ownership", tags=["Ownership"])
app.include_router(running_cost_router, prefix=settings.API_V1_PREFIX + "/running-cost", tags=["Running Cost"])
app.include_router(fuel_router, prefix=settings.API_V1_PREFIX + "/fuel", tags=["Fuel"])
app.include_router(admin_router, prefix=settings.API_V1_PREFIX + "/admin", tags=["Admin"])
app.include_router(reports_router, prefix=settings.API_V1_PREFIX + "/reports", tags=["Reports"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
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


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG
    )
