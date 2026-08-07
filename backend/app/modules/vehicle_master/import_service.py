"""
Auto-D Kenya
Vehicle Master Import Service
"""

import csv
import json
import logging
from typing import Any, Dict, List, Optional
from io import StringIO
from datetime import datetime

from fastapi.concurrency import run_in_threadpool

from app.core.database import get_supabase
from app.core.exceptions import ValidationException

logger = logging.getLogger(__name__)


class VehicleImportService:
    """Import vehicles from various formats."""

    def __init__(self):
        self.db = get_supabase()

    async def _run(self, fn):
        return await run_in_threadpool(fn)

    async def import_csv(self, csv_content: str) -> Dict[str, Any]:
        """Import vehicles from CSV."""
        try:
            reader = csv.DictReader(StringIO(csv_content))
            rows = list(reader)
            
            if not rows:
                return {"success": False, "message": "No data found", "imported": 0}
            
            imported = 0
            errors = []
            
            for row in rows:
                try:
                    # Validate required fields
                    if not row.get("make") or not row.get("model"):
                        errors.append({"row": row, "error": "Missing make or model"})
                        continue
                    
                   
