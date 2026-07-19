# backend/app/services/__init__.py
"""
Services Package - Business logic layer
Handles application logic and orchestrates data access
"""

import logging

logger = logging.getLogger(__name__)

from app.services.vehicle_service import VehicleService
from app.services.fuel_service import FuelService
from app.services.mileage_service import MileageService
from app.services.ownership_service import OwnershipService
from app.services.valuation_service import ValuationService
from app.services.report_service import ReportService

# Try to import M-Pesa service - graceful fallback if not available
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
    "VehicleService",
    "FuelService",
    "MileageService",
    "OwnershipService",
    "ValuationService",
    "ReportService",
    "MpesaService",
]

logger.info("📦 Services loaded successfully")
