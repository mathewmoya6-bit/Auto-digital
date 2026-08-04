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
from app.core.database import get_supabase
from app.core.middleware import setup_middleware

# ─── Import Routers from modules ──────────────────────────────────
# Based on your project structure: app/modules/[module_name]/router.py
from app.modules.auth.router import router as auth_router
from app.modules.vehicles.router import router as vehicles_router
from app.modules.valuation.router import router as valuation_router
from app.modules.ownership.router import router as ownership_router
from app.modules.reports.router import router as reports_router
from app.modules.running_cost.router import router as running_cost_router
from app.modules.admin.router import router as admin_router
from app.modules.mileage.router import router as mileage_router

# ─── Market Router ──────────────────────────────────────────────
try:
    from app.modules.market.router import router as market_router
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
    from app.modules.scraper.router import router as scraper_router
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
    from app.modules.mpesa.router import router as mpesa_router
    MPESA_ROUTER_LOADED = True
    logger_import = logging.getLogger(__name__)
    logger_import.info("✅ M-Pesa router loaded successfully")
except ImportError as e:
    MPESA_ROUTER_LOADED = False
    logger_import = logging.getLogger(__name__)
    logger_import.warning(f"⚠️ M-Pesa router not available: {e}")
    mpesa_router = None

# ─── Notifications Router ────────────────────────────────────────
try:
    from app.modules.notifications.router import router as notifications_router
    NOTIFICATIONS_ROUTER_LOADED = True
    logger_import = logging.getLogger(__name__)
    logger_import.info("✅ Notifications router loaded successfully")
except ImportError as e:
    NOTIFICATIONS_ROUTER_LOADED = False
    logger_import = logging.getLogger(__name__)
    logger_import.warning(f"⚠️ Notifications router not available: {e}")
    notifications_router = None

# ─── Price Alignment Router ─────────────────────────────────────
try:
    from app.modules.price_alignment.router import router as price_alignment_router
    PRICE_ALIGNMENT_LOADED = True
    logger_import = logging.getLogger(__name__)
    logger_import.info("✅ Price Alignment router loaded successfully")
except ImportError as e:
    PRICE_ALIGNMENT_LOADED = False
    logger_import = logging.getLogger(__name__)
    logger_import.warning(f"⚠️ Price Alignment router not available: {e}")
    price_alignment_router = None

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
        supabase = get_supabase()
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
    
    # Check services
    if MARKET_ROUTER_LOADED:
        logger.info("✅ Market services loaded")
    else:
        logger.warning("⚠️ Market services not loaded")
    
    if SCRAPER_ROUTER_LOADED:
        logger.info("✅ Market Scraper loaded")
    else:
        logger.warning("⚠️ Market Scraper not loaded")
    
    if MPESA_ROUTER_LOADED:
        logger.info("✅ M-Pesa services loaded")
    else:
        logger.warning("⚠️ M-Pesa services not loaded")
    
    if PRICE_ALIGNMENT_LOADED:
        logger.info("✅ Price Alignment services loaded")
    else:
        logger.warning("⚠️ Price Alignment services not loaded")
    
    logger.info(f"🔒 CORS Origins: {settings.BACKEND_CORS_ORIGINS}")
    
    # Check database tables
    try:
        supabase = get_supabase()
        response = supabase.table("services").select("count", count="exact").limit(1).execute()
        logger.info(f"✅ Services table found: {response.count} services")
    except Exception as e:
        logger.warning(f"⚠️ Services table not found: {e}")
    
    try:
        supabase = get_supabase()
        response = supabase.table("market_prices").select("count", count="exact").limit(1).execute()
        logger.info(f"✅ Market prices table found: {response.count} records")
    except Exception as e:
        logger.warning(f"⚠️ Market prices table not found: {e}")
    
    # Check mileage table
    try:
        supabase = get_supabase()
        response = supabase.table("mileage_records").select("count", count="exact").limit(1).execute()
        logger.info(f"✅ Mileage records table found: {response.count} records")
    except Exception as e:
        logger.warning(f"⚠️ Mileage records table not found: {e}")
        logger.warning("   Please run the database migration to create the mileage_records table")
    
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


# ─── Setup Middleware (BEFORE CORS) ──────────────────────────────
setup_middleware(app)
logger.info("✅ Middleware configured")


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

# ─── Core Routers (Always Available) ──────────────────────────────
app.include_router(auth_router, prefix=f"{api_prefix}/auth", tags=["Authentication"])
logger.info(f"✅ Auth router registered at {api_prefix}/auth")

app.include_router(vehicles_router, prefix=f"{api_prefix}/vehicles", tags=["Vehicles"])
logger.info(f"✅ Vehicles router registered at {api_prefix}/vehicles")

app.include_router(valuation_router, prefix=f"{api_prefix}/valuation", tags=["Valuation"])
logger.info(f"✅ Valuation router registered at {api_prefix}/valuation")

app.include_router(ownership_router, prefix=f"{api_prefix}/ownership", tags=["Ownership"])
logger.info(f"✅ Ownership router registered at {api_prefix}/ownership")

app.include_router(reports_router, prefix=f"{api_prefix}/reports", tags=["Reports"])
logger.info(f"✅ Reports router registered at {api_prefix}/reports")

app.include_router(admin_router, prefix=f"{api_prefix}/admin", tags=["Admin"])
logger.info(f"✅ Admin router registered at {api_prefix}/admin")

app.include_router(running_cost_router, prefix=f"{api_prefix}/running-cost", tags=["Running Cost"])
logger.info(f"✅ Running Cost router registered at {api_prefix}/running-cost")

app.include_router(mileage_router, prefix=f"{api_prefix}/mileage", tags=["Mileage"])
logger.info(f"✅ Mileage router registered at {api_prefix}/mileage")

logger.info("=" * 40)
logger.info("✅ Core routers registered")

# ─── Market Router ────────────────────────────────────────────────
if MARKET_ROUTER_LOADED and market_router is not None:
    try:
        app.include_router(
            market_router,
            prefix=f"{api_prefix}/market",
            tags=["Market Data"]
        )
        logger.info("✅ Market router registered successfully")
        logger.info(f"   POST {api_prefix}/market/scrape - Scrape market data")
        logger.info(f"   GET  {api_prefix}/market/insights - Get market insights")
        logger.info(f"   GET  {api_prefix}/market/location/factors - Get location factors")
    except Exception as e:
        logger.error(f"❌ Failed to register Market router: {e}")
else:
    logger.warning("⚠️ Market router not loaded")

# ─── Market Scraper Router ───────────────────────────────────────
if SCRAPER_ROUTER_LOADED and scraper_router is not None:
    try:
        app.include_router(
            scraper_router,
            prefix=api_prefix,  # Router has its own /scraper prefix
            tags=["Market Scraper"]
        )
        logger.info("✅ Market Scraper router registered successfully")
        logger.info(f"   POST {api_prefix}/scraper/start - Start scraping")
        logger.info(f"   GET  {api_prefix}/scraper/job/{{job_id}} - Get job status")
        logger.info(f"   GET  {api_prefix}/scraper/jobs - List all jobs")
        logger.info(f"   GET  {api_prefix}/scraper/sources - List data sources")
        logger.info(f"   GET  {api_prefix}/scraper/health - Health check")
    except Exception as e:
        logger.error(f"❌ Failed to register Market Scraper router: {e}")
else:
    logger.warning("⚠️ Market Scraper router not loaded")

# ─── M-Pesa Router ────────────────────────────────────────────────
if MPESA_ROUTER_LOADED and mpesa_router is not None:
    try:
        app.include_router(
            mpesa_router,
            prefix=f"{api_prefix}/mpesa",
            tags=["M-Pesa"]
        )
        logger.info("✅ M-Pesa router registered successfully")
        logger.info(f"   POST {api_prefix}/mpesa/stkpush - Initiate STK Push")
        logger.info(f"   POST {api_prefix}/mpesa/callback - M-Pesa callback")
        logger.info(f"   GET  {api_prefix}/mpesa/status - Check payment status")
        logger.info(f"   GET  {api_prefix}/mpesa/transactions - List transactions")
    except Exception as e:
        logger.error(f"❌ Failed to register M-Pesa router: {e}")
else:
    logger.warning("⚠️ M-Pesa router not loaded")

# ─── Notifications Router ─────────────────────────────────────────
if NOTIFICATIONS_ROUTER_LOADED and notifications_router is not None:
    try:
        app.include_router(
            notifications_router,
            prefix=f"{api_prefix}/notifications",
            tags=["Notifications"]
        )
        logger.info("✅ Notifications router registered successfully")
        logger.info(f"   POST {api_prefix}/notifications/send - Send notification")
        logger.info(f"   GET  {api_prefix}/notifications - List notifications")
        logger.info(f"   GET  {api_prefix}/notifications/{{id}} - Get notification")
        logger.info(f"   PUT  {api_prefix}/notifications/{{id}}/read - Mark as read")
    except Exception as e:
        logger.error(f"❌ Failed to register Notifications router: {e}")
else:
    logger.warning("⚠️ Notifications router not loaded")

# ─── Price Alignment Router ──────────────────────────────────────
if PRICE_ALIGNMENT_LOADED and price_alignment_router is not None:
    try:
        app.include_router(
            price_alignment_router,
            prefix=f"{api_prefix}/price",
            tags=["Price Alignment"]
        )
        logger.info("✅ Price Alignment router registered successfully")
        logger.info(f"   POST {api_prefix}/price/align - Align prices")
        logger.info(f"   POST {api_prefix}/price/analyze - Analyze prices")
        logger.info(f"   GET  {api_prefix}/price/history - Get price history")
        logger.info(f"   GET  {api_prefix}/price/trend - Get price trends")
        logger.info(f"   GET  {api_prefix}/price/comparables - Get comparable vehicles")
    except Exception as e:
        logger.error(f"❌ Failed to register Price Alignment router: {e}")
else:
    logger.warning("⚠️ Price Alignment router not loaded")

logger.info("=" * 40)
logger.info("✅ All routers registered")
logger.info(f"📚 API Documentation available at {settings.API_DOCS_URL}")
logger.info(f"📚 Alternative Docs at {settings.API_REDOC_URL}")
logger.info("=" * 40)


# ─── Health Check Endpoints ──────────────────────────────────────
@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint - Supports both /health and /api/health"""
    supabase_status = "connected"
    try:
        supabase = get_supabase()
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
        "services": {
            "supabase": supabase_status,
            "mpesa": "configured" if mpesa_configured else "not_configured",
            "mpesa_router": MPESA_ROUTER_LOADED,
            "market_router": MARKET_ROUTER_LOADED,
            "scraper_router": SCRAPER_ROUTER_LOADED,
            "notifications_router": NOTIFICATIONS_ROUTER_LOADED,
            "price_alignment_router": PRICE_ALIGNMENT_LOADED,
        },
        "environment": getattr(settings, "ENVIRONMENT", "production"),
        "version": getattr(settings, "API_VERSION", "4.0.0"),
        "docs": {
            "enabled": settings.ENABLE_DOCS,
            "swagger": settings.API_DOCS_URL if settings.ENABLE_DOCS else None,
            "redoc": settings.API_REDOC_URL if settings.ENABLE_DOCS else None,
        }
    }


@app.get("/ready", tags=["Health"])
@app.get("/api/ready", tags=["Health"])
async def readiness_check():
    """Readiness check endpoint"""
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/live", tags=["Health"])
@app.get("/api/live", tags=["Health"])
async def liveness_check():
    """Liveness check endpoint"""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/ping", tags=["Health"])
async def ping():
    """Simple ping endpoint for testing connectivity"""
    return {
        "pong": datetime.utcnow().isoformat(),
        "status": "alive"
    }


@app.get("/", tags=["Info"])
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
        "documentation": {
            "swagger": settings.API_DOCS_URL if settings.ENABLE_DOCS else "disabled",
            "redoc": settings.API_REDOC_URL if settings.ENABLE_DOCS else "disabled",
            "openapi": settings.API_OPENAPI_URL if settings.ENABLE_DOCS else "disabled",
        },
        "api_prefix": getattr(settings, "API_V1_PREFIX", "/api/v1"),
        "features": {
            "mpesa": {
                "enabled": getattr(settings, "ENABLE_MPESA", True),
                "shortcode": getattr(settings, "MPESA_SHORTCODE", "4095377"),
                "configured": mpesa_configured,
                "router_loaded": MPESA_ROUTER_LOADED,
            },
            "market_data": MARKET_ROUTER_LOADED,
            "market_scraper": SCRAPER_ROUTER_LOADED,
            "notifications": NOTIFICATIONS_ROUTER_LOADED,
            "price_alignment": PRICE_ALIGNMENT_LOADED,
            "google_auth": getattr(settings, "ENABLE_GOOGLE_AUTH", True),
            "docs": settings.ENABLE_DOCS
        },
        "endpoints": {
            "auth": f"{api_prefix}/auth",
            "vehicles": f"{api_prefix}/vehicles",
            "valuation": f"{api_prefix}/valuation",
            "ownership": f"{api_prefix}/ownership",
            "reports": f"{api_prefix}/reports",
            "admin": f"{api_prefix}/admin",
            "running_cost": f"{api_prefix}/running-cost",
            "mileage": f"{api_prefix}/mileage",
            "market": f"{api_prefix}/market" if MARKET_ROUTER_LOADED else "unavailable",
            "scraper": f"{api_prefix}/scraper" if SCRAPER_ROUTER_LOADED else "unavailable",
            "mpesa": f"{api_prefix}/mpesa" if MPESA_ROUTER_LOADED else "unavailable",
            "notifications": f"{api_prefix}/notifications" if NOTIFICATIONS_ROUTER_LOADED else "unavailable",
            "price_alignment": f"{api_prefix}/price" if PRICE_ALIGNMENT_LOADED else "unavailable",
        },
        "health": {
            "health": "/health",
            "ready": "/ready",
            "live": "/live",
            "ping": "/ping",
        }
    }


@app.get("/info", tags=["Info"])
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
        "docs": {
            "enabled": settings.ENABLE_DOCS,
            "swagger": settings.API_DOCS_URL if settings.ENABLE_DOCS else None,
            "redoc": settings.API_REDOC_URL if settings.ENABLE_DOCS else None,
        },
        "features": {
            "mpesa": {
                "enabled": getattr(settings, "ENABLE_MPESA", True),
                "shortcode": getattr(settings, "MPESA_SHORTCODE", "4095377"),
                "environment": getattr(settings, "MPESA_ENV", "sandbox"),
                "configured": mpesa_configured,
                "router_loaded": MPESA_ROUTER_LOADED,
            },
            "market_data": MARKET_ROUTER_LOADED,
            "market_scraper": SCRAPER_ROUTER_LOADED,
            "notifications": NOTIFICATIONS_ROUTER_LOADED,
            "price_alignment": PRICE_ALIGNMENT_LOADED,
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


# ─── API Version Endpoint ─────────────────────────────────────────
@app.get("/api/version", tags=["Info"])
async def api_version():
    """Get API version information"""
    return {
        "api_version": settings.API_VERSION,
        "project_name": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
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
    logger.info(f"📊 Market Router Loaded: {MARKET_ROUTER_LOADED}")
    logger.info(f"📊 Market Scraper Loaded: {SCRAPER_ROUTER_LOADED}")
    logger.info(f"📊 Notifications Loaded: {NOTIFICATIONS_ROUTER_LOADED}")
    logger.info(f"📊 Price Alignment Loaded: {PRICE_ALIGNMENT_LOADED}")
    logger.info(f"📡 API Base URL: {getattr(settings, 'API_BASE_URL', 'http://localhost:' + str(port))}")
    logger.info(f"📚 Docs enabled: {settings.ENABLE_DOCS}")
    if settings.ENABLE_DOCS:
        logger.info(f"📚 Swagger Docs: {settings.API_DOCS_URL}")
        logger.info(f"📚 ReDoc Docs: {settings.API_REDOC_URL}")
    logger.info("=" * 60)
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="debug" if debug else "info",
        access_log=True,
    )
