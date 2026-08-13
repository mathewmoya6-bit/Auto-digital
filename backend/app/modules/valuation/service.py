"""
app/modules/valuation/service.py

Backward-compatible wrapper around the current implementation
(engine.py + repository.py + schemas.py). This exists solely because
app.modules.reports.service imports `ValuationService` from here — the
actual valuation logic all lives in engine.py now.

NOTE: The exact shape of this class (constructor args, method name,
sync vs. async) is a best guess based on the original pre-refactor
interface. If app/modules/reports/service.py calls it differently
(different method name, different args, expects a plain dict instead
of a ValuationResponse, etc.), update the `calculate` method below to
match rather than changing the call site in reports/service.py.
"""

from __future__ import annotations

from .engine import ValuationEngine, ValuationEngineError  # noqa: F401  (re-exported for compatibility)
from .repository import ValuationRepository
from .schemas import ValuationRequest, ValuationResponse


class ValuationService:
    """Thin wrapper preserving the original `ValuationService(supabase)`
    construction + `await service.calculate(request)` call pattern that
    other modules (e.g. reports) were built against.
    """

    def __init__(self, supabase):
        self.supabase = supabase
        self._engine = ValuationEngine(ValuationRepository(supabase))

    async def calculate(self, req: ValuationRequest) -> ValuationResponse:
        # ValuationEngine.calculate is currently synchronous (it makes
        # blocking supabase-py calls); wrapped in an async method here
        # so existing `await service.calculate(...)` call sites keep working.
        return self._engine.calculate(req)


__all__ = ["ValuationService"]
