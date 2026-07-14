"""
Market Intelligence Engine - Auto-D Kenya
Market data and demand analysis
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MarketData:
    """Market data for a vehicle"""
    make: str = ""
    model: str = ""
    demand_score: float = 50.0
    popularity: float = 50.0
    resale_score: float = 50.0
    import_tax: float = 0.0
    market_trend: str = "stable"
    competition_count: int = 5


# ─── MARKET DATA ──────────────────────────────────────────────────

MARKET_DATA = {
    "toyota_prado": {
        "demand_score": 85,
        "popularity": 90,
        "resale_score": 88,
        "import_tax": 25,
        "market_trend": "up",
        "competition_count": 4
    },
    "toyota_hilux": {
        "demand_score": 82,
        "popularity": 88,
        "resale_score": 85,
        "import_tax": 25,
        "market_trend": "stable",
        "competition_count": 5
    },
    "toyota_land_cruiser": {
        "demand_score": 90,
        "popularity": 92,
        "resale_score": 90,
        "import_tax": 35,
        "market_trend": "up",
        "competition_count": 2
    },
    "nissan_patrol": {
        "demand_score": 75,
        "popularity": 78,
        "resale_score": 72,
        "import_tax": 35,
        "market_trend": "down",
        "competition_count": 3
    },
    "bmw_x5": {
        "demand_score": 70,
        "popularity": 75,
        "resale_score": 65,
        "import_tax": 40,
        "market_trend": "down",
        "competition_count": 6
    },
    "mercedes_glc": {
        "demand_score": 72,
        "popularity": 76,
        "resale_score": 68,
        "import_tax": 40,
        "market_trend": "stable",
        "competition_count": 5
    },
    "ford_ranger": {
        "demand_score": 78,
        "popularity": 82,
        "resale_score": 76,
        "import_tax": 25,
        "market_trend": "up",
        "competition_count": 4
    },
    "isuzu_dmax": {
        "demand_score": 76,
        "popularity": 80,
        "resale_score": 74,
        "import_tax": 25,
        "market_trend": "stable",
        "competition_count": 4
    }
}

DEFAULT_MARKET_DATA = {
    "demand_score": 50,
    "popularity": 50,
    "resale_score": 50,
    "import_tax": 25,
    "market_trend": "stable",
    "competition_count": 5
}


class MarketIntelligenceEngine:
    """Professional market intelligence engine"""
    
    @staticmethod
    def get_market_data(make: str = "", model: str = "") -> Dict[str, Any]:
        """
        Get market data for a vehicle.
        
        Args:
            make: Vehicle make
            model: Vehicle model
        
        Returns:
            Dict with market data
        """
        if make and model:
            key = f"{make}_{model}".lower().replace(" ", "_")
            data = MARKET_DATA.get(key)
            if data:
                return data
        
        return DEFAULT_MARKET_DATA.copy()
    
    @staticmethod
    def calculate_demand_multiplier(make: str = "", model: str = "") -> float:
        """
        Calculate demand multiplier for valuation.
        
        Returns:
            Float between 0.8 and 1.2
        """
        data = MarketIntelligenceEngine.get_market_data(make, model)
        demand_score = data.get("demand_score", 50)
        
        # Convert demand score to multiplier (50 = 1.0)
        multiplier = 0.8 + (demand_score / 250)
        
        return round(min(max(multiplier, 0.8), 1.2), 3)
    
    @staticmethod
    def get_market_trend(make: str = "", model: str = "") -> str:
        """
        Get market trend for a vehicle.
        
        Returns:
            'up', 'down', or 'stable'
        """
        data = MarketIntelligenceEngine.get_market_data(make, model)
        return data.get("market_trend", "stable")
    
    @staticmethod
    def compare_vehicles(
        vehicle1: Dict[str, Any],
        vehicle2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare market position of two vehicles.
        
        Returns:
            Dict with comparison results
        """
        make1 = vehicle1.get("make", "")
        model1 = vehicle1.get("model", "")
        make2 = vehicle2.get("make", "")
        model2 = vehicle2.get("model", "")
        
        data1 = MarketIntelligenceEngine.get_market_data(make1, model1)
        data2 = MarketIntelligenceEngine.get_market_data(make2, model2)
        
        return {
            "vehicle1": {
                "name": f"{make1} {model1}",
                "demand_score": data1.get("demand_score", 50),
                "popularity": data1.get("popularity", 50),
                "resale_score": data1.get("resale_score", 50),
                "trend": data1.get("market_trend", "stable")
            },
            "vehicle2": {
                "name": f"{make2} {model2}",
                "demand_score": data2.get("demand_score", 50),
                "popularity": data2.get("popularity", 50),
                "resale_score": data2.get("resale_score", 50),
                "trend": data2.get("market_trend", "stable")
            },
            "recommendation": "Vehicle 1 has better market position" 
                if data1.get("demand_score", 0) > data2.get("demand_score", 0)
                else "Vehicle 2 has better market position"
        }


def get_market_data(make: str = "", model: str = "") -> Dict[str, Any]:
    """Convenience function for market data"""
    return MarketIntelligenceEngine.get_market_data(make, model)


def get_demand_multiplier(make: str = "", model: str = "") -> float:
    """Convenience function for demand multiplier"""
    return MarketIntelligenceEngine.calculate_demand_multiplier(make, model)


# ─── EXAMPLE USAGE ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("📊 Market Intelligence Engine")
    print("=" * 60)
    
    # Example: Toyota Prado
    data = get_market_data("Toyota", "Prado")
    print(f"\n🚗 Toyota Prado:")
    print(f"  Demand Score: {data.get('demand_score', 50)}")
    print(f"  Popularity: {data.get('popularity', 50)}")
    print(f"  Resale Score: {data.get('resale_score', 50)}")
    print(f"  Trend: {data.get('market_trend', 'stable')}")
    print(f"  Demand Multiplier: {get_demand_multiplier('Toyota', 'Prado')}")
    
    print("\n" + "=" * 60)
