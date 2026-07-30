# app/modules/market/statistics.py
# Auto-D Kenya - Market Statistics
# ================================================================
# TYPE: MODULE - Market statistical analysis

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class MarketStatistics:
    """Market statistics and analysis."""
    
    def __init__(self):
        self.supabase = get_supabase()
    
    async def calculate_trends(self, make: str, model: str, period: str = "90d") -> Dict[str, Any]:
        """Calculate market trends for a vehicle."""
        try:
            # Calculate date range
            days = int(period.replace("d", ""))
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get historical data
            response = self.supabase.table("market_prices").select("*").eq("make", make).eq("model", model).gte("updated_at", start_date.isoformat()).execute()
            
            data = response.data
            
            if not data:
                return {
                    "make": make,
                    "model": model,
                    "period": period,
                    "trend": "insufficient_data",
                    "message": "Not enough data for trend analysis"
                }
            
            # Calculate trend
            sorted_data = sorted(data, key=lambda x: x.get("updated_at", ""))
            prices = [float(item.get("avg_price", 0)) for item in sorted_data if item.get("avg_price")]
            
            if len(prices) < 2:
                return {
                    "make": make,
                    "model": model,
                    "period": period,
                    "trend": "insufficient_data",
                    "message": "Not enough data points"
                }
            
            # Calculate trend direction
            first_price = prices[0]
            last_price = prices[-1]
            percent_change = ((last_price - first_price) / first_price * 100) if first_price > 0 else 0
            
            if percent_change > 5:
                trend = "increasing"
            elif percent_change < -5:
                trend = "decreasing"
            else:
                trend = "stable"
            
            return {
                "make": make,
                "model": model,
                "period": period,
                "data_points": len(prices),
                "first_price": round(first_price, 2),
                "last_price": round(last_price, 2),
                "percent_change": round(percent_change, 2),
                "trend": trend,
                "average_price": round(sum(prices) / len(prices), 2) if prices else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating trends: {str(e)}")
            return {"error": str(e)}
    
    async def get_price_distribution(self, make: str, model: str) -> Dict[str, Any]:
        """Get price distribution for a vehicle model."""
        try:
            response = self.supabase.table("market_prices").select("*").eq("make", make).eq("model", model).execute()
            data = response.data
            
            if not data:
                return {"message": "No data found"}
            
            prices = [float(item.get("avg_price", 0)) for item in data if item.get("avg_price")]
            
            if not prices:
                return {"message": "No price data found"}
            
            # Create distribution bins
            min_price = min(prices)
            max_price = max(prices)
            range_size = max_price - min_price
            
            if range_size == 0:
                return {
                    "make": make,
                    "model": model,
                    "distribution": [{"range": f"KES {min_price:,.0f}", "count": len(prices), "percentage": 100}]
                }
            
            # Create 5 bins
            bin_size = range_size / 5
            bins = defaultdict(int)
            
            for price in prices:
                bin_index = min(int((price - min_price) / bin_size), 4)
                bin_key = f"KES {min_price + bin_index * bin_size:,.0f} - {min_price + (bin_index + 1) * bin_size:,.0f}"
                bins[bin_key] += 1
            
            distribution = []
            total = len(prices)
            for bin_key, count in bins.items():
                distribution.append({
                    "range": bin_key,
                    "count": count,
                    "percentage": round((count / total) * 100, 1)
                })
            
            return {
                "make": make,
                "model": model,
                "distribution": sorted(distribution, key=lambda x: x["range"]),
                "total_listings": total
            }
            
        except Exception as e:
            logger.error(f"Error getting price distribution: {str(e)}")
            return {"error": str(e)}
