"""
Services Package - Business logic layer
Handles application logic and orchestrates data access
"""

import logging

logger = logging.getLogger(__name__)

# ─── Core Services ──────────────────────────────────────────────────────
from app.services.vehicle_service import VehicleService
from app.services.fuel_service import FuelService
from app.services.mileage_service import MileageService
from app.services.ownership_service import OwnershipService
from app.services.valuation_service import ValuationService
from app.services.report_service import ReportService
from app.services.cost_calculator import CostCalculator
from app.services.auth_service import AuthService
from app.services.notification_service import NotificationService

# ─── Market & Scraper Services ─────────────────────────────────────────
from app.services.market_service import MarketService
from app.services.scraper_service import ScraperService

# ─── M-Pesa Service (graceful fallback) ──────────────────────────────
try:
    from app.services.mpesa_service import MpesaService
    logger.info("✅ M-Pesa service loaded successfully")
except ImportError as e:
    MpesaService = None
    logger.warning(f"⚠️ M-Pesa service not available: {e}")
except Exception as e:
    MpesaService = None
    logger.error(f"❌ Error loading M-Pesa service: {e}")


__all__ = [
    # Core Services
    "VehicleService",
    "FuelService",
    "MileageService",
    "OwnershipService",
    "ValuationService",
    "ReportService",
    "CostCalculator",
    "AuthService",
    "NotificationService",
    
    # Market & Scraper Services
    "MarketService",
    "ScraperService",
    
    # M-Pesa
    "MpesaService",
]

# ─── Service Registry ──────────────────────────────────────────────────
SERVICES = {
    "vehicle": VehicleService,
    "fuel": FuelService,
    "mileage": MileageService,
    "ownership": OwnershipService,
    "valuation": ValuationService,
    "report": ReportService,
    "cost": CostCalculator,
    "auth": AuthService,
    "notification": NotificationService,
    "market": MarketService,
    "scraper": ScraperService,
    "mpesa": MpesaService,
}

logger.info("📦 Services loaded successfully")
logger.info(f"📋 Available services: {', '.join(SERVICES.keys())}")
