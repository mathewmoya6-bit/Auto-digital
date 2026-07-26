# backend/app/api/v1/__init__.py
"""
API V1 - Version 1 of the Auto-D API
All endpoints are prefixed with /api/v1
"""

import logging

logger = logging.getLogger(__name__)

# Import all routers directly
from .auth import router as auth_router
from .vehicles import router as vehicles_router
from .valuation import router as valuation_router
from .mileage import router as mileage_router
from .ownership import router as ownership_router
from .fuel import router as fuel_router
from .admin import router as admin_router
from .reports import router as reports_router
from .running_cost import router as running_cost_router

# ============================================================
# NEW: Price Alignment & Market Scraper Routes
# ============================================================
try:
    from .price_alignment import router as price_alignment_router
    logger.info("✅ Price Alignment router loaded successfully")
except ImportError as e:
    price_alignment_router = None
    logger.warning(f"⚠️ Price Alignment router not available: {e}")
except Exception as e:
    price_alignment_router = None
    logger.error(f"❌ Error loading Price Alignment router: {e}")

try:
    from .market import router as market_router
    logger.info("✅ Market router loaded successfully")
except ImportError as e:
    market_router = None
    logger.warning(f"⚠️ Market router not available: {e}")
except Exception as e:
    market_router = None
    logger.error(f"❌ Error loading Market router: {e}")

# Try to import M-Pesa router - graceful fallback
try:
    from .mpesa import router as mpesa_router
    logger.info("✅ M-Pesa router loaded successfully")
except ImportError as e:
    mpesa_router = None
    logger.warning(f"⚠️ M-Pesa router not available: {e}")
except Exception as e:
    mpesa_router = None
    logger.error(f"❌ Error loading M-Pesa router: {e}")

__all__ = [
    "auth_router",
    "vehicles_router",
    "valuation_router",
    "mileage_router",
    "ownership_router",
    "fuel_router",
    "admin_router",
    "reports_router",
    "running_cost_router",
    "price_alignment_router",  # NEW
    "market_router",           # NEW
    "mpesa_router",
]

logger.info("📦 API Routers loaded successfully")
