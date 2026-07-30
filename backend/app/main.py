# main.py
# Auto-D Kenya - FastAPI Application Entry Point
# ================================================================
# TYPE: ROUTES - Application entry point and route registration

import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import local modules
from config import settings
from routes import (
    auth_routes,
    vehicle_routes,
    service_routes,
    mpesa_routes,
    valuation_routes,
    running_cost_routes,
    ownership_routes,
    mileage_routes
)

# ─── LOGGING CONFIGURATION ──────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ─── LIFESPAN MANAGER ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"{settings.PROJECT_NAME} starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Base URL: {settings.API_BASE_URL}")
    
    # Initialize database connection
    try:
        from database import get_supabase
        client = get_supabase()
        logger.info("✅ Supabase connection established")
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {str(e)}")
    
    yield
    
    # Shutdown
    logger.info(f"{settings.PROJECT_NAME} shutting down...")


# ─── CREATE FASTAPI APP ──────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="""
    Auto-D Kenya - Vehicle Cost Analysis and Valuation System
    
    ## Features
    - Vehicle Valuation with AI-powered market analysis
    - Running Cost Calculator for trip and 5-year projections
    - Total Ownership Cost with loan amortization
    - Mileage and Fuel Cost Calculator
    - M-Pesa Integration for payments
    - Vehicle Data Scraping from Kenyan marketplaces
    """,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)


# ─── MIDDLEWARE ───────────────────────────────────────────────────

# CORS Middleware - Using helper methods from config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.get_cors_methods(),
    allow_headers=settings.get_cors_headers(),
    expose_headers=["X-Total-Count", "X-Page", "X-Limit"],
    max_age=settings.CORS_MAX_AGE
)


# Trusted Host Middleware (only in production)
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "auto-digital.meipressgroup.com",
            "auto-d.meipressgroup.com",
            "auto-digital.onrender.com",
            "auto-d.onrender.com",
            "localhost",
            "127.0.0.1"
        ]
    )


# ─── EXCEPTION HANDLERS ──────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for all unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ─── HEALTH CHECK ROUTES ─────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Returns the status of the API and its dependencies.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "service": settings.PROJECT_NAME
    }
    
    # Check Supabase connection
    try:
        from database import get_supabase
        client = get_supabase()
        # Test connection with a simple query
        response = client.table("services").select("count").limit(1).execute()
        health_status["supabase"] = "connected"
        health_status["supabase_status"] = "healthy"
    except Exception as e:
        logger.warning(f"Supabase health check failed: {str(e)}")
        health_status["supabase"] = "disconnected"
        health_status["supabase_status"] = "unhealthy"
        health_status["supabase_error"] = str(e)
        health_status["status"] = "degraded"
    
    # Check M-Pesa service
    try:
        from mpesa import MpesaService
        mpesa = MpesaService()
        token = await mpesa._get_access_token()
        health_status["mpesa"] = "connected"
        health_status["mpesa_status"] = "healthy"
    except Exception as e:
        logger.warning(f"M-Pesa health check failed: {str(e)}")
        health_status["mpesa"] = "disconnected"
        health_status["mpesa_status"] = "unhealthy"
        health_status["mpesa_error"] = str(e)
        if health_status["status"] == "healthy":
            health_status["status"] = "degraded"
    
    return health_status


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness check endpoint.
    Indicates whether the API is ready to accept traffic.
    """
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/live", tags=["Health"])
async def liveness_check():
    """
    Liveness check endpoint.
    Indicates whether the API is still running.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint.
    Returns basic API information.
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs" if settings.ENVIRONMENT == "development" else None,
        "api_prefix": settings.API_V1_PREFIX,
        "base_url": settings.API_BASE_URL,
        "endpoints": {
            "auth": f"{settings.API_V1_PREFIX}/login",
            "vehicles": f"{settings.API_V1_PREFIX}/vehicles",
            "services": f"{settings.API_V1_PREFIX}/mpesa/services",
            "valuation": f"{settings.API_V1_PREFIX}/valuation/calculate",
            "running_cost": f"{settings.API_V1_PREFIX}/running-cost/calculate",
            "ownership": f"{settings.API_V1_PREFIX}/ownership/calculate",
            "mileage": f"{settings.API_V1_PREFIX}/mileage/calculate"
        },
        "health": {
            "health": "/health",
            "ready": "/ready",
            "live": "/live"
        }
    }


# ─── REGISTER API ROUTES ──────────────────────────────────────────

# Authentication Routes
app.include_router(
    auth_routes.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Authentication"]
)

# Vehicle Routes
app.include_router(
    vehicle_routes.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Vehicles"]
)

# Service Management Routes
app.include_router(
    service_routes.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Services"]
)

# M-Pesa Payment Routes
app.include_router(
    mpesa_routes.router,
    prefix=settings.API_V1_PREFIX,
    tags=["M-Pesa"]
)

# Valuation Routes
app.include_router(
    valuation_routes.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Valuation"]
)

# Running Cost Routes
app.include_router(
    running_cost_routes.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Running Cost"]
)

# Ownership Cost Routes
app.include_router(
    ownership_routes.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Ownership Cost"]
)

# Mileage Routes
app.include_router(
    mileage_routes.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Mileage"]
)


# ─── STARTUP LOG ──────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"🚀 Starting {settings.PROJECT_NAME}")
    logger.info(f"📡 API Base URL: {settings.API_BASE_URL}")
    logger.info(f"🔧 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔌 Port: {settings.PORT}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
