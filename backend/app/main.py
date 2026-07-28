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


# ─── Helper function to safely import routers ──────────────────────
def load_router(module_path: str, router_name: str = "router"):
    """
    Attempt to import a router from a module.
    If it fails, log the error and raise the exception to stop the app.
    """
    try:
        module = __import__(module_path, fromlist=[router_name])
        router = getattr(module, router_name)
        logger.info(f"✅ Router loaded: {module_path}")
        return router
    except Exception as e:
        logger.error(f"❌ Failed to load router from {module_path}: {e}")
        logger.error(traceback.format_exc())
        raise


# ─── Import Routers using the helper ──────────────────────────────
logger.info("📦 Loading routers...")

try:
    auth_router = load_router("app.api.v1.auth")
    vehicles_router = load_router("app.api.v1.vehicles")
    valuation_router = load_router("app.api.v1.valuation")
    mileage_router = load_router("app.api.v1.mileage")
    ownership_router = load_router("app.api.v1.ownership")
    fuel_router = load_router("app.api.v1.fuel")
    running_cost_router = load_router("app.api.v1.running_cost")
    admin_router = load_router("app.api.v1.admin")
    reports_router = load_router("app.api.v1.reports")
    services_router = load_router("app.api.v1.services")
    price_alignment_router = load_router("app.api.v1.price_alignment")
    market_router = load_router("app.api.v1.market")
    scraper_router = load_router("app.api.v1.scraper")
    mpesa_router = load_router("app.api.v1.mpesa")
    
    logger.info("✅ All routers loaded successfully!")

except Exception as e:
    logger.critical(f"❌ Application failed to start due to router import error: {e}")
    sys.exit(1)


# ─── Custom CORS Middleware ────────────────────────────────────────
class CORSHeaderMiddleware(BaseHTTPMiddleware):
    """Custom middleware to ensure CORS headers are always present"""
    
    async def dispatch(self, request: Request, call_next):
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
        
        response = await call_next(request)
        
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
cors_origins = settings.get_cors_origins() if hasattr(settings, 'get_cors_origins') else settings.BACKEND_CORS_ORIGINS
logger.info(f"🔒 Configuring CORS with origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["*"],
    max_age=settings.CORS_MAX_AGE,
)

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

app.include_router(auth_router, prefix=f"{api_prefix}/auth", tags=["Authentication"])
app.include_router(vehicles_router, prefix=f"{api_prefix}/vehicles", tags=["Vehicles"])
app.include_router(valuation_router, prefix=f"{api_prefix}/valuation", tags=["Valuation"])
app.include_router(mileage_router, prefix=f"{api_prefix}/mileage", tags=["Mileage"])
app.include_router(running_cost_router, prefix=f"{api_prefix}/running-cost", tags=["Running Cost"])
app.include_router(ownership_router, prefix=f"{api_prefix}/ownership", tags=["Ownership"])
app.include_router(fuel_router, prefix=f"{api_prefix}/fuel", tags=["Fuel"])
app.include_router(admin_router, prefix=f"{api_prefix}/admin", tags=["Admin"])
app.include_router(reports_router, prefix=f"{api_prefix}/reports", tags=["Reports"])
app.include_router(services_router, prefix=f"{api_prefix}/services", tags=["Service Prices"])
app.include_router(price_alignment_router, prefix=f"{api_prefix}/price", tags=["Price Alignment"])
app.include_router(market_router, prefix=f"{api_prefix}/market", tags=["Market Data"])
app.include_router(scraper_router, prefix=f"{api_prefix}/scraper", tags=["Market Scraper"])
app.include_router(mpesa_router, prefix=f"{api_prefix}/mpesa", tags=["M-Pesa"])

logger.info("✅ All routers registered successfully")
logger.info(f"📚 API Documentation available at {settings.API_DOCS_URL}")


# ─── Health Check Endpoints ──────────────────────────────────────
@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Health check endpoint - supports both /health and /api/health"""
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
        "mpesa_router_loaded": True,
        "mpesa_shortcode": getattr(settings, "MPESA_SHORTCODE", "4095377"),
        "service_prices_table": "exists" if service_prices_exist else "not_found",
        "service_count": service_count,
        "market_prices_table": "exists" if market_prices_exist else "not_found",
        "fuel_prices_table": "exists" if fuel_prices_exist else "not_found",
        "price_alignment_loaded": True,
        "market_router_loaded": True,
        "scraper_loaded": True,
        "services_router_loaded": True,
        "environment": getattr(settings, "ENVIRONMENT", "production"),
        "version": getattr(settings, "API_VERSION", "4.0.0"),
        "docs_enabled": settings.ENABLE_DOCS,
        "docs_url": settings.API_DOCS_URL if settings.ENABLE_DOCS else None,
        "data_sources": ["Jiji", "Cheki", "Autochek", "BeepBeep", "PigiaMe"]
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
        "data_sources": ["Jiji", "Cheki", "Autochek", "BeepBeep", "PigiaMe"],
        "features": {
            "mpesa": getattr(settings, "ENABLE_MPESA", True),
            "mpesa_shortcode": getattr(settings, "MPESA_SHORTCODE", "4095377"),
            "mpesa_configured": mpesa_configured,
            "mpesa_router_loaded": True,
            "price_alignment": True,
            "market_data": True,
            "market_scraper": True,
            "service_prices": True,
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
            "services": f"{api_prefix}/services",
            "services_types": f"{api_prefix}/services/types",
            "services_summary": f"{api_prefix}/services/summary/pricing",
            "price_align": f"{api_prefix}/price/align",
            "price_analyze": f"{api_prefix}/price/analyze",
            "price_history": f"{api_prefix}/price/history",
            "market_insights": f"{api_prefix}/market/insights",
            "scrape": f"{api_prefix}/market/scrape",
            "location_factors": f"{api_prefix}/market/location/factors",
            "scraper_run": f"{api_prefix}/scraper/run",
            "scraper_status": f"{api_prefix}/scraper/status"
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
        "data_sources": ["Jiji", "Cheki", "Autochek", "BeepBeep", "PigiaMe"],
        "features": {
            "mpesa": getattr(settings, "ENABLE_MPESA", True),
            "mpesa_shortcode": getattr(settings, "MPESA_SHORTCODE", "4095377"),
            "mpesa_environment": getattr(settings, "MPESA_ENV", "sandbox"),
            "mpesa_configured": mpesa_configured,
            "mpesa_router_loaded": True,
            "price_alignment": True,
            "market_data": True,
            "market_scraper": True,
            "service_prices": True,
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
