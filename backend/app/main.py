# app/main.py
# Auto-D Kenya - Application Entry Point
# ================================================================

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles

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

# Mileage router — imported defensively since it's newly added and
# hasn't been verified in production yet. If it has a bad schema or
# import error, the rest of the API keeps running instead of the
# whole app crashing on startup (as happened with an earlier WIP
# version of main.py that imported it unguarded).
try:
    from app.modules.mileage.router import router as mileage_router
    MILEAGE_ROUTER_LOADED = True
    logger.info("✅ Mileage router imported successfully")
except Exception as e:
    logger.error(f"❌ Mileage router failed to import: {e}")
    mileage_router = None
    MILEAGE_ROUTER_LOADED = False

# ─── STATIC FILE PATHS ───────────────────────────────────────────
# Confirmed repo layout (Auto-digital repo root = Render's
# /opt/render/project/src):
#   backend/app/main.py   <- this file
#   public/manifest.json
#   public/assets/icon-192.png ...
# i.e. public/ is a SIBLING of backend/, not of app/. So from this
# file we go up two levels (app -> backend -> repo root) then into
# public/.

PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "public")
MANIFEST_PATH = os.path.join(PUBLIC_DIR, "manifest.json")
ASSETS_DIR = os.path.join(PUBLIC_DIR, "assets")

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
    logger.info(f"Mileage router loaded: {MILEAGE_ROUTER_LOADED}")
    logger.info(f"Public dir: {os.path.abspath(PUBLIC_DIR)}")
    logger.info(f"Manifest present: {os.path.isfile(MANIFEST_PATH)}")
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


# ─── STATIC / PWA FILES ──────────────────────────────────────────
# ⚠️ IMPORTANT: These are registered here — BEFORE the /{page_name}
# and /{page_name}.html catch-all redirects defined further down —
# on purpose. Starlette matches routes in registration order, and
# /manifest.json is a single path segment, so it would otherwise be
# caught by the /{page_name} catch-all (which falls through without
# a return value for names not in spa_pages, producing a `null` JSON
# body instead of your actual manifest). Registering the explicit
# route first means it always wins the match.

@app.get("/manifest.json", include_in_schema=False)
async def manifest():
    """Serves the PWA web app manifest with the correct media type."""
    if not os.path.isfile(MANIFEST_PATH):
        logger.error(f"❌ manifest.json not found at {os.path.abspath(MANIFEST_PATH)}")
        return {"error": "manifest.json not found on server"}
    return FileResponse(MANIFEST_PATH, media_type="application/manifest+json")


# Icons and other static assets. Multi-segment paths like
# /assets/icon-192.png have two path segments, so they never collide
# with the single-segment /{page_name} catch-all regardless of
# ordering — but this is kept up here for clarity alongside the
# manifest route.
#
# Guarded with an isdir check so a wrong/missing path logs a clear
# warning instead of crashing the whole app on startup (as happened
# when ASSETS_DIR pointed at a folder that doesn't exist on Render).
if os.path.isdir(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
else:
    logger.error(
        f"❌ ASSETS_DIR not found at {os.path.abspath(ASSETS_DIR)} — "
        f"/assets/* will 404 until PUBLIC_DIR is corrected."
    )


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

# Admin Routes — also mounted WITHOUT the versioned API prefix.
# The admin panel frontend calls unprefixed paths like
# /admin/service-prices, /admin/payments, /admin/analytics, and
# /admin/services. Those were only reachable at
# {API_V1_PREFIX}/admin/... before, so unprefixed calls fell through
# to the SPA catch-all redirect / 404'd, which surfaces in the
# browser as "Failed to fetch". Mounting the same router again here
# (no prefix) makes both paths work without duplicating any route
# logic. Remove this block if the frontend is updated to always call
# the prefixed path instead.
app.include_router(
    admin_router,
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

# Mileage Routes (guarded — see import block above)
if MILEAGE_ROUTER_LOADED and mileage_router is not None:
    app.include_router(
        mileage_router,
        prefix=settings.API_V1_PREFIX,
        tags=["Mileage"]
    )
    logger.info(f"✅ Mileage router registered at {settings.API_V1_PREFIX}/mileage")
else:
    logger.warning("⚠️ Mileage router not registered — check import error above")


# ─── DIGITAL ASSET LINKS (for TWA / Android app verification) ───
# Required so the Android app (com.meipressgroup.autod) can verify
# it's authorized to open this domain fullscreen without a browser
# address bar. Google Play / Chrome fetches this at install time.
#
# IMPORTANT: replace the fingerprint below with the real SHA-256
# value from your own signing key, obtained via:
#   keytool -list -v -keystore android.keystore -alias android
# Keep the colons in the fingerprint string.
#
# This route is defined here (before the catch-all page redirects
# below) so it can never be shadowed by /{page_name} — though as a
# two-segment path it wouldn't collide with that single-segment
# catch-all anyway.

ASSETLINKS_SHA256_FINGERPRINTS = [
    "24:E7:D7:72:81:65:C1:44:5F:3B:AF:E2:C4:F5:51:83:CE:FF:AF:5D:A5:75:79:16:66:60:59:BD:9D:03:99:B1",
]


@app.get("/.well-known/assetlinks.json", include_in_schema=False)
async def digital_asset_links():
    """Digital Asset Links manifest for TWA verification."""
    return [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": "com.meipressgroup.autod",
                "sha256_cert_fingerprints": ASSETLINKS_SHA256_FINGERPRINTS,
            },
        }
    ]


# ─── HTML PAGE REDIRECTS ────────────────────────────────────────
# Prevent direct access to HTML pages - redirect to SPA root

@app.get("/{page_name}.html", include_in_schema=False)
async def redirect_html_pages(page_name: str):
    """
    Prevent direct access to HTML pages.
    Always load the SPA from the root.
    
    This redirects:
    - /services.html → /
    - /login.html → /
    - /admin.html → /
    - /index.html → /
    - /dashboard.html → /
    - /valuation.html → /
    - /market.html → /
    - /scraper.html → /
    - /profile.html → /
    - /settings.html → /
    - /vehicles.html → /
    - /reports.html → /
    - /notifications.html → /
    - /ownership.html → /
    - /running-cost.html → /
    - /mpesa.html → /
    """
    return RedirectResponse(url="/", status_code=302)


# Also redirect common SPA routes without .html extension
@app.get("/{page_name}", include_in_schema=False)
async def redirect_spa_pages(page_name: str):
    """
    Redirect common SPA routes to root.
    This ensures the SPA handles routing.
    """
    # List of pages that should redirect to root
    spa_pages = {
        "services", "login", "admin", "index", "dashboard", 
        "valuation", "market", "scraper", "profile", "settings",
        "vehicles", "reports", "notifications", "ownership", 
        "running-cost", "mpesa", "signup", "register", "forgot-password"
    }
    
    if page_name.lower() in spa_pages:
        return RedirectResponse(url="/", status_code=302)
    
    # Don't redirect API paths or other valid routes
    # Let FastAPI handle them normally


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
        "dependencies": {},
        "modules": {
            "mileage": MILEAGE_ROUTER_LOADED,
        },
        "mileage_router_loaded": MILEAGE_ROUTER_LOADED,
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
        "environment": settings.ENVIRONMENT,
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
        "modules": {
            "mileage": MILEAGE_ROUTER_LOADED,
        },
        "mileage_router_loaded": MILEAGE_ROUTER_LOADED,
    }


# ─── STARTUP ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.PROJECT_NAME}")
    logger.info(f"📡 API Base URL: {settings.API_BASE_URL}")
    logger.info(f"🔧 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔌 Port: {settings.PORT}")
    logger.info(f"🛣️  Mileage router loaded: {MILEAGE_ROUTER_LOADED}")
    logger.info("=" * 60)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
