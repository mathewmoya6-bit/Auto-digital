# app/modules/admin/router.py
# Auto-D Kenya - Admin Router
# ================================================================
# TYPE: MODULE - Admin API endpoints (Minimal)

from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import require_admin
from app.core.logging import get_logger
from app.core.supabase import get_supabase_client
from app.modules.admin.schemas import *

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)


def get_supabase():
    """Get Supabase client."""
    return get_supabase_client()


# ─── PAYMENTS ────────────────────────────────────────────────────

@router.get("/payments", response_model=AdminPaymentsResponse)
async def get_payments(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[PaymentStatus] = None,
    user_id: Optional[UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """
    Get all payments with filtering and pagination.
    
    This is the ONE endpoint for all payment-related queries.
    """
    supabase = get_supabase()
    
    try:
        # Build query
        query = supabase.table("payments").select("*, services(*)", count="exact")
        
        # Apply filters
        if status:
            query = query.eq("status", status.value)
        
        if user_id:
            query = query.eq("user_id", str(user_id))
        
        if start_date:
            query = query.gte("created_at", start_date.isoformat())
        
        if end_date:
            query = query.lte("created_at", end_date.isoformat())
        
        # Get total count
        count_result = query.limit(0).execute()
        total = count_result.count or 0
        
        # Get payments with pagination
        result = query.order("created_at", desc=True).limit(limit).offset(offset).execute()
        payments_data = result.data or []

        # Transform to schema
        payments = []
        for p in payments_data:
            service = p.get("services", {})
            payments.append(AdminPayment(
                id=UUID(p["id"]),
                user_id=UUID(p["user_id"]) if p.get("user_id") else None,
                service_id=UUID(p["service_id"]) if p.get("service_id") else None,
                service_name=service.get("name") if service else None,
                service_code=ServiceCode(service.get("code")) if service and service.get("code") else None,
                amount=Decimal(str(p.get("amount", 0))),
                currency=p.get("currency", "KES"),
                status=PaymentStatus(p.get("status", "pending")),
                phone=p.get("phone"),
                checkout_request_id=p.get("checkout_request_id"),
                mpesa_receipt=p.get("mpesa_receipt"),
                created_at=datetime.fromisoformat(p["created_at"]) if p.get("created_at") else datetime.utcnow(),
                completed_at=datetime.fromisoformat(p["completed_at"]) if p.get("completed_at") else None,
            ))

        return AdminPaymentsResponse(
            payments=payments,
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Error fetching payments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch payments"
        )


# ─── REPORTS ────────────────────────────────────────────────────

@router.get("/reports", response_model=RevenueReportResponse)
async def get_reports(
    period: str = Query("month", description="Period: day, week, month, year, all"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """
    Get comprehensive reports with revenue analytics.
    
    This is the ONE endpoint for all report-related queries.
    Returns revenue breakdown by service, total revenue, and transaction counts.
    """
    supabase = get_supabase()
    
    try:
        # Set date range based on period
        now = datetime.utcnow()
        
        if start_date and end_date:
            # Use provided dates
            pass
        elif period == "day":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == "week":
            start_date = now - timedelta(days=7)
            end_date = now
        elif period == "month":
            start_date = now - timedelta(days=30)
            end_date = now
        elif period == "year":
            start_date = now - timedelta(days=365)
            end_date = now
        else:  # all
            start_date = None
            end_date = None
        
        # Build query
        query = supabase.table("payments").select("*, services(*)")
        query = query.eq("status", "completed")
        
        if start_date:
            query = query.gte("created_at", start_date.isoformat())
        if end_date:
            query = query.lte("created_at", end_date.isoformat())
        
        result = query.execute()
        payments_data = result.data or []

        # Calculate totals
        total_revenue = Decimal(0)
        revenue_by_service = {}
        service_breakdown = []
        
        for payment in payments_data:
            amount = Decimal(str(payment.get("amount", 0)))
            total_revenue += amount
            
            service = payment.get("services", {})
            service_name = service.get("name", "Unknown") if service else "Unknown"
            
            if service_name in revenue_by_service:
                revenue_by_service[service_name] += amount
            else:
                revenue_by_service[service_name] = amount

        # Build service breakdown
        for name, revenue in revenue_by_service.items():
            percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0
            service_breakdown.append({
                "service": name,
                "revenue": float(revenue),
                "percentage": float(percentage),
                "transactions": len([p for p in payments_data 
                                    if p.get("services", {}).get("name") == name])
            })

        return RevenueReportResponse(
            total_revenue=float(total_revenue),
            total_transactions=len(payments_data),
            revenue_by_service={k: float(v) for k, v in revenue_by_service.items()},
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )


# ─── OPTIONAL: SIMPLE STATS ─────────────────────────────────────

@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats():
    """
    Get quick dashboard statistics.
    
    Optional - can be removed if not needed.
    """
    supabase = get_supabase()
    
    try:
        # Get counts
        users_count = supabase.table("users").select("count", count="exact").limit(0).execute()
        vehicles_count = supabase.table("vehicles").select("count", count="exact").limit(0).execute()
        payments_count = supabase.table("payments").select("count", count="exact").limit(0).execute()
        
        # Get revenue
        revenue_result = supabase.table("payments") \
            .select("amount") \
            .eq("status", "completed") \
            .execute()
        
        total_revenue = Decimal(0)
        for p in revenue_result.data or []:
            total_revenue += Decimal(str(p.get("amount", 0)))
        
        return AdminStatsResponse(
            total_users=users_count.count or 0,
            total_vehicles=vehicles_count.count or 0,
            total_payments=payments_count.count or 0,
            total_revenue=total_revenue,
            total_services_purchased=0,  # Could add if needed
            new_users_this_week=0,  # Could add if needed
            active_services=0,  # Could add if needed
            updated_at=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch stats"
        )


# ─── OPTIONAL: HEALTH CHECK ─────────────────────────────────────

@router.get("/health", response_model=AdminHealthResponse)
async def health_check():
    """Simple health check."""
    return AdminHealthResponse(
        status=ComponentStatus.HEALTHY,
        service="admin",
        timestamp=datetime.utcnow()
    )
