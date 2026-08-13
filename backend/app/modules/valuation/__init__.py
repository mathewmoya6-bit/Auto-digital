"""
app/modules/valuation/__init__.py

Exposes the valuation router and the ValuationService compatibility
wrapper (used by app.modules.reports.service) for:

    from app.modules.valuation.router import router as valuation_router
    from app.modules.valuation.service import ValuationService
"""

from .router import router
from .service import ValuationService

__all__ = ["router", "ValuationService"]
