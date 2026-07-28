"""
API v1 package - Router imports
"""
from .auth import router as auth_router
from .vehicles import router as vehicles_router
from .valuation import router as valuation_router
from .mileage import router as mileage_router
from .ownership import router as ownership_router
from .fuel import router as fuel_router
from .running_cost import router as running_cost_router
from .admin import router as admin_router
from .reports import router as reports_router
from .mpesa import router as mpesa_router

# Optional: These will be available if the files exist
try:
    from .services import router as services_router
except ImportError:
    services_router = None

try:
    from .price_alignment import router as price_alignment_router
except ImportError:
    price_alignment_router = None

try:
    from .market import router as market_router
except ImportError:
    market_router = None

try:
    from .scraper import router as scraper_router
except ImportError:
    scraper_router = None

__all__ = [
    "auth_router",
    "vehicles_router", 
    "valuation_router",
    "mileage_router",
    "ownership_router",
    "fuel_router",
    "running_cost_router",
    "admin_router",
    "reports_router",
    "mpesa_router",
    "services_router",
    "price_alignment_router",
    "market_router",
    "scraper_router"
]
