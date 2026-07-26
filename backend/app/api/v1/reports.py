# app/api/v1/reports.py
"""
Reports API - Professional report generation
"""

from fastapi import APIRouter, HTTPException, Query, Response, BackgroundTasks
from typing import Optional
from datetime import datetime
import logging

from app.services.report_generator import ReportGenerator

logger = logging.getLogger(__name__)

router = APIRouter()
report_generator = ReportGenerator()


@router.get("/valuation")
async def generate_valuation_report(
    variant_id: str = Query(..., description="Vehicle variant ID"),
    year: int = Query(..., description="Vehicle year"),
    include_comparables: bool = Query(True, description="Include comparable vehicles"),
    include_history: bool = Query(True, description="Include price history"),
    include_trends: bool = Query(True, description="Include market trends")
):
    """
    Generate a professional vehicle valuation report (PDF)
    
    Returns a PDF file with:
    - Executive summary
    - Valuation analysis
    - Price history chart
    - Comparable vehicles
    - Market trends
    - Recommendations
    """
    try:
        pdf_bytes = await report_generator.generate_valuation_report(
            variant_id=variant_id,
            year=year,
            include_comparables=include_comparables,
            include_history=include_history,
            include_trends=include_trends
        )
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=valuation_report_{variant_id}_{year}_{datetime.now().strftime('%Y%m%d')}.pdf"
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating valuation report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")


@router.get("/market-insights")
async def generate_market_insights_report(
    make: Optional[str] = Query(None, description="Filter by make"),
    body_type: Optional[str] = Query(None, description="Filter by body type"),
    county: Optional[str] = Query(None, description="Filter by county")
):
    """
    Generate a professional market insights report (PDF)
    
    Returns a PDF file with:
    - Market overview
    - Key metrics
    - Price distribution
    - Trending vehicles
    - Dealer performance
    - Market outlook
    """
    try:
        pdf_bytes = await report_generator.generate_market_insights_report(
            make=make,
            body_type=body_type,
            county=county
        )
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=market_insights_{datetime.now().strftime('%Y%m%d')}.pdf"
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating market insights report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")


@router.get("/ownership-cost")
async def generate_ownership_cost_report(
    variant_id: str = Query(..., description="Vehicle variant ID"),
    year: int = Query(..., description="Vehicle year"),
    annual_mileage: int = Query(20000, description="Annual mileage in km"),
    ownership_years: int = Query(5, description="Ownership period in years"),
    county: str = Query("Nairobi", description="County for location adjustment")
):
    """
    Generate a professional ownership cost report (PDF)
    
    Returns a PDF file with:
    - Vehicle summary
    - Cost breakdown chart
    - Year-by-year cost table
    - Cost per kilometer analysis
    - Savings recommendations
    """
    try:
        pdf_bytes = await report_generator.generate_ownership_cost_report(
            variant_id=variant_id,
            year=year,
            annual_mileage=annual_mileage,
            ownership_years=ownership_years,
            county=county
        )
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=ownership_cost_{variant_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating ownership cost report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")
