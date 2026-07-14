"""
Report Engine - Auto-D Kenya
PDF and CSV report generation
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Report:
    """Report data structure"""
    report_id: str = ""
    generated_at: str = ""
    report_type: str = ""
    data: Dict[str, Any] = None
    metadata: Dict[str, Any] = None


class ReportEngine:
    """Professional report generation engine"""
    
    @staticmethod
    def generate_report_id(report_type: str = "report") -> str:
        """Generate a unique report ID"""
        timestamp = datetime.now().strftime("%Y%m%d")
        random_suffix = datetime.now().strftime("%f")[-4:]
        return f"AD-{report_type.upper()}-{timestamp}-{random_suffix}"
    
    @staticmethod
    def create_valuation_report(
        valuation_data: Dict[str, Any],
        vehicle_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a valuation report.
        
        Args:
            valuation_data: Valuation results
            vehicle_data: Vehicle information
        
        Returns:
            Dict with report data
        """
        report_id = ReportEngine.generate_report_id("VAL")
        
        return {
            "report_id": report_id,
            "report_type": "valuation",
            "generated_at": datetime.now().isoformat(),
            "certificate": {
                "verified": True,
                "verified_by": "Auto-D Intelligence Engine",
                "method": "AI-powered market analysis"
            },
            "data": {
                "vehicle": vehicle_data,
                "valuation": valuation_data
            },
            "summary": {
                "current_value": valuation_data.get("current_value", 0),
                "confidence_score": valuation_data.get("confidence_score", 85),
                "valuation_method": "AI-powered market valuation",
                "total_depreciation": valuation_data.get("total_depreciation", 0),
                "value_retained": valuation_data.get("value_retained", 0)
            },
            "disclaimer": "This valuation is an estimate based on current market data. Actual market value may vary."
        }
    
    @staticmethod
    def create_ownership_report(
        ownership_data: Dict[str, Any],
        vehicle_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create an ownership cost report.
        
        Args:
            ownership_data: Ownership cost results
            vehicle_data: Vehicle information
        
        Returns:
            Dict with report data
        """
        report_id = ReportEngine.generate_report_id("OWN")
        
        return {
            "report_id": report_id,
            "report_type": "ownership",
            "generated_at": datetime.now().isoformat(),
            "data": {
                "vehicle": vehicle_data,
                "ownership": ownership_data
            },
            "summary": {
                "total_cost": ownership_data.get("total_cost", 0),
                "annual_cost": ownership_data.get("annual_cost", 0),
                "cost_per_km": ownership_data.get("cost_per_km", 0),
                "resale_value": ownership_data.get("resale_value", 0)
            }
        }
    
    @staticmethod
    def create_mileage_report(
        mileage_data: Dict[str, Any],
        vehicle_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a mileage report.
        
        Args:
            mileage_data: Mileage calculation results
            vehicle_data: Vehicle information
        
        Returns:
            Dict with report data
        """
        report_id = ReportEngine.generate_report_id("MIL")
        
        return {
            "report_id": report_id,
            "report_type": "mileage",
            "generated_at": datetime.now().isoformat(),
            "data": {
                "vehicle": vehicle_data,
                "mileage": mileage_data
            },
            "summary": {
                "total_cost": mileage_data.get("total_cost", 0),
                "cost_per_km": mileage_data.get("cost_per_km", 0),
                "distance_km": mileage_data.get("distance_km", 0),
                "fuel_cost": mileage_data.get("fuel_cost", 0)
            }
        }
    
    @staticmethod
    def to_csv(data: Dict[str, Any], filename: str = None) -> str:
        """
        Convert report data to CSV format.
        
        Args:
            data: Report data
            filename: Optional filename (not used in return)
        
        Returns:
            CSV string
        """
        lines = []
        
        # Header
        lines.append("Metric,Value")
        
        # Flatten data
        def flatten_dict(d, prefix=""):
            items = []
            for key, value in d.items():
                if isinstance(value, dict):
                    items.extend(flatten_dict(value, f"{prefix}{key}."))
                else:
                    items.append((f"{prefix}{key}", value))
            return items
        
        for key, value in flatten_dict(data):
            lines.append(f"{key},{value}")
        
        return "\n".join(lines)
    
    @staticmethod
    def to_markdown(data: Dict[str, Any]) -> str:
        """
        Convert report data to Markdown format.
        
        Args:
            data: Report data
        
        Returns:
            Markdown string
        """
        lines = []
        lines.append(f"# Auto-D Kenya Report")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        
        def render_dict(d, indent=0):
            for key, value in d.items():
                if isinstance(value, dict):
                    lines.append(f"{' ' * indent}- **{key}:**")
                    render_dict(value, indent + 2)
                else:
                    lines.append(f"{' ' * indent}- **{key}:** {value}")
        
        # Render summary if it exists, otherwise render the whole data
        if "summary" in data:
            render_dict(data.get("summary", {}))
        else:
            render_dict(data)
        
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*Generated by Auto-D Kenya*")
        
        return "\n".join(lines)
    
    @staticmethod
    def to_json(data: Dict[str, Any]) -> str:
        """
        Convert report data to JSON format.
        
        Args:
            data: Report data
        
        Returns:
            JSON string
        """
        return json.dumps(data, indent=2, default=str)
    
    @staticmethod
    def get_report_types() -> List[str]:
        """
        Get available report types.
        
        Returns:
            List of report types
        """
        return ["valuation", "ownership", "mileage", "general"]


def generate_report(
    data: Dict[str, Any], 
    report_type: str = "valuation"
) -> Dict[str, Any]:
    """
    Convenience function for report generation.
    
    Args:
        data: Report data
        report_type: Type of report (valuation, ownership, mileage, general)
    
    Returns:
        Dict with report data
    """
    engine = ReportEngine()
    
    if report_type == "valuation":
        return engine.create_valuation_report(
            valuation_data=data.get("valuation", {}),
            vehicle_data=data.get("vehicle", {})
        )
    elif report_type == "ownership":
        return engine.create_ownership_report(
            ownership_data=data.get("ownership", {}),
            vehicle_data=data.get("vehicle", {})
        )
    elif report_type == "mileage":
        return engine.create_mileage_report(
            mileage_data=data.get("mileage", {}),
            vehicle_data=data.get("vehicle", {})
        )
    else:
        return {
            "report_id": ReportEngine.generate_report_id("GEN"),
            "report_type": "general",
            "generated_at": datetime.now().isoformat(),
            "data": data,
            "summary": {}
        }


# ─── EXAMPLE USAGE ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("📄 Report Engine")
    print("=" * 60)
    
    # Example valuation report
    report = generate_report({
        "valuation": {
            "current_value": 3450000,
            "confidence_score": 92,
            "total_depreciation": 1750000,
            "value_retained": 66.35
        },
        "vehicle": {
            "make": "Toyota",
            "model": "Prado",
            "year": 2020,
            "condition": "Good",
            "mileage": 45000
        }
    }, report_type="valuation")
    
    print(f"\n📋 Report ID: {report['report_id']}")
    print(f"📊 Type: {report['report_type']}")
    print(f"📅 Generated: {report['generated_at']}")
    print(f"💰 Value: KES {report['summary']['current_value']:,.2f}")
    print(f"🎯 Confidence: {report['summary']['confidence_score']}%")
    
    # Example CSV output
    print("\n📊 CSV Preview:")
    csv_output = ReportEngine.to_csv(report)
    print(csv_output[:200] + "...")
    
    # Example Markdown output
    print("\n📝 Markdown Preview:")
    markdown_output = ReportEngine.to_markdown(report)
    print(markdown_output[:200] + "...")
    
    print("\n" + "=" * 60)
