# backend/app/api/v1/price_alignment.py
"""
Price Alignment API Routes
Handles vehicle price alignment, analysis, and history
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional, List, Dict
from datetime import datetime
import logging

from app.services.price_aligner import PriceAligner
from app.services.price_analyzer import PriceAnalyzer
from app.services.supabase_service import SupabaseService
from app.models.price import AlignedPrice, VehicleCondition

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/price", tags=["Price Alignment"])

# Initialize services
supabase_service = SupabaseService()
price_aligner = PriceAligner(supabase_service)
price_analyzer = PriceAnalyzer(supabase_service)


@router.get("/align")
async def align_price(
    variant_id: str = Query(..., description="Vehicle variant ID"),
    year: int = Query(..., description="Vehicle year"),
    mileage: Optional[int] = Query(None, description="Current mileage in km"),
    condition: VehicleCondition = Query(VehicleCondition.GOOD, description="Vehicle condition"),
    county: str = Query("Nairobi", description="County for location adjustment")
) -> AlignedPrice:
    """
    Get aligned market price for a vehicle.
    
    Combines data from:
    - Jiji Kenya (highest volume)
    - Cheki Kenya (dealer pricing)
    - Autochek Kenya (premium market)
    - Secondary sources (BeepBeep, PigiaMe)
    """
    try:
        result = await price_aligner.align_price(
            variant_id=variant_id,
            year=year,
            mileage=mileage,
            condition=condition,
            county=county
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Price alignment error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analyze")
async def analyze_prices(
    variant_id: str = Query(..., description="Vehicle variant ID"),
    year: int = Query(..., description="Vehicle year")
) -> Dict:
    """
    Get detailed price analysis for a vehicle.
    
    Returns:
    - Statistical analysis (median, average, min, max)
    - Confidence score based on data quality
    - Source breakdown (which marketplaces contributed)
    - Price distribution (percentiles)
    """
    try:
        analysis = await price_analyzer.analyze_prices(variant_id, year)
        
        if not analysis:
            return {
                "status": "insufficient_data",
                "message": "Not enough market data available for this vehicle",
                "variant_id": variant_id,
                "year": year,
                "recommendation": "Try a different year or check back later"
            }
        
        # Get price distribution
        distribution = await price_analyzer.get_price_distribution(variant_id, year)
        
        # Determine confidence level
        confidence_level = "high" if analysis.confidence_score > 0.7 else "medium" if analysis.confidence_score > 0.5 else "low"
        
        return {
            "status": "success",
            "variant_id": variant_id,
            "year": year,
            "analysis": analysis.dict(),
            "source_breakdown": analysis.source_breakdown,
            "price_distribution": distribution,
            "confidence_level": confidence_level,
            "confidence_score": analysis.confidence_score,
            "sample_size": analysis.sample_size,
            "recommendation": "Price data is reliable" if confidence_level == "high" else "Price data is moderately reliable" if confidence_level == "medium" else "Price data is limited - consider professional valuation"
        }
    except Exception as e:
        logger.error(f"Price analysis error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/history")
async def get_price_history(
    variant_id: str = Query(..., description="Vehicle variant ID"),
    year: int = Query(..., description="Vehicle year"),
    months: int = Query(6, description="Number of months of history", ge=1, le=24)
) -> Dict:
    """
    Get price history for trend analysis.
    
    Returns:
    - Historical price data points
    - Price trend direction (up/down/stable)
    - Percentage change over the period
    """
    try:
        history = await supabase_service.get_price_history(variant_id, year, months)
        
        if not history:
            return {
                "status": "no_data",
                "message": "No historical data available",
                "variant_id": variant_id,
                "year": year
            }
        
        # Calculate trend
        prices = [h['price_kes'] for h in history]
        
        if len(prices) >= 2:
            first_price = prices[0]
            last_price = prices[-1]
            
            if first_price > 0:
                percentage_change = ((last_price - first_price) / first_price) * 100
            else:
                percentage_change = 0
            
            if percentage_change > 5:
                trend = "up"
                trend_description = "📈 Prices are increasing"
            elif percentage_change < -5:
                trend = "down"
                trend_description = "📉 Prices are decreasing"
            else:
                trend = "stable"
                trend_description = "➡️ Prices are stable"
        else:
            trend = "insufficient_data"
            trend_description = "⚠️ Not enough data for trend analysis"
            percentage_change = 0
        
        return {
            "status": "success",
            "variant_id": variant_id,
            "year": year,
            "history": history,
            "trend": trend,
            "trend_description": trend_description,
            "percentage_change": round(percentage_change, 2),
            "data_points": len(history),
            "first_price": prices[0] if prices else None,
            "last_price": prices[-1] if prices else None
        }
    except Exception as e:
        logger.error(f"Error fetching price history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/trend")
async def get_price_trend(
    variant_id: str = Query(..., description="Vehicle variant ID"),
    year: int = Query(..., description="Vehicle year")
) -> Dict:
    """
    Get detailed price trend analysis including seasonality.
    
    Returns:
    - Monthly trend data
    - Seasonal patterns
    - Peak and low months
    """
    try:
        # Get 12 months of data for seasonality
        trend_data = await supabase_service.get_price_history(variant_id, year, 12)
        
        if len(trend_data) < 3:
            return {
                "status": "insufficient_data",
                "message": "Not enough historical data for trend analysis",
                "variant_id": variant_id,
                "year": year
            }
        
        # Calculate monthly averages
        monthly_avg = {}
        for record in trend_data:
            month = record['recorded_at'][:7]  # YYYY-MM
            if month not in monthly_avg:
                monthly_avg[month] = []
            monthly_avg[month].append(record['price_kes'])
        
        monthly_trend = {
            month: sum(prices) / len(prices) 
            for month, prices in sorted(monthly_avg.items())
        }
        
        # Calculate seasonality
        seasonality = await price_analyzer.calculate_seasonality(variant_id, year)
        
        # Calculate moving average (3-month)
        months = list(monthly_trend.keys())
        if len(months) >= 3:
            moving_avg = {}
            for i in range(2, len(months)):
                avg = (monthly_trend[months[i-2]] + monthly_trend[months[i-1]] + monthly_trend[months[i]]) / 3
                moving_avg[months[i]] = avg
        else:
            moving_avg = {}
        
        return {
            "status": "success",
            "variant_id": variant_id,
            "year": year,
            "monthly_trend": monthly_trend,
            "moving_average_3month": moving_avg,
            "seasonality": seasonality,
            "data_points": len(trend_data),
            "months_analyzed": len(monthly_trend)
        }
    except Exception as e:
        logger.error(f"Error calculating trend: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/distribution")
async def get_price_distribution(
    variant_id: str = Query(..., description="Vehicle variant ID"),
    year: int = Query(..., description="Vehicle year")
) -> Dict:
    """
    Get price distribution for a specific vehicle.
    
    Returns:
    - Price percentiles (10th, 25th, 50th, 75th, 90th)
    - Price bracket distribution
    """
    try:
        distribution = await price_analyzer.get_price_distribution(variant_id, year)
        
        if not distribution:
            return {
                "status": "no_data",
                "message": "No price data available for this vehicle",
                "variant_id": variant_id,
                "year": year
            }
        
        return {
            "status": "success",
            "variant_id": variant_id,
            "year": year,
            "distribution": distribution,
            "sample_size": distribution.get('sample_size', 0)
        }
    except Exception as e:
        logger.error(f"Error getting price distribution: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
