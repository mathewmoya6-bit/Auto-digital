"""
app/modules/valuation/__init__.py

Exposes the valuation router for app.main to import as:

    from app.modules.valuation.router import router as valuation_router

Keeping this export here too means `from app.modules.valuation import router`
(the package, not just the module) also works if anything imports it that way.
"""

from .router import router

__all__ = ["router"]
