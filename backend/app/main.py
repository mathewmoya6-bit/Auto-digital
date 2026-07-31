# app/main.py
# Auto-D Kenya - Application Entry Point
# ================================================================

import logging
from contextlib import asynccontextmanager
from datetime import datetime, UTC
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
from app.modules.running_cost.router import router as running_cost_router
from app.modules.ownership.router import router as ownership_router

logger = logging.getLogger(__name__)

# ─── LIFESPAN MANAGER ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
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

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    # ✅ ENABLED: Docs are now accessible in all environments
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# ─── MIDDLEWARE (non-CORS) ───────────────────────────────────────
# ⚠️ IMPORTANT: This must run BEFORE CORSMiddleware is added below.
# In Starlette, the LAST middleware added becomes the OUTERMOST layer.
# CORS has to be outermost so it can attach Access-Control-* headers
# even to responses produced by TrustedHostMiddleware, auth checks,
# or errors from the middleware below — and so unauthenticated OPTIONS
# preflight requests never get rejected before reaching CORSMiddleware.

setup_middleware(app)


# ─── CORS MIDDLEWARE ─────────────────────────────────────────────
# ⚠️ CRITICAL: CORS MUST be the LAST middleware registered so it ends
# up as the outermost layer (see note above).

cors_origins = settings.get_cors_origins()
logger.info(f"CORS Origins configured: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)


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

# Running Cost Routes
app.include_router(
    running_cost_router,
    prefix=settings.API_V1_PREFIX,
    tags=["Running Cost"]
)

# Ownership Routes
app.include_router(
    ownership_router,
    prefix=settings.API_V1_PREFIX,
    tags=["Ownership"]
)


# ─── HEALTH CHECK ENDPOINTS ─────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
        "service": settings.PROJECT_NAME,
        "timestamp": datetime.now(UTC).isoformat(),
        "dependencies": {}
    }

    # Check Supabase connection
    try:
        client = get_supabase()
        client.table("services").select("*", count="exact").limit(1).execute()
        health_status["dependencies"]["supabase"] = "connected"
    except Exception as e:
        health_status["dependencies"]["supabase"] = "disconnected"
        health_status["dependencies"]["supabase_error"] = str(e)
        health_status["status"] = "degraded"

    return health_status


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Readiness check endpoint"""
    readiness_status = {
        "status": "ready",
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": settings.ENVIRONMENT
    }

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
    """Liveness check endpoint"""
    return {
        "status": "alive",
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": settings.ENVIRONMENT
    }


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
    """Root endpoint"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "api_prefix": settings.API_V1_PREFIX,
        "base_url": settings.API_BASE_URL,
        "docs_url": f"{settings.API_BASE_URL}/docs",
        "cors_origins": settings.get_cors_origins(),
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
