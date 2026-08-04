# app/modules/market/schemas.py
# ================================================================
# Auto-D Kenya - Market Schemas
# ================================================================

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field


# ─── Request Schemas ──────────────────────────────────────────────

class MarketInsightsRequest(BaseModel
