# Auto-D Kenya - Vehicle Repository
# ================================================================
# TYPE: MODULE - Vehicle Repository
#
# SINGLE SOURCE OF TRUTH
#
# Master Catalogue : vehicle_master_specs (VIEW)
# Prices           : vehicle_base_prices
# User Vehicles    : user_vehicles
#
# ================================================================

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi.concurrency import run_in_threadpool

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class VehicleRepository:
    """
    Repository for all vehicle database operations.
    """

    def __init__(self):
        self.supabase = get_supabase()

    async def _run(self, fn):
        """
        Execute synchronous Supabase queries in a worker thread.
        """
        return await run_in_threadpool(fn)
