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

# ─── NEW: Service Prices Router ────────────────────────────────────
try:
    from app.api.v1.services import router as services_router
    SERVICES_ROUTER_LOADED = True
    logger_import = logging.getLogger(__name__)
    logger_import.info("✅ Service Prices router loaded successfully")
except ImportError as e:
    SERVICES_ROUTER_LOADED = False
    logger_import = logging.getLogger(__name__)
    logger_import.warning(f"⚠️ Service Prices router not available: {e}")
    services_router = None

# ─── NEW: Price Alignment & Market Scraper Routers ────────────────
try:
    from app.api.v1.price_alignment import router as price_alignment_router
    PRICE_ALIGNMENT_LOADED = True
    logger_import = logging.getLogger(__name__)
    logger_import.info("✅ Price Alignment router loaded successfully")
except ImportError as e:
    PRICE_ALIGNMENT_LOADED = False
    logger_import = logging.getLogger(__name__)
    logger_import.warning(f"⚠️ Price Alignment router not available: {e}")
    price_alignment_router = None

try:
    from app.api.v1.market import router as market_router
    MARKET_ROUTER_LOADED = True
    logger_import = logging.getLogger(__name__)
    logger_import.info("✅ Market router loaded successfully")
except ImportError as e:
    MARKET_ROUTER_LOADED = False
    logger_import = logging.getLogger(__name__)
    logger_import.warning(f"⚠️ Market router not available: {e}")
    market_router = None

# ─── Market Scraper Router ───────────────────────────────────────
try:
    from app.api.v1.scraper import router as scraper_router
    SCRAPER_ROUTER_LOADED = True
    logger_import = logging.getLogger(__name__)
    logger_import.info("✅ Market Scraper router loaded successfully")
except ImportError as e:
    SCRAPER_ROUTER_LOADED = False
    logger_import = logging.getLogger(__name__)
    logger_import.warning(f"⚠️ Market Scraper router not available: {e}")
    scraper_router = None

# ─── M-Pesa Router ────────────────────────────────────────────────
try:
    from app.api.v1.mpesa import router as mpesa_router
    MPESA_ROUTER_LOADED = True
    logger_import = logging.getLogger(__name__)
    logger_import.info("✅ M-Pesa router loaded successfully")
except ImportError as e:
    MPESA_ROUTER_LOADED = False
    logger_import = logging.getLogger(__name__)
    logger_import.warning(f"⚠️ M-Pesa router not available: {e}")
    mpesa_router = None

# ─── Configure Logging ─────────────────────────────────────────────
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
    
    # ─── NEW: Check Service Prices Table ──────────────────────────
    try:
        response = supabase.table("service_prices").select("count", count="exact").limit(1).execute()
        count = response.count if hasattr(response, 'count') else 0
        logger.info(f"✅ Service prices table found: {count} services")
    except Exception as e:
        logger.warning(f"⚠️ Service prices table not found: {e}")
        logger.warning("   Please run the database migration to create the service_prices table")
    
    # ─── Check Price Alignment Services ──────────────────────────
    if PRICE_ALIGNMENT_LOADED:
        logger.info("✅ Price Alignment services loaded")
        logger.info("   Data Sources: Jiji, Cheki, Autochek, BeepBeep, PigiaMe")
    else:
        logger.warning("⚠️ Price Alignment services not loaded")
    
    if MARKET_ROUTER_LOADED:
        logger.info("✅ Market services loaded")
    else:
        logger.warning("⚠️ Market services not loaded")
    
    if SCRAPER_ROUTER_LOADED:
        logger.info("✅ Market Scraper loaded")
    else:
        logger.warning("⚠️ Market Scraper not loaded")
    
    if SERVICES_ROUTER_LOADED:
        logger.info("✅ Service Prices router loaded")
    else:
        logger.warning("⚠️ Service Prices router not loaded")
    
    # ─── Log CORS origins from settings ──────────────────────────
    logger.info(f"🔒 CORS Origins: {settings.BACKEND_CORS_ORIGINS}")
    
    # ─── Check if market_prices table exists ─────────────────────
    try:
        response = supabase.table("market_prices").select("count", count="exact").limit(1).execute()
        count = response.count if hasattr(response, 'count') else 0
        logger.info(f"✅ Market prices table found: {count} records")
    except Exception as e:
        logger.warning(f"⚠️ Market prices table not found: {e}")
        logger.warning("   Please run the database migration to create the market_prices table")
    
    # ─── Check if fuel_prices table exists ───────────────────────
    try:
        response = supabase.table("fuel_prices").select("count", count="exact").limit(1).execute()
        count = response.count if hasattr(response, 'count') else 0
        logger.info(f"✅ Fuel prices table found: {count} records")
    except Exception as e:
        logger.warning(f"⚠️ Fuel prices table not found: {e}")
        logger.warning("   Please run the database migration to create the fuel_prices table")
    
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
cors_origins = settings.BACKEND_CORS_ORIGINS

logger.info(f"🔒 Configuring CORS with origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=settings.CORS_MAX_AGE,
)

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

app.include_router(auth_router, prefix=f"{api_prefix}/auth", tags=["Authentication"])
app.include_router(vehicles_router, prefix=f"{api_prefix}/vehicles", tags=["Vehicles"])
app.include_router(valuation_router, prefix=f"{api_prefix}/valuation", tags=["Valuation"])
app.include_router(mileage_router, prefix=f"{api_prefix}/mileage", tags=["Mileage"])
app.include_router(running_cost_router, prefix=f"{api_prefix}/running-cost", tags=["Running Cost"])
app.include_router(ownership_router, prefix=f"{api_prefix}/ownership", tags=["Ownership"])
app.include_router(fuel_router, prefix=f"{api_prefix}/fuel", tags=["Fuel"])
app.include_router(admin_router, prefix=f"{api_prefix}/admin", tags=["Admin"])
app.include_router(reports_router, prefix=f"{api_prefix}/reports", tags=["Reports"])

# ─── NEW: Include Service Prices Router ──────────────────────────
if SERVICES_ROUTER_LOADED and services_router is not None:
    try:
        app.include_router(
            services_router,
            prefix=f"{api_prefix}/services",
            tags=["Service Prices"]
        )
        logger.info("✅ Service Prices router registered successfully")
        logger.info("   Endpoints:")
        logger.info("      GET    /services - List all services")
        logger.info("      GET    /services/{id} - Get service by ID")
        logger.info("      POST   /services - Create service")
        logger.info("      PUT    /services/{id} - Update service")
        logger.info("      DELETE /services/{id} - Delete service")
        logger.info("      GET    /services/types - Get service types")
        logger.info("      GET    /services/summary/pricing - Pricing summary")
        logger.info("      GET    /services/comparison/types - Compare by type")
        logger.info("      POST   /services/bulk - Bulk create services")
        logger.info("      GET    /services/price-range - Filter by price range")
    except Exception as e:
        logger.error(f"❌ Failed to register Service Prices router: {e}")
else:
    logger.warning("⚠️ Service Prices router not loaded - service endpoints will be unavailable")

# ─── NEW: Include Price Alignment Router ──────────────────────────
if PRICE_ALIGNMENT_LOADED and price_alignment_router is not None:
    try:
        app.include_router(
            price_alignment_router,
            prefix=f"{api_prefix}/price",
            tags=["Price Alignment"]
        )
        logger.info("✅ Price Alignment router registered successfully")
        logger.info("   Endpoints: /price/align, /price/analyze, /price/history, /price/trend")
    except Exception as e:
        logger.error(f"❌ Failed to register Price Alignment router: {e}")
else:
    logger.warning("⚠️ Price Alignment router not loaded - price endpoints will be unavailable")

# ─── NEW: Include Market Router ────────────────────────────────────
if MARKET_ROUTER_LOADED and market_router is not None:
    try:
        app.include_router(
            market_router,
            prefix=f"{api_prefix}/market",
            tags=["Market Data"]
        )
        logger.info("✅ Market router registered successfully")
        logger.info("   Endpoints: /market/scrape, /market/insights, /market/location/factors")
    except Exception as e:
        logger.error(f"❌ Failed to register Market router: {e}")
else:
    logger.warning("⚠️ Market router not loaded - market data endpoints will be unavailable")

# ─── Include Market Scraper Router ───────────────────────────────
if SCRAPER_ROUTER_LOADED and scraper_router is not None:
    try:
        app.include_router(
            scraper_router,
            prefix=f"{api_prefix}/scraper",
            tags=["Market Scraper"]
        )

        logger.info("✅ Market Scraper router registered successfully")
        logger.info("   Endpoints:")
        logger.info("      POST /scraper/run")
        logger.info("      POST /scraper/autochek")
        logger.info("      POST /scraper/jiji")
        logger.info("      POST /scraper/carapi")
        logger.info("      GET  /scraper/status")

    except Exception as e:
        logger.error(f"❌ Failed to register Market Scraper router: {e}")

else:
    logger.warning("⚠️ Market Scraper router not loaded")

# ─── Include M-Pesa router ────────────────────────────────────────
if MPESA_ROUTER_LOADED and mpesa_router is not None:
    try:
        app.include_router(
            mpesa_router,
            prefix=f"{api_prefix}/mpesa",
            tags=["M-Pesa"]
        )
        logger.info("✅ M-Pesa router registered successfully")
    except Exception as e:
        logger.error(f"❌ Failed to register M-Pesa router: {e}")
else:
    logger.warning("⚠️ M-Pesa router not loaded - payment endpoints will be unavailable")

logger.info("✅ All routers registered")
logger.info(f"📚 API Documentation available at {settings.API_DOCS_URL}")


# ─── Health Check Endpoints ──────────────────────────────────────
@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Health check endpoint - Supports both /health and /api/health"""
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
    
    # Check if service_prices exist
    service_prices_exist = False
    service_count = 0
    try:
        response = supabase.table("service_prices").select("count", count="exact").limit(1).execute()
        service_prices_exist = True
        service_count = response.count if hasattr(response, 'count') else 0
    except Exception:
        pass
    
    # Check if market_prices exist
    market_prices_exist = False
    try:
        response = supabase.table("market_prices").select("count", count="exact").limit(1).execute()
        market_prices_exist = True
    except Exception:
        pass
    
    # Check if fuel_prices exist
    fuel_prices_exist = False
    try:
        response = supabase.table("fuel_prices").select("count", count="exact").limit(1).execute()
        fuel_prices_exist = True
    except Exception:
        pass
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "supabase": supabase_status,
        "mpesa": "configured" if mpesa_configured else "not_configured",
        "mpesa_router_loaded": MPESA_ROUTER_LOADED,
        "mpesa_shortcode": getattr(settings, "MPESA_SHORTCODE", "4095377"),
        "service_prices_table": "exists" if service_prices_exist else "not_found",
        "service_count": service_count,
        "market_prices_table": "exists" if market_prices_exist else "not_found",
        "fuel_prices_table": "exists" if fuel_prices_exist else "not_found",
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
    """Simple ping endpoint for testing connectivity"""
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
            "auth": f"{api_prefix}/auth",
            "vehicles": f"{api_prefix}/vehicles",
            "valuation": f"{api_prefix}/valuation",
            "mileage": f"{api_prefix}/mileage",
            "ownership": f"{api_prefix}/ownership",
            "running_cost": f"{api_prefix}/running-cost",
            "fuel": f"{api_prefix}/fuel",
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
    logger.info(f"📱 M-Pesa Router Loaded: {MPESA_ROUTER_LOADED}")
    logger.info(f"📊 Price Alignment Loaded: {PRICE_ALIGNMENT_LOADED}")
    logger.info(f"📊 Market Router Loaded: {MARKET_ROUTER_LOADED}")
    logger.info(f"📊 Market Scraper Loaded: {SCRAPER_ROUTER_LOADED}")
    logger.info(f"📊 Service Prices Router Loaded: {SERVICES_ROUTER_LOADED}")
    logger.info(f"📡 API Base URL: {getattr(settings, 'API_BASE_URL', 'http://localhost:' + str(port))}")
    logger.info(f"📚 Docs enabled: {settings.ENABLE_DOCS}")
   
