# app/modules/valuation/__init__.py
# ================================================================
# Auto-D Kenya - Valuation Module
# ================================================================

"""Vehicle valuation module for Auto-D Kenya."""

from .router import router
from .engine import ValuationEngine
from .service import ValuationService
from .repository import ValuationRepository

from .schemas import (
    # Request schemas
    ValuationRequest,
    LegacyValuationRequest,
    
    # Response schemas
    ValuationResponse,
    ValuationReportResponse,
    ValuationSummary,
    ValuationStats,
    ValuationHistoryItem,
    ValuationHistoryResponse,
    ValuationHealthResponse,
    QuickValuationResponse,
    
    # Component schemas
    ValuationAdjustment,
    DepreciationResult,
    ValuationVehicle,
    ValuationComparable,
    
    # Factory functions
    create_valuation_response,
    create_valuation_report_response,
)

__all__ = [
    "router",
    "ValuationEngine",
    "ValuationService",
    "ValuationRepository",
    
    # Request schemas
    "ValuationRequest",
    "LegacyValuationRequest",
    
    # Response schemas
    "ValuationResponse",
    "ValuationReportResponse",
    "ValuationSummary",
    "ValuationStats",
    "ValuationHistoryItem",
    "ValuationHistoryResponse",
    "ValuationHealthResponse",
    "QuickValuationResponse",
    
    # Component schemas
    "ValuationAdjustment",
    "DepreciationResult",
    "ValuationVehicle",
    "ValuationComparable",
    
    # Factory functions
    "create_valuation_response",
    "create_valuation_report_response",
]
