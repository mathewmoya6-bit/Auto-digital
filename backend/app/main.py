"""
Auto-D Kenya - FastAPI Application
Vehicle cost analysis and valuation system
"""

import os
import sys
import json
import logging
import traceback
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.database import supabase

# ─── Configure Logging FIRST ─────────────────────────────────────────
try:
    log_level_name = getattr(settings, "LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
except Exception:
    log_level = logging.INFO

log_format = getattr(settings, "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("🚀 Auto-D Kenya API Starting...")
logger.info(f"📋 Log Level: {logging.getLevelName(log_level)}")
logger.info("=" * 60)


# ─── Import Routers ──────────────────────────────────────────────────
logger.info("📦 Loading routers...")

# Auth Router
try:
    from app.api.v1.auth import router as auth_router
    AUTH_ROUTER_LOADED = True
    logger.info("✅ Auth router loaded successfully")
except ImportError as e:
    AUTH_ROUTER_LOADED = False
    logger.error(f"❌ Auth router not available: {e}")
    auth_router = None

# Vehicles Router
try:
    from app.api.v1.vehicles import router as vehicles_router
    VEHICLES_ROUTER_LOADED = True
    logger.info("✅ Vehicles router loaded successfully")
except ImportError as e:
    VEHICLES_ROUTER_LOADED = False
    logger.error(f"❌ Vehicles router not available: {e}")
    vehicles_router = None

# Valuation Router
try:
    from app.api.v1.valuation import router as valuation_router
    VALUATION_ROUTER_LOADED = True
    logger.info("✅ Valuation router loaded successfully")
except ImportError as e:
    VALUATION_ROUTER_LOADED = False
    logger.error(f"❌ Valuation router not available: {e}")
    valuation_router = None

# Mileage Router
try:
    from app.api.v1.mileage import router as mileage_router
    MILEAGE_ROUTER_LOADED = True
    logger.info("✅ Mileage router loaded successfully")
except ImportError as e:
    MILEAGE_ROUTER_LOADED = False
    logger.error(f"❌ Mileage router not available: {e}")
    mileage_router = None

# Ownership Router
try:
    from app.api.v1.ownership import router as ownership_router
    OWNERSHIP_ROUTER_LOADED = True
    logger.info("✅ Ownership router loaded successfully")
except ImportError as e:
    OWNERSHIP_ROUTER_LOADED = False
    logger.error(f"❌ Ownership router not available: {e}")
    ownership_router = None

# Fuel Router
try:
    from app.api.v1.fuel import router as fuel_router
    FUEL_ROUTER_LOADED = True
    logger.info("✅ Fuel router loaded successfully")
except ImportError as e:
    FUEL_ROUTER_LOADED = False
    logger.error(f"❌ Fuel router not available: {e}")
    fuel_router = None

# Running Cost Router
try:
    from app.api.v1.running_cost import router as running_cost_router
    RUNNING_COST_ROUTER_LOADED = True
    logger.info("✅ Running Cost router loaded successfully")
except ImportError as e:
    RUNNING_COST_ROUTER_LOADED = False
    logger.error(f"❌ Running Cost router not available: {e}")
    running_cost_router = None

# Admin Router
try:
    from app.api.v1.admin import router as admin_router
    ADMIN_ROUTER_LOADED = True
    logger.info("✅ Admin router loaded successfully")
except ImportError as e:
    ADMIN_ROUTER_LOADED = False
    logger.error(f"❌ Admin router not available: {e}")
    admin_router = None

# Reports Router
try:
    from app.api.v1.reports import router as reports_router
    REPORTS_ROUTER_LOADED = True
    logger.info("✅ Reports router loaded successfully")
except ImportError as e:
    REPORTS_ROUTER_LOADED = False
    logger.error(f"❌ Reports router not available: {e}")
    reports_router = None

# Service Prices Router
try:
    from app.api.v1.services import router as services_router
    SERVICES_ROUTER_LOADED = True
    logger.info("✅ Service Prices router loaded successfully")
except ImportError as e:
    SERVICES_ROUTER_LOADED = False
    logger.warning(f"⚠️ Service Prices router not available: {e}")
    services_router = None

# Price Alignment Router
try:
    from app.api.v1.price_alignment import router as price_alignment_router
    PRICE_ALIGNMENT_LOADED = True
    logger.info("✅ Price Alignment router loaded successfully")
except ImportError as e:
    PRICE_ALIGNMENT_LOADED = False
    logger.warning(f"⚠️ Price Alignment router not available: {e}")
    price_alignment_router = None

# Market Router
try:
    from app.api.v1.market import router as market_router
    MARKET_ROUTER_LOADED = True
    logger.info("✅ Market router loaded successfully")
except ImportError as e:
    MARKET_ROUTER_LOADED = False
    logger.warning(f"⚠️ Market router not available: {e}")
    market_router = None

# Scraper Router
try:
    from app.api.v1.scraper import router as scraper_router
    SCRAPER_ROUTER_LOADED = True
    logger.info("✅ Scraper router loaded successfully")
except ImportError as e:
    SCRAPER_ROUTER_LOADED = False
    logger.warning(f"⚠️ Scraper router not available: {e}")
    scraper_router = None

# M-Pesa Router
try:
    from app.api.v1.mpesa import router as mpesa_router
    MPESA_ROUTER_LOADED = True
    logger.info("✅ M-Pesa router loaded successfully")
except ImportError as e:
    MPESA_ROUTER_LOADED = False
    logger.warning(f"⚠️ M-Pesa router not available: {e}")
    mpesa_router = None

logger.info("📦 All routers loaded")
logger.info("=" * 60)


# ─── Custom CORS Middleware ────────────────────────────────────────
class CORSHeaderMiddleware(BaseHTTPMiddleware):
    """Custom middleware to ensure CORS headers are always present"""
    
    async def dispatch(self, request: Request, call_next):
        # Handle preflight OPTIONS requests
        if request.method == "OPTIONS":
            response = JSONResponse(
                status_code=200,
                content={},
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                    "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept, Origin, X-Requested-With",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "86400",
                }
            )
            return response
        
        # Process the request
        response = await call_next(request)
        
        # Ensure CORS headers are present
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, Origin, X-Requested-With"
        
        return response


# ─── Lifespan Context Manager ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    logger.info(f"🚀 Starting {settings.PROJECT_NAME}...")
    logger.info(f"📍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔗 API Base URL: {settings.API_BASE_URL}")
    logger.info(f"🔗 Supabase URL: {settings.SUPABASE_URL}")
    logger.info(f"📱 M-Pesa Environment: {getattr(settings, 'MPESA_ENV', 'sandbox')}")
    logger.info(f"📱 M-Pesa Shortcode: {getattr(settings, 'MPESA_SHORTCODE', '4095377')}")

    # Check Supabase connection
    try:
        response = supabase.table("vehicle_makes").select("count", count="exact").limit(1).execute()
        logger.info("✅ Supabase connection successful")
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {e}")
    
    # Check M-Pesa configuration
    mpesa_configured = bool(
        getattr(settings, 'MPESA_CONSUMER_KEY', '') and 
        getattr(settings, 'MPESA_CONSUMER_SECRET', '') and 
        getattr(settings, 'MPESA_PASSKEY', '')
    )
    if mpesa_configured:
        logger.info("✅ M-Pesa configuration loaded")
    else:
        logger.warning("⚠️ M-Pesa configuration incomplete - payment endpoints may not work")
    
    # Check tables
    try:
        response = supabase.table("service_prices").select("count", count="exact").limit(1).execute()
        count = response.count if hasattr(response, 'count') else 0
        logger.info(f"✅ Service prices table found: {count} services")
    except Exception as e:
        logger.warning(f"⚠️ Service prices table not found: {e}")
    
    try:
        response = supabase.table("market_prices").select("count", count="exact").limit(1).execute()
        count = response.count if hasattr(response, 'count') else 0
        logger.info(f"✅ Market prices table found: {count} records")
    except Exception as e:
        logger.warning(f"⚠️ Market prices table not found: {e}")
    
    try:
        response = supabase.table("fuel_prices").select("count", count="exact").limit(1).execute()
        count = response.count if hasattr(response, 'count') else 0
        logger.info(f"✅ Fuel prices table found: {count} records")
    except Exception as e:
        logger.warning(f"⚠️ Fuel prices table not found: {e}")
    
    logger.info("=" * 60)
    logger.info("✅ Application is ready to serve requests")
    logger.info("=" * 60)
    
    yield
    
    logger.info(f"🛑 Shutting down {settings.PROJECT_NAME}...")


# ─── Initialize FastAPI App ────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.SWAGGER_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url=settings.API_DOCS_URL if settings.ENABLE_DOCS else None,
    redoc_url=settings.API_REDOC_URL if settings.ENABLE_DOCS else None,
    openapi_url=settings.API_OPENAPI_URL if settings.ENABLE_DOCS else None,
    contact={
        "name": settings.SWAGGER_CONTACT_NAME,
        "email": settings.SWAGGER_CONTACT_EMAIL,
    },
    license_info={
        "name": settings.SWAGGER_LICENSE_NAME,
    },
    lifespan=lifespan,
)


# ─── CORS Configuration ────────────────────────────────────────────
# Get CORS origins from settings
cors_origins = settings.get_cors_origins() if hasattr(settings, 'get_cors_origins') else settings.BACKEND_CORS_ORIGINS

logger.info(f"🔒 Configuring CORS with origins: {cors_origins}")

# 1. Add CORSMiddleware from FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["*"],
    max_age=settings.CORS_MAX_AGE,
)

# 2. Add custom middleware to ensure CORS headers
app.add_middleware(CORSHeaderMiddleware)

logger.info("✅ CORS configured successfully")


# ─── Exception Handlers ────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.warning(f"Validation error: {exc.errors()}")
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

# Only include routers that loaded successfully
if AUTH_ROUTER_LOADED and auth_router is not None:
    app.include_router(auth_router, prefix=f"{api_prefix}/auth", tags=["Authentication"])
    logger.info("✅ Auth router registered")

if VEHICLES_ROUTER_LOADED and vehicles_router is not None:
    app.include_router(vehicles_router, prefix=f"{api_prefix}/vehicles", tags=["Vehicles"])
    logger.info("✅ Vehicles router registered")

if VALUATION_ROUTER_LOADED and valuation_router is not None:
    app.include_router(valuation_router, prefix=f"{api_prefix}/valuation", tags=["Valuation"])
    logger.info("✅ Valuation router registered")

if MILEAGE_ROUTER_LOADED and mileage_router is not None:
    app.include_router(mileage_router, prefix=f"{api_prefix}/mileage", tags=["Mileage"])
    logger.info("✅ Mileage router registered")

if RUNNING_COST_ROUTER_LOADED and running_cost_router is not None:
    app.include_router(running_cost_router, prefix=f"{api_prefix}/running-cost", tags=["Running Cost"])
    logger.info("✅ Running Cost router registered")

if OWNERSHIP_ROUTER_LOADED and ownership_router is not None:
    app.include_router(ownership_router, prefix=f"{api_prefix}/ownership", tags=["Ownership"])
    logger.info("✅ Ownership router registered")

if FUEL_ROUTER_LOADED and fuel_router is not None:
    app.include_router(fuel_router, prefix=f"{api_prefix}/fuel", tags=["Fuel"])
    logger.info("✅ Fuel router registered")

if ADMIN_ROUTER_LOADED and admin_router is not None:
    app.include_router(admin_router, prefix=f"{api_prefix}/admin", tags=["Admin"])
    logger.info("✅ Admin router registered")

if REPORTS_ROUTER_LOADED and reports_router is not None:
    app.include_router(reports_router, prefix=f"{api_prefix}/reports", tags=["Reports"])
    logger.info("✅ Reports router registered")

if SERVICES_ROUTER_LOADED and services_router is not None:
    app.include_router(services_router, prefix=f"{api_prefix}/services", tags=["Service Prices"])
    logger.info("✅ Service Prices router registered")

if PRICE_ALIGNMENT_LOADED and price_alignment_router is not None:
    app.include_router(price_alignment_router, prefix=f"{api_prefix}/price", tags=["Price Alignment"])
    logger.info("✅ Price Alignment router registered")

if MARKET_ROUTER_LOADED and market_router is not None:
    app.include_router(market_router, prefix=f"{api_prefix}/market", tags=["Market Data"])
    logger.info("✅ Market router registered")

if SCRAPER_ROUTER_LOADED and scraper_router is not None:
    app.include_router(scraper_router, prefix=f"{api_prefix}/scraper", tags=["Market Scraper"])
    logger.info("✅ Scraper router registered")

if MPESA_ROUTER_LOADED and mpesa_router is not None:
    app.include_router(mpesa_router, prefix=f"{api_prefix}/mpesa", tags=["M-Pesa"])
    logger.info("✅ M-Pesa router registered")

logger.info("✅ All routers registered")
logger.info(f"📚 API Documentation available at {settings.API_DOCS_URL}")


# ─── Health Check Endpoints ──────────────────────────────────────
@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    supabase_status = "connected"
    try:
        response = supabase.table("vehicle_makes").select("count", count="exact").limit(1).execute()
    except Exception as e:
        supabase_status = f"error: {str(e)}"
        logger.error(f"Supabase health check failed: {e}")
    
    mpesa_configured = all([
        getattr(settings, "MPESA_CONSUMER_KEY", ""),
        getattr(settings, "MPESA_CONSUMER_SECRET", ""),
        getattr(settings, "MPESA_PASSKEY", "")
    ])
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "supabase": supabase_status,
        "mpesa": "configured" if mpesa_configured else "not_configured",
        "mpesa_router_loaded": MPESA_ROUTER_LOADED,
        "mpesa_shortcode": getattr(settings, "MPESA_SHORTCODE", "4095377"),
        "price_alignment_loaded": PRICE_ALIGNMENT_LOADED,
        "market_router_loaded": MARKET_ROUTER_LOADED,
        "scraper_loaded": SCRAPER_ROUTER_LOADED,
        "services_router_loaded": SERVICES_ROUTER_LOADED,
        "environment": getattr(settings, "ENVIRONMENT", "production"),
        "version": getattr(settings, "API_VERSION", "4.0.0"),
        "docs_enabled": settings.ENABLE_DOCS,
        "docs_url": settings.API_DOCS_URL if settings.ENABLE_DOCS else None,
        "data_sources": ["Jiji", "Cheki", "Autochek", "BeepBeep", "PigiaMe"] if PRICE_ALIGNMENT_LOADED else []
    }


@app.get("/ready")
@app.get("/api/ready")
async def readiness_check():
    """Readiness check endpoint"""
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/live")
@app.get("/api/live")
async def liveness_check():
    """Liveness check endpoint"""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return {
        "pong": datetime.utcnow().isoformat(),
        "status": "alive"
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    mpesa_configured = all([
        getattr(settings, "MPESA_CONSUMER_KEY", ""),
        getattr(settings, "MPESA_CONSUMER_SECRET", ""),
        getattr(settings, "MPESA_PASSKEY", "")
    ])
    
    return {
        "name": getattr(settings, "PROJECT_NAME", "Auto-D Kenya API"),
        "version": getattr(settings, "API_VERSION", "4.0.0"),
        "environment": getattr(settings, "ENVIRONMENT", "production"),
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "documentation": settings.API_DOCS_URL if settings.ENABLE_DOCS else "disabled",
        "api_prefix": getattr(settings, "API_V1_PREFIX", "/api/v1"),
        "data_sources": ["Jiji", "Cheki", "Autochek", "BeepBeep", "PigiaMe"] if PRICE_ALIGNMENT_LOADED else [],
        "features": {
            "mpesa": getattr(settings, "ENABLE_MPESA", True),
            "mpesa_shortcode": getattr(settings, "MPESA_SHORTCODE", "4095377"),
            "mpesa_configured": mpesa_configured,
            "mpesa_router_loaded": MPESA_ROUTER_LOADED,
            "price_alignment": PRICE_ALIGNMENT_LOADED,
            "market_data": MARKET_ROUTER_LOADED,
            "market_scraper": SCRAPER_ROUTER_LOADED,
            "service_prices": SERVICES_ROUTER_LOADED,
            "google_auth": getattr(settings, "ENABLE_GOOGLE_AUTH", True),
            "docs": settings.ENABLE_DOCS
        },
        "endpoints": {
            "auth": f"{api_prefix}/auth" if AUTH_ROUTER_LOADED else "unavailable",
            "vehicles": f"{api_prefix}/vehicles" if VEHICLES_ROUTER_LOADED else "unavailable",
            "valuation": f"{api_prefix}/valuation" if VALUATION_ROUTER_LOADED else "unavailable",
            "mileage": f"{api_prefix}/mileage" if MILEAGE_ROUTER_LOADED else "unavailable",
            "ownership": f"{api_prefix}/ownership" if OWNERSHIP_ROUTER_LOADED else "unavailable",
            "running_cost": f"{api_prefix}/running-cost" if RUNNING_COST_ROUTER_LOADED else "unavailable",
            "fuel": f"{api_prefix}/fuel" if FUEL_ROUTER_LOADED else "unavailable",
            "services": f"{api_prefix}/services" if SERVICES_ROUTER_LOADED else "unavailable",
            "services_types": f"{api_prefix}/services/types" if SERVICES_ROUTER_LOADED else "unavailable",
            "services_summary": f"{api_prefix}/services/summary/pricing" if SERVICES_ROUTER_LOADED else "unavailable",
            "price_align": f"{api_prefix}/price/align" if PRICE_ALIGNMENT_LOADED else "unavailable",
            "price_analyze": f"{api_prefix}/price/analyze" if PRICE_ALIGNMENT_LOADED else "unavailable",
            "price_history": f"{api_prefix}/price/history" if PRICE_ALIGNMENT_LOADED else "unavailable",
            "market_insights": f"{api_prefix}/market/insights" if MARKET_ROUTER_LOADED else "unavailable",
            "scrape": f"{api_prefix}/market/scrape" if MARKET_ROUTER_LOADED else "unavailable",
            "location_factors": f"{api_prefix}/market/location/factors" if MARKET_ROUTER_LOADED else "unavailable",
            "scraper_run": f"{api_prefix}/scraper/run" if SCRAPER_ROUTER_LOADED else "unavailable",
            "scraper_status": f"{api_prefix}/scraper/status" if SCRAPER_ROUTER_LOADED else "unavailable"
        }
    }


@app.get("/info")
async def info():
    """Get application information"""
    mpesa_configured = all([
        getattr(settings, "MPESA_CONSUMER_KEY", ""),
        getattr(settings, "MPESA_CONSUMER_SECRET", ""),
        getattr(settings, "MPESA_PASSKEY", "")
    ])
    
    return {
        "name": getattr(settings, "PROJECT_NAME", "Auto-D Kenya API"),
        "version": getattr(settings, "API_VERSION", "4.0.0"),
        "environment": getattr(settings, "ENVIRONMENT", "production"),
        "docs_enabled": settings.ENABLE_DOCS,
        "docs_url": settings.API_DOCS_URL if settings.ENABLE_DOCS else None,
        "data_sources": ["Jiji", "Cheki", "Autochek", "BeepBeep", "PigiaMe"] if PRICE_ALIGNMENT_LOADED else [],
        "features": {
            "mpesa": getattr(settings, "ENABLE_MPESA", True),
            "mpesa_shortcode": getattr(settings, "MPESA_SHORTCODE", "4095377"),
            "mpesa_environment": getattr(settings, "MPESA_ENV", "sandbox"),
            "mpesa_configured": mpesa_configured,
            "mpesa_router_loaded": MPESA_ROUTER_LOADED,
            "price_alignment": PRICE_ALIGNMENT_LOADED,
            "market_data": MARKET_ROUTER_LOADED,
            "market_scraper": SCRAPER_ROUTER_LOADED,
            "service_prices": SERVICES_ROUTER_LOADED,
            "google_auth": getattr(settings, "ENABLE_GOOGLE_AUTH", True),
            "analytics": getattr(settings, "ENABLE_ANALYTICS", True),
            "caching": getattr(settings, "ENABLE_CACHING", True),
            "email_notifications": getattr(settings, "ENABLE_EMAIL_NOTIFICATIONS", True),
        },
        "supabase": {
            "url": getattr(settings, "SUPABASE_URL", ""),
            "connected": True
        },
        "timestamp": datetime.utcnow().isoformat()
    }


# ─── Main Entry Point ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    debug = getattr(settings, "DEBUG", False)
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info("=" * 60)
    logger.info(f"🚀 Starting server on {host}:{port}")
    logger.info(f"🐛 Debug mode: {debug}")
    logger.info(f"📱 M-Pesa Shortcode: {getattr(settings, 'MPESA_SHORTCODE', '4095377')}")
    logger.info(f"📡 API Base URL: {getattr(settings, 'API_BASE_URL', 'http://localhost:' + str(port))}")
    logger.info(f"📚 Docs enabled: {settings.ENABLE_DOCS}")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level=log_level_name.lower() if isinstance(log_level_name, str) else "info",
    )
