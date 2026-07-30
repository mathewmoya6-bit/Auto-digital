# app/modules/market/pricing.py
# Auto-D Kenya - Pricing Engine
# ================================================================
# TYPE: MODULE - Pricing algorithms

import logging
from typing import List, Dict, Any
from statistics import mean, median, stdev

logger = logging.getLogger(__name__)


class PricingEngine:
    """Pricing engine for market price calculations."""
    
    def __init__(self):
        self.confidence_threshold = 0.5
        self.min_sample_size = 3
    
    def calculate_average_price(self, prices: List[float]) -> float:
        """Calculate average price."""
        if not prices:
            return 0
        return sum(prices) / len(prices)
    
    def calculate_median_price(self, prices: List[float]) -> float:
        """Calculate median price."""
        if not prices:
            return 0
        return median(prices)
    
    def calculate_confidence_score(self, prices: List[float]) -> float:
        """Calculate confidence score based on price consistency."""
        if len(prices) < self.min_sample_size:
            return 0.3
        
        if len(prices) == 1:
            return 0.5
        
        avg = mean(prices)
        if avg == 0:
            return 0
        
        # Calculate coefficient of variation
        if len(prices) > 1:
            std = stdev(prices)
            cv = std / avg if avg > 0 else 1
        else:
            cv = 0.5
        
        # Confidence decreases with higher variation
        confidence = 1 - min(cv, 1)
        
        # Adjust for sample size
        size_factor = min(len(prices) / 20, 1)
        confidence = (confidence * 0.7) + (size_factor * 0.3)
        
        return max(0.3, min(0.95, confidence))
    
    def get_price_range(self, prices: List[float]) -> Dict[str, float]:
        """Get price range (min, max)."""
        if not prices:
            return {"min": 0, "max": 0}
        return {"min": min(prices), "max": max(prices)}
    
    def detect_outliers(self, prices: List[float], threshold: float = 2.0) -> List[float]:
        """Detect outliers in price data."""
        if len(prices) < 4:
            return []
        
        avg = mean(prices)
        std = stdev(prices) if len(prices) > 1 else 0
        
        if std == 0:
            return []
        
        outliers = []
        for price in prices:
            if abs(price - avg) > threshold * std:
                outliers.append(price)
        
        return outliers
    
    def clean_prices(self, prices: List[float]) -> List[float]:
        """Remove outliers from price data."""
        if len(prices) < 4:
            return prices
        
        outliers = self.detect_outliers(prices)
        return [p for p in prices if p not in outliers]
    
    def calculate_market_value(
        self,
        prices: List[float],
        use_median: bool = True
    ) -> Dict[str, Any]:
        """Calculate market value from price data."""
        if not prices:
            return {
                "value": 0,
                "confidence": 0,
                "sample_size": 0,
                "range": {"min": 0, "max": 0}
            }
        
        cleaned_prices = self.clean_prices(prices)
        
        if use_median:
            value = self.calculate_median_price(cleaned_prices)
        else:
            value = self.calculate_average_price(cleaned_prices)
        
        confidence = self.calculate_confidence_score(cleaned_prices)
        price_range = self.get_price_range(cleaned_prices)
        
        return {
            "value": round(value, 2),
            "confidence": round(confidence, 2),
            "sample_size": len(cleaned_prices),
            "original_size": len(prices),
            "range": {
                "min": round(price_range["min"], 2),
                "max": round(price_range["max"], 2)
            }
        }
