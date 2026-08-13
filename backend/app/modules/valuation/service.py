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

import inspect
from typing import Optional

from app.core.database import get_supabase

from .engine import ValuationEngine, ValuationEngineError  # noqa: F401  (re-exported for compatibility)
from .repository import ValuationRepository
from .schemas import ValuationRequest, ValuationResponse


def _resolve_supabase_client():
    """Resolve an actual Supabase client from get_supabase().

    get_supabase() might be:
      - a plain factory:            def get_supabase(): return client
      - a sync generator dependency: def get_supabase(): yield client
      - an async generator dependency (can't be resolved synchronously here)

    This module-level `ReportService()` -> `ValuationService()` chain runs
    at import time, outside FastAPI's request cycle, so we can't rely on
    Depends() to drive a generator dependency for us. Handle the common
    cases and fail loudly with a clear message for the one we can't.
    """
    result = get_supabase()

    if inspect.isasyncgen(result):
        raise RuntimeError(
            "get_supabase() is an async-generator dependency, which can't be "
            "resolved outside of FastAPI's request cycle. ValuationService is "
            "being instantiated at module import time (via ReportService()), "
            "so it needs either a plain synchronous client factory in "
            "app/core/database.py (e.g. get_supabase_client()), or "
            "ReportService/ValuationService should be refactored to receive "
            "their supabase client via Depends() instead of module-level "
            "instantiation."
        )

    if inspect.isgenerator(result) or hasattr(result, "__next__"):
        return next(result)

    return result


class ValuationService:
    """Thin wrapper preserving the original `ValuationService()` /
    `ValuationService(supabase)` construction + `await service.calculate(request)`
    call pattern that other modules (e.g. reports) were built against.

    `supabase` is optional: app.modules.reports.service instantiates this
    with no arguments (`ValuationService()`), so when it isn't passed in,
    the client is resolved internally via _resolve_supabase_client().
    """

    def __init__(self, supabase: Optional[object] = None):
        self.supabase = supabase if supabase is not None else _resolve_supabase_client()
        self._engine = ValuationEngine(ValuationRepository(self.supabase))

    async def calculate(self, req: ValuationRequest) -> ValuationResponse:
        # ValuationEngine.calculate is currently synchronous (it makes
        # blocking supabase-py calls); wrapped in an async method here
        # so existing `await service.calculate(...)` call sites keep working.
        return self._engine.calculate(req)


__all__ = ["ValuationService"]
