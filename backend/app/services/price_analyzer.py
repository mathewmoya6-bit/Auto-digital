# app/services/price_analyzer.py
import statistics
from typing import List, Dict, Optional
from datetime import datetime
import logging
from app.services.supabase_service import SupabaseService
from app.models.price import PriceAnalysis, AlignedPrice, PriceSource

logger = logging.getLogger(__name__)

class PriceAnalyzer:
    def __init__(self, supabase_service: SupabaseService):
        self.supabase = supabase_service
        
        # Source weights for confidence calculation
        self.source_weights = {
            PriceSource.JIJI.value: 1.0,      # Highest volume
            PriceSource.CHEKI.value: 0.9,     # Dealer pricing
            PriceSource.AUTOCHEK.value: 0.85, # Inspected vehicles
            PriceSource.BEEPBEEP.value: 0.7,  # Secondary
            PriceSource.PIGIAME.value: 0.6,   # Secondary
        }

    async def analyze_prices(self, variant_id: str, year: int) -> Optional[PriceAnalysis]:
        """Analyze market prices for a vehicle"""
        # Get all market prices for this variant and year
        market_prices = await self.supabase.get_market_prices(variant_id, year, limit=100)
        
        if not market_prices or len(market_prices) < 3:
            return None
        
        # Extract prices
        prices = [p['price_kes'] for p in market_prices]
        
        # Remove outliers using IQR method
        prices_clean = self._remove_outliers(prices)
        
        if len(prices_clean) < 3:
            prices_clean = prices  # Fallback to all prices
        
        # Calculate statistics
        median_price = int(statistics.median(prices_clean))
        average_price = int(statistics.mean(prices_clean))
        min_price = min(prices_clean)
        max_price = max(prices_clean)
        std_dev = statistics.stdev(prices_clean) if len(prices_clean) > 1 else 0
        
        # Calculate confidence score
        confidence = self._calculate_confidence(prices_clean, market_prices)
        
        # Source breakdown
        source_breakdown = {}
        for p in market_prices:
            source = p.get('source', 'unknown')
            source_breakdown[source] = source_breakdown.get(source, 0) + 1
        
        return PriceAnalysis(
            variant_id=variant_id,
            year=year,
            sample_size=len(prices_clean),
            median_price=median_price,
            average_price=average_price,
            min_price=min_price,
            max_price=max_price,
            standard_deviation=std_dev,
            confidence_score=confidence,
            price_range={
                'min': min_price,
                'max': max_price,
                'median': median_price,
                'average': average_price
            },
            adjusted_price=median_price,  # Will be adjusted by aligner
            factors_applied={},
            source_breakdown=source_breakdown
        )

    def _remove_outliers(self, prices: List[int]) -> List[int]:
        """Remove outliers using IQR method"""
        if len(prices) < 4:
            return prices
        
        sorted_prices = sorted(prices)
        q1 = sorted_prices[len(sorted_prices) // 4]
        q3 = sorted_prices[3 * len(sorted_prices) // 4]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        return [p for p in prices if lower_bound <= p <= upper_bound]

    def _calculate_confidence(self, prices: List[int], all_prices: List[Dict]) -> float:
        """Calculate confidence score based on data quality"""
        if len(prices) < 3:
            return 0.3
        
        # Sample size factor
        sample_size_factor = min(1.0, len(prices) / 30)
        
        # Price consistency factor (lower std dev = higher confidence)
        if len(prices) > 1:
            avg = statistics.mean(prices)
            std_dev = statistics.stdev(prices)
            cv = std_dev / avg if avg > 0 else 1  # Coefficient of variation
            consistency_factor = max(0, 1 - cv)
        else:
            consistency_factor = 0.5
        
        # Source diversity factor
        sources = set(p.get('source', 'unknown') for p in all_prices)
        source_factor = min(1.0, len(sources) / 3)
        
        # Recency factor (newer prices weighted more)
        now = datetime.now()
        recency_scores = []
        for p in all_prices:
            recorded_at = datetime.fromisoformat(p['recorded_at'].replace('Z', '+00:00'))
            days_ago = (now - recorded_at).days
            score = max(0, 1 - (days_ago / 90))  # 90-day half-life
            recency_scores.append(score)
        recency_factor = statistics.mean(recency_scores) if recency_scores else 0.5
        
        # Weighted confidence
        confidence = (
            sample_size_factor * 0.3 +
            consistency_factor * 0.3 +
            source_factor * 0.2 +
            recency_factor * 0.2
        )
        
        return round(min(0.95, max(0.3, confidence)), 2)
