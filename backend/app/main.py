# app/main.py
# Auto-D Kenya - Application Entry Point
# ================================================================
# TYPE: ROUTES - Main application entry point

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import init_db, get_supabase
from app.core.middleware import setup_middleware
from app.core.exceptions import setup_exception_handlers

# Import module routers
from app.modules.auth.router import router as auth_router
from app.modules.vehicles.router import router as vehicles_router
from app.modules.valuation.router import router as valuation_router
from app.modules.mpesa.router import router as mpesa_router
from app.modules.reports.router import router as reports_router
from app.modules.scraper.router import router as scraper_router
from app.modules.market.router import router as market_router
from app.modules.notifications.router import router as notifications_router
from app.modules.admin.router import router as admin_router

# ─── NEW MODULES ──────────────────────────────────────────────────

# Import new Running Cost and Ownership modules
from app.modules.running_cost.router import router as running_cost_router
from app.modules.ownership.router import router as ownership_router

# ─── LOGGING ──────────────────────────────────────────────────────

logger = logging.getLogger(__name__)


# ─── LIFESPAN MANAGER ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("=" * 60)
    logger.info(f"{settings.PROJECT_NAME} starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Base URL: {settings.API_BASE_URL}")
    logger.info(f"Port: {settings.PORT}")
    logger.info("=" * 60)
    
    # Initialize logging
    try:
        setup_logging()
        logger.info("✅ Logging configured successfully")
    except Exception as e:
        print(f"❌ Logging configuration failed: {str(e)}")
    
    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
    
    yield
    
    # Shutdown
    logger.info(f"{settings.PROJECT_NAME} shutting down...")


# ─── CREATE APP ──────────────────────────────────────────────────

# Always enable docs for debugging
ENABLE_DOCS = True  # Set to False to disable docs

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
    lifespan=lifespan
)


# ─── MIDDLEWARE ──────────────────────────────────────────────────

setup_middleware(app)


# ─── EXCEPTION HANDLERS ──────────────────────────────────────────

setup_exception_handlers(app)


# ─── ROUTES ──────────────────────────────────────────────────────

# Authentication Routes
app.include_router(
    auth_router,
    prefix=settings.API_V1_PREFIX,
    tags=["Authentication"]
)

# Vehicles Routes
app.include_router(
    vehicles_router,
    prefix=settings.API_V1_PREFIX,
    tags=["Vehicles"]
)

# Valuation Routes
app.include_router(
    valuation_router,
    prefix=settings.API_V1_PREFIX,
    tags=["Valuation"]
)

# M-Pesa Payment Routes
app.include_router(
    mpesa_router,
    prefix=settings.API_V1_PREFIX,
    tags=["M-Pesa"]
)

# Reports Routes
app.include_router(
    reports_router,
    prefix=settings.API_V1_PREFIX,
    tags=["Reports"]
)

# Scraper Routes
app.include_router(
    scraper_router,
    prefix=settings.API_V1_PREFIX,
    tags=["Scraper"]
)

# Market Routes
app.include_router(
    market_router,
    prefix=settings.API_V1_PREFIX,
    tags=["Market"]
)

# Notifications Routes
app.include_router(
    notifications_router,
    prefix=settings.API_V1_PREFIX,
    tags=["Notifications"]
)

# Admin Routes
app.include_router(
    admin_router,
    prefix=settings.API_V1_PREFIX,
    tags=["Admin"]
)

# ─── NEW ROUTES ──────────────────────────────────────────────────

# Running Cost Routes (Mileage & Running Cost Calculator)
app.include_router(
    running_cost_router,
    prefix=settings.API_V1_PREFIX,
    tags=["Running Cost"]
)

# Ownership Routes (Total Cost of Ownership - TCO)
app.include_router(
    ownership_router,
    prefix=settings.API_V1_PREFIX,
    tags=["Ownership"]
)


# ─── HEALTH CHECK ENDPOINTS ─────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Returns the status of the API and its dependencies.
    """
    health_status = {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
        "service": settings.PROJECT_NAME,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Check Supabase connection
    try:
        client = get_supabase()
        client.table("services").select("*", count="exact").limit(1).execute()
        health_status["supabase"] = "connected"
    except Exception as e:
        health_status["supabase"] = "disconnected"
        health_status["supabase_error"] = str(e)
        health_status["status"] = "degraded"
    
    return health_status


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness check endpoint.
    Indicates whether the API is ready to accept traffic.
    """
    readiness_status = {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT
    }
    
    # Check all dependencies are ready
    try:
        client = get_supabase()
        client.table("services").select("*", count="exact").limit(1).execute()
        readiness_status["supabase"] = "ready"
    except Exception:
        readiness_status["supabase"] = "not_ready"
        readiness_status["status"] = "not_ready"
    
    return readiness_status


@app.get("/live", tags=["Health"])
async def liveness_check():
    """
    Liveness check endpoint.
    Indicates whether the API is still running.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT
    }


# Also support /api/health for Render.com compatibility
@app.get("/api/health", tags=["Health"])
async def api_health_check():
    """API Health check endpoint (for Render.com compatibility)"""
    return await health_check()


@app.get("/api/ready", tags=["Health"])
async def api_readiness_check():
    """API Readiness check endpoint (for Render.com compatibility)"""
    return await readiness_check()


@app.get("/api/live", tags=["Health"])
async def api_liveness_check():
    """API Liveness check endpoint (for Render.com compatibility)"""
    return await liveness_check()


@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint.
    Returns basic API information and available endpoints.
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "api_prefix": settings.API_V1_PREFIX,
        "base_url": settings.API_BASE_URL,
        "docs_url": f"{settings.API_BASE_URL}/docs" if ENABLE_DOCS else None,
        "endpoints": {
            "auth": {
                "login": f"{settings.API_V1_PREFIX}/login",
                "register": f"{settings.API_V1_PREFIX}/register",
                "logout": f"{settings.API_V1_PREFIX}/logout",
                "me": f"{settings.API_V1_PREFIX}/me"
            },
            "vehicles": {
                "makes": f"{settings.API_V1_PREFIX}/makes",
                "models": f"{settings.API_V1_PREFIX}/models/{{make_id}}",
                "generations": f"{settings.API_V1_PREFIX}/generations/{{model_id}}",
                "variants": f"{settings.API_V1_PREFIX}/variants/{{generation_id}}",
                "variant": f"{settings.API_V1_PREFIX}/variant/{{variant_id}}",
                "vehicles": f"{settings.API_V1_PREFIX}/vehicles",
                "search": f"{settings.API_V1_PREFIX}/search"
            },
            "valuation": {
                "calculate": f"{settings.API_V1_PREFIX}/valuation/calculate",
                "history": f"{settings.API_V1_PREFIX}/valuation/history"
            },
            "mpesa": {
                "stk_push": f"{settings.API_V1_PREFIX}/mpesa/stkpush",
                "status": f"{settings.API_V1_PREFIX}/mpesa/status/{{checkout_request_id}}",
                "confirm": f"{settings.API_V1_PREFIX}/mpesa/confirm/{{checkout_request_id}}",
                "callback": f"{settings.API_V1_PREFIX}/mpesa/callback",
                "payments": f"{settings.API_V1_PREFIX}/mpesa/payments",
                "services": f"{settings.API_V1_PREFIX}/mpesa/services",
                "user_services": f"{settings.API_V1_PREFIX}/mpesa/user/services",
                "health": f"{settings.API_V1_PREFIX}/mpesa/health"
            },
            "reports": {
                "valuation": f"{settings.API_V1_PREFIX}/reports/valuation",
                "running_cost": f"{settings.API_V1_PREFIX}/reports/running-cost",
                "history": f"{settings.API_V1_PREFIX}/reports/history",
                "mileage_rate": f"{settings.API_V1_PREFIX}/reports/mileage-rate",
                "ownership_cost": f"{settings.API_V1_PREFIX}/reports/ownership-cost",
                "fuel_prices": f"{settings.API_V1_PREFIX}/reports/fuel-prices",
                "service_cost": f"{settings.API_V1_PREFIX}/reports/service-cost",
                "comparison": f"{settings.API_V1_PREFIX}/reports/comparison",
                "valuation_history": f"{settings.API_V1_PREFIX}/reports/valuation-history",
                "market_comparison": f"{settings.API_V1_PREFIX}/reports/market-comparison"
            },
            "scraper": {
                "run": f"{settings.API_V1_PREFIX}/scraper/run",
                "status": f"{settings.API_V1_PREFIX}/scraper/status",
                "sources": f"{settings.API_V1_PREFIX}/scraper/sources",
                "health": f"{settings.API_V1_PREFIX}/scraper/health",
                "history": f"{settings.API_V1_PREFIX}/scraper/history"
            },
            "market": {
                "insights": f"{settings.API_V1_PREFIX}/market/insights",
                "prices": f"{settings.API_V1_PREFIX}/market/prices",
                "trends": f"{settings.API_V1_PREFIX}/market/trends",
                "location_factors": f"{settings.API_V1_PREFIX}/market/location/factors",
                "sources": f"{settings.API_V1_PREFIX}/market/sources/status"
            },
            "notifications": {
                "email": f"{settings.API_V1_PREFIX}/notifications/email",
                "sms": f"{settings.API_V1_PREFIX}/notifications/sms",
                "history": f"{settings.API_V1_PREFIX}/notifications/history"
            },
            "admin": {
                "stats": f"{settings.API_V1_PREFIX}/admin/stats",
                "users": f"{settings.API_V1_PREFIX}/admin/users",
                "payments": f"{settings.API_V1_PREFIX}/admin/payments"
            },
            # ─── NEW ENDPOINTS ──────────────────────────────────────
            "running_cost": {
                "calculate": f"{settings.API_V1_PREFIX}/running-cost/calculate",
                "health": f"{settings.API_V1_PREFIX}/running-cost/health"
            },
            "ownership": {
                "calculate": f"{settings.API_V1_PREFIX}/ownership/calculate",
                "health": f"{settings.API_V1_PREFIX}/ownership/health"
            }
        },
        "health": {
            "health": "/health",
            "ready": "/ready",
            "live": "/live",
            "api_health": "/api/health",
            "api_ready": "/api/ready",
            "api_live": "/api/live"
        }
    }


# ─── STARTUP ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.PROJECT_NAME}")
    logger.info(f"📡 API Base URL: {settings.API_BASE_URL}")
    logger.info(f"🔧 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔌 Port: {settings.PORT}")
    logger.info("=" * 60)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
