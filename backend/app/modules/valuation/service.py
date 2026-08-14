"""
service.py

Backward-compatible service wrapper for the valuation module.

The actual valuation logic lives in:
    engine.py
    repository.py
    schemas.py
    models.py

This wrapper exists for modules such as reports.service that still
instantiate ValuationService.
"""

from __future__ import annotations

import inspect
from typing import Any, Optional

from app.core.database import get_supabase

from .engine import (
    ValuationEngine,
    ValuationEngineError,
)
from .repository import ValuationRepository
from .schemas import (
    ValuationRequest,
    ValuationResponse,
)


def _resolve_supabase_client() -> Any:
    """
    Resolve the configured synchronous Supabase client.

    Supports:
    - normal synchronous factory
    - synchronous generator dependency

    Async-generator dependencies are rejected because this wrapper
    is used outside FastAPI's dependency lifecycle.
    """

    result = get_supabase()

    if inspect.isasyncgen(result):
        raise RuntimeError(
            "get_supabase() returned an async generator. "
            "ValuationService requires a synchronous "
            "Supabase client."
        )

    if inspect.isgenerator(result):
        try:
            return next(result)
        finally:
            result.close()

    if hasattr(result, "__next__"):
        return next(result)

    return result


class ValuationService:
    """
    Compatibility wrapper around ValuationEngine.
    """

    def __init__(
        self,
        supabase: Optional[Any] = None,
    ):

        client = (
            supabase
            if supabase is not None
            else _resolve_supabase_client()
        )

        self.supabase = client

        self.repository = (
            ValuationRepository(client)
        )

        self.engine = (
            ValuationEngine(
                self.repository
            )
        )

    async def calculate(
        self,
        req: ValuationRequest,
    ) -> ValuationResponse:
        """
        Preserve the existing async service interface.
        """

        return self.engine.calculate(req)


__all__ = [
    "ValuationService",
    "ValuationEngine",
    "ValuationEngineError",
]
