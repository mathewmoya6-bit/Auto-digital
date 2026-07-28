"""
app/api/v1/services.py
========================
Backs the "Service Prices" feature your admin dashboard already reads/writes
directly via the Supabase JS client (the `service_prices` table). This module
is the FastAPI-side equivalent, for any code path (mobile app, other backend
services) that goes through the API instead of hitting Supabase directly.

Endpoints (mounted by main.py at {api_prefix}/services):
    GET    /                 - List all services
    GET    /{id}             - Get service by ID
    POST   /                 - Create service
    PUT    /{id}             - Update service
    DELETE /{id}             - Delete service
    GET    /types            - Get distinct service types
    GET    /summary/pricing  - Pricing summary (counts, avg price, etc.)
    GET    /comparison/types - Per-type comparison (min/max/avg price per type)
    POST   /bulk             - Bulk create services
    GET    /price-range      - Filter services by min/max price
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.database import supabase

router = APIRouter()

TABLE = "service_prices"


# ─── Schemas ────────────────────────────────────────────────────────────────

class ServiceCreate(BaseModel):
    service_type: str
    service_name: str
    price: float = Field(..., ge=0)
    currency: str = "KES"
    description: str = ""
    icon: str = ""
    display_order: int = 0
    is_active: bool = True


class ServiceUpdate(BaseModel):
    service_name: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


# ─── Helpers ────────────────────────────────────────────────────────────────

def _get_or_404(service_id: int) -> dict:
    resp = supabase.table(TABLE).select("*").eq("id", service_id).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail=f"Service {service_id} not found")
    return resp.data


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("")
def list_services(active_only: bool = Query(False)):
    query = supabase.table(TABLE).select("*").order("display_order")
    if active_only:
        query = query.eq("is_active", True)
    resp = query.execute()
    return {"services": resp.data or []}


@router.get("/types")
def get_service_types():
    """Distinct service_type codes currently in the catalog."""
    resp = supabase.table(TABLE).select("service_type, service_name").execute()
    rows = resp.data or []
    seen: dict[str, str] = {}
    for r in rows:
        seen.setdefault(r["service_type"], r.get("service_name"))
    return {"types": [{"service_type": k, "service_name": v} for k, v in seen.items()]}


@router.get("/summary/pricing")
def pricing_summary():
    resp = supabase.table(TABLE).select("*").execute()
    rows = resp.data or []
    active = [r for r in rows if r.get("is_active")]

    by_currency: dict[str, list[float]] = {}
    for r in active:
        by_currency.setdefault(r.get("currency", "KES"), []).append(float(r.get("price") or 0))

    return {
        "total_services": len(rows),
        "active_services": len(active),
        "inactive_services": len(rows) - len(active),
        "average_price_by_currency": {
            cur: round(sum(p) / len(p), 2) if p else 0 for cur, p in by_currency.items()
        },
        "min_price_by_currency": {cur: min(p) if p else 0 for cur, p in by_currency.items()},
        "max_price_by_currency": {cur: max(p) if p else 0 for cur, p in by_currency.items()},
    }


@router.get("/comparison/types")
def compare_by_type():
    """Per-service_type price comparison - useful for an admin table showing
    min/max/avg price across all currencies/entries for each service type."""
    resp = supabase.table(TABLE).select("*").execute()
    rows = resp.data or []

    by_type: dict[str, list[float]] = {}
    names: dict[str, str] = {}
    for r in rows:
        t = r.get("service_type", "unknown")
        by_type.setdefault(t, []).append(float(r.get("price") or 0))
        names.setdefault(t, r.get("service_name", t))

    return {
        "comparison": [
            {
                "service_type": t,
                "service_name": names[t],
                "count": len(prices),
                "min_price": min(prices),
                "max_price": max(prices),
                "avg_price": round(sum(prices) / len(prices), 2),
            }
            for t, prices in by_type.items()
        ]
    }


@router.get("/price-range")
def filter_by_price_range(
    min_price: float = Query(0, ge=0),
    max_price: float = Query(1_000_000, ge=0),
    currency: str = Query("KES"),
):
    if max_price < min_price:
        raise HTTPException(status_code=400, detail="max_price must be >= min_price")
    resp = (
        supabase.table(TABLE)
        .select("*")
        .eq("currency", currency)
        .gte("price", min_price)
        .lte("price", max_price)
        .execute()
    )
    return {"services": resp.data or [], "min_price": min_price, "max_price": max_price}


@router.get("/{service_id}")
def get_service(service_id: int):
    return _get_or_404(service_id)


@router.post("")
def create_service(payload: ServiceCreate):
    resp = supabase.table(TABLE).insert(payload.model_dump()).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to create service")
    return resp.data[0]


@router.post("/bulk")
def bulk_create_services(payload: list[ServiceCreate]):
    if not payload:
        raise HTTPException(status_code=400, detail="Provide at least one service")
    rows = [p.model_dump() for p in payload]
    resp = supabase.table(TABLE).insert(rows).execute()
    return {"created": len(resp.data or []), "services": resp.data or []}


@router.put("/{service_id}")
def update_service(service_id: int, payload: ServiceUpdate):
    _get_or_404(service_id)
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    resp = supabase.table(TABLE).update(updates).eq("id", service_id).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to update service")
    return resp.data[0]


@router.delete("/{service_id}")
def delete_service(service_id: int):
    _get_or_404(service_id)
    supabase.table(TABLE).delete().eq("id", service_id).execute()
    return {"deleted": True, "id": service_id}
