# app/services/report_generator.py

"""
Report Generator Service
Generates vehicle valuation reports in multiple formats:
- PDF (via ReportLab)
- HTML
- JSON
- CSV
- Markdown
Production Grade - Auto-D Kenya
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
import json
import logging
import io
import base64
import csv
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ─── Enums ──────────────────────────────────────────────────────────

class ReportFormat(str, Enum):
    """Supported report formats."""
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "md"


class ReportSection(str, Enum):
    """Report sections."""
    SUMMARY = "summary"
    VEHICLE_INFO = "vehicle_info"
    VALUATION = "valuation"
    COMPARABLES = "comparables"
    ADJUSTMENTS = "adjustments"
    RECOMMENDATIONS = "recommendations"
    DISCLAIMER = "disclaimer"
    APPENDIX = "appendix"


# ─── Data Models ──────────────────────────────────────────────────

@dataclass
class ReportData:
    """Report data structure."""
    vehicle: Dict[str, Any]
    valuation: Dict[str, Any]
    comparables: Optional[List[Dict]] = None
    adjustments: Optional[Dict] = None
    recommendations: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "vehicle": self.vehicle,
            "valuation": self.valuation,
            "comparables": self.comparables or [],
            "adjustments": self.adjustments or {},
            "recommendations": self.recommendations or [],
            "metadata": self.metadata,
            "generated_at": self.generated_at
        }


class ReportGenerator:
    """Generate vehicle valuation reports in multiple formats."""
    
    def __init__(self):
        """Initialize the report generator with styles."""
        self.reportlab_available = False
        
        # Try to import reportlab
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape, letter
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                PageBreak, Image, KeepTogether, Preformatted
            )
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch, cm
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
            from reportlab.pdfgen import canvas
            
            self.colors = colors
            self.A4 = A4
            self.landscape = landscape
            self.letter = letter
            self.SimpleDocTemplate = SimpleDocTemplate
            self.Paragraph = Paragraph
            self.Spacer = Spacer
            self.Table = Table
            self.TableStyle = TableStyle
            self.PageBreak = PageBreak
            self.Image = Image
            self.KeepTogether = KeepTogether
            self.Preformatted = Preformatted
            self.getSampleStyleSheet = getSampleStyleSheet
            self.ParagraphStyle = ParagraphStyle
            self.inch = inch
            self.cm = cm
            self.TA_CENTER = TA_CENTER
            self.TA_RIGHT = TA_RIGHT
            self.TA_LEFT = TA_LEFT
            self.TA_JUSTIFY = TA_JUSTIFY
            
            # Initialize styles
            self._init_styles()
            self.reportlab_available = True
            logger.info("✅ ReportLab loaded successfully - PDF reports available")
        except ImportError as e:
            logger.warning(f"⚠️ ReportLab not available - PDF reports disabled: {e}")
    
    # ─── Style Initialization ──────────────────────────────────────
    
    def _init_styles(self):
        """Initialize report styles."""
        if not self.reportlab_available:
            return
        
        self.styles = self.getSampleStyleSheet()
        self.primary_color = self.colors.HexColor('#1a56db')
        self.secondary_color = self.colors.HexColor('#059669')
        self.accent_color = self.colors.HexColor('#eab308')
        self.danger_color = self.colors.HexColor('#dc2626')
        self.text_color = self.colors.HexColor('#1f2937')
        self.text_muted = self.colors.HexColor('#6b7280')
        
        # Add custom styles
        self.styles.add(self.ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            textColor=self.primary_color,
            alignment=self.TA_CENTER,
            spaceAfter=30,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(self.ParagraphStyle(
            name='ReportSubtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=self.text_muted,
            alignment=self.TA_CENTER,
            spaceAfter=20
        ))
        
        self.styles.add(self.ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=18,
            textColor=self.primary_color,
            spaceAfter=15,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(self.ParagraphStyle(
            name='SubSectionHeading',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=self.text_color,
            spaceAfter=10,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(self.ParagraphStyle(
            name='BodyText',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.text_color,
            spaceAfter=8,
            alignment=self.TA_JUSTIFY
        ))
        
        self.styles.add(self.ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=self.text_muted,
            spaceAfter=4
        ))
        
        self.styles.add(self.ParagraphStyle(
            name='ValueText',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=self.secondary_color,
            fontName='Helvetica-Bold',
            alignment=self.TA_RIGHT
        ))
        
        self.styles.add(self.ParagraphStyle(
            name='Disclaimer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=self.text_muted,
            alignment=self.TA_LEFT,
            spaceAfter=10,
            fontName='Helvetica-Oblique'
        ))
    
    # ─── Number Formatting ─────────────────────────────────────────
    
    def _format_kes(self, value: Any) -> str:
        """Format value as KES currency."""
        if value is None:
            return "KES 0"
        try:
            return f"KES {int(value):,}"
        except (ValueError, TypeError):
            return f"KES {value}"
    
    def _format_percentage(self, value: Any) -> str:
        """Format value as percentage."""
        if value is None:
            return "0%"
        try:
            return f"{float(value) * 100:.1f}%"
        except (ValueError, TypeError):
            return f"{value}%"
    
    def _format_date(self, date_str: Optional[str]) -> str:
        """Format date string."""
        if not date_str:
            return "N/A"
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%B %d, %Y")
        except:
            return date_str
    
    # ─── Report Section Builders ──────────────────────────────────
    
    def _create_header(self, title: str, subtitle: Optional[str] = None) -> List:
        """Create report header."""
        if not self.reportlab_available:
            return []
        
        elements = []
        elements.append(self.Paragraph(title, self.styles['ReportTitle']))
        if subtitle:
            elements.append(self.Paragraph(subtitle, self.styles['ReportSubtitle']))
        elements.append(self.Spacer(1, 20))
        return elements
    
    def _create_vehicle_info_section(self, vehicle: Dict) -> List:
        """Create vehicle information section."""
        if not self.reportlab_available:
            return []
        
        elements = []
        elements.append(self.Paragraph("Vehicle Information", self.styles['SectionHeading']))
        
        data = [
            ['Make', vehicle.get('make', 'N/A')],
            ['Model', vehicle.get('model', 'N/A')],
            ['Variant', vehicle.get('variant', 'N/A')],
            ['Year', str(vehicle.get('year', 'N/A'))],
            ['Engine', f"{vehicle.get('engine_cc', 'N/A')} cc"],
            ['Fuel Type', vehicle.get('fuel_type', 'N/A')],
            ['Transmission', vehicle.get('transmission', 'N/A')],
            ['Mileage', f"{vehicle.get('mileage', 'N/A')} km"],
            ['Condition', vehicle.get('condition', 'N/A')]
        ]
        
        table = self.Table(data, colWidths=[2*self.inch, 4*self.inch])
        table.setStyle(self.TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), self.colors.white),
            ('GRID', (0, 0), (-1, -1), 1, self.colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.colors.whitesmoke, self.colors.white]),
        ]))
        
        elements.append(table)
        elements.append(self.Spacer(1, 10))
        return elements
    
    def _create_valuation_section(self, valuation: Dict) -> List:
        """Create valuation section."""
        if not self.reportlab_available:
            return []
        
        elements = []
        elements.append(self.Paragraph("Valuation Results", self.styles['SectionHeading']))
        
        market_value = valuation.get('market_value', 0)
        retail_value = valuation.get('retail_value', 0)
        trade_value = valuation.get('trade_value', 0)
        confidence = valuation.get('confidence_score', 0)
        
        # Calculate range
        min_price = int(market_value * 0.92)
        max_price = int(market_value * 1.08)
        
        data = [
            ['Metric', 'Value'],
            ['Market Value', self._format_kes(market_value)],
            ['Retail Value', self._format_kes(retail_value)],
            ['Trade Value', self._format_kes(trade_value)],
            ['Expected Range', f"{self._format_kes(min_price)} - {self._format_kes(max_price)}"],
            ['Confidence Score', self._format_percentage(confidence)],
        ]
        
        # Add additional fields if present
        if 'depreciation_rate' in valuation:
            data.append(['Depreciation Rate', self._format_percentage(valuation.get('depreciation_rate'))])
        if 'estimated_life' in valuation:
            data.append(['Estimated Life', f"{valuation.get('estimated_life')} years"])
        
        table = self.Table(data, colWidths=[2.5*self.inch, 3.5*self.inch])
        table.setStyle(self.TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), self.colors.white),
            ('GRID', (0, 0), (-1, -1), 1, self.colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.colors.whitesmoke, self.colors.white]),
        ]))
        
        elements.append(table)
        elements.append(self.Spacer(1, 10))
        return elements
    
    def _create_adjustments_section(self, adjustments: Dict) -> List:
        """Create adjustments section."""
        if not self.reportlab_available or not adjustments:
            return []
        
        elements = []
        elements.append(self.Paragraph("Value Adjustments", self.styles['SectionHeading']))
        
        data = [['Factor', 'Adjustment', 'Effect']]
        for key, value in adjustments.items():
            if isinstance(value, dict):
                factor = value.get('name', key)
                adjustment = self._format_percentage(value.get('percentage', 0))
                effect = value.get('effect', 'neutral')
                data.append([factor, adjustment, effect])
            else:
                data.append([key.replace('_', ' ').title(), self._format_percentage(value), 'Applied'])
        
        if len(data) > 1:
            table = self.Table(data, colWidths=[2.5*self.inch, 1.5*self.inch, 2*self.inch])
            table.setStyle(self.TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), self.colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), self.colors.white),
                ('GRID', (0, 0), (-1, -1), 1, self.colors.lightgrey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.colors.whitesmoke, self.colors.white]),
            ]))
            elements.append(table)
            elements.append(self.Spacer(1, 10))
        else:
            elements.append(self.Paragraph("No significant adjustments applied.", self.styles['BodyText']))
        
        return elements
    
    def _create_recommendations_section(self, recommendations: List[str]) -> List:
        """Create recommendations section."""
        if not self.reportlab_available or not recommendations:
            return []
        
        elements = []
        elements.append(self.Paragraph("Recommendations", self.styles['SectionHeading']))
        
        for rec in recommendations:
            elements.append(self.Paragraph(f"• {rec}", self.styles['BodyText']))
        
        elements.append(self.Spacer(1, 10))
        return elements
    
    def _create_comparables_section(self, comparables: List[Dict]) -> List:
        """Create comparables section."""
        if not self.reportlab_available or not comparables:
            return []
        
        elements = []
        elements.append(self.Paragraph("Comparable Vehicles", self.styles['SectionHeading']))
        
        data = [['Make', 'Model', 'Year', 'Price', 'Source']]
        for c in comparables[:10]:
            data.append([
                c.get('make', 'N/A'),
                c.get('model', 'N/A'),
                str(c.get('year', 'N/A')),
                self._format_kes(c.get('price', 0)),
                c.get('source', 'Unknown')
            ])
        
        table = self.Table(data, colWidths=[1.5*self.inch, 1.5*self.inch, 1*self.inch, 1.5*self.inch, 1.5*self.inch])
        table.setStyle(self.TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), self.colors.white),
            ('GRID', (0, 0), (-1, -1), 1, self.colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.colors.whitesmoke, self.colors.white]),
        ]))
        
        elements.append(table)
        elements.append(self.Spacer(1, 10))
        return elements
    
    def _create_disclaimer(self) -> List:
        """Create disclaimer section."""
        if not self.reportlab_available:
            return []
        
        elements = []
        disclaimer_text = """
        <b>Disclaimer:</b> This valuation is an estimate based on market data, vehicle specifications, 
        and condition factors. It should not be considered as a definitive appraisal. Actual market 
        prices may vary based on vehicle condition, location, demand, and other factors. 
        This report is for informational purposes only and does not constitute financial advice. 
        Auto-D Kenya does not guarantee the accuracy of this valuation and is not liable for 
        any decisions made based on this report.
        """
        elements.append(self.Paragraph(disclaimer_text, self.styles['Disclaimer']))
        elements.append(self.Spacer(1, 5))
        return elements
    
    def _create_footer(self) -> List:
        """Create report footer."""
        if not self.reportlab_available:
            return []
        
        elements = []
        footer_text = f"""
        Generated by Auto-D Kenya • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Report ID: {datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}
        """
        elements.append(self.Paragraph(footer_text, self.styles['SmallText']))
        return elements
    
    # ─── PDF Report Generation ────────────────────────────────────
    
    def generate_pdf_report(
        self,
        report_data: Union[Dict, ReportData],
        include_comparables: bool = True,
        include_adjustments: bool = True,
        include_recommendations: bool = True
    ) -> str:
        """
        Generate a PDF report and return as base64 string.
        
        Args:
            report_data: Report data dictionary or ReportData object
            include_comparables: Include comparable vehicles
            include_adjustments: Include value adjustments
            include_recommendations: Include recommendations
            
        Returns:
            Base64 encoded PDF string
        """
        if not self.reportlab_available:
            raise ImportError(
                "ReportLab is not installed. PDF reports are disabled. "
                "Install with: pip install reportlab"
            )
        
        # Convert to ReportData if needed
        if isinstance(report_data, dict):
            report_data = ReportData(
                vehicle=report_data.get('vehicle', {}),
                valuation=report_data.get('valuation', {}),
                comparables=report_data.get('comparables', []),
                adjustments=report_data.get('adjustments', {}),
                recommendations=report_data.get('recommendations', [])
            )
        
        buffer = io.BytesIO()
        doc = self.SimpleDocTemplate(
            buffer,
            pagesize=self.A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )
        
        # Build document
        story = []
        
        # Header
        vehicle = report_data.vehicle
        title = f"Vehicle Valuation Report"
        subtitle = f"{vehicle.get('make', '')} {vehicle.get('model', '')} {vehicle.get('variant', '')}".strip()
        story.extend(self._create_header(title, subtitle or "Vehicle Valuation"))
        
        # Vehicle Info
        story.extend(self._create_vehicle_info_section(vehicle))
        
        # Valuation
        story.extend(self._create_valuation_section(report_data.valuation))
        
        # Adjustments
        if include_adjustments and report_data.adjustments:
            story.extend(self._create_adjustments_section(report_data.adjustments))
        
        # Recommendations
        if include_recommendations and report_data.recommendations:
            story.extend(self._create_recommendations_section(report_data.recommendations))
        
        # Comparables
        if include_comparables and report_data.comparables:
            story.extend(self._create_comparables_section(report_data.comparables))
        
        # Disclaimer
        story.extend(self._create_disclaimer())
        
        # Footer
        story.extend(self._create_footer())
        
        # Build PDF
        doc.build(story)
        
        # Get PDF data and encode as base64
        pdf_data = buffer.getvalue()
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        buffer.close()
        
        return pdf_base64
    
    # ─── HTML Report Generation ──────────────────────────────────
    
    def generate_html_report(self, report_data: Union[Dict, ReportData]) -> str:
        """
        Generate an HTML report.
        
        Args:
            report_data: Report data dictionary or ReportData object
            
        Returns:
            HTML string
        """
        # Convert to dict if needed
        if isinstance(report_data, ReportData):
            report_data = report_data.to_dict()
        
        vehicle = report_data.get('vehicle', {})
        valuation = report_data.get('valuation', {})
        comparables = report_data.get('comparables', [])
        adjustments = report_data.get('adjustments', {})
        recommendations = report_data.get('recommendations', [])
        
        # Build comparables table
        comparables_html = ""
        if comparables:
            comparables_html = """
            <h2>Comparable Vehicles</h2>
            <table>
                <tr><th>Make</th><th>Model</th><th>Year</th><th>Price</th><th>Source</th></tr>
            """
            for c in comparables[:10]:
                comparables_html += f"""
                <tr>
                    <td>{c.get('make', 'N/A')}</td>
                    <td>{c.get('model', 'N/A')}</td>
                    <td>{c.get('year', 'N/A')}</td>
                    <td>{self._format_kes(c.get('price', 0))}</td>
                    <td>{c.get('source', 'Unknown')}</td>
                </tr>
                """
            comparables_html += "</table>"
        
        # Build adjustments table
        adjustments_html = ""
        if adjustments:
            adjustments_html = """
            <h2>Value Adjustments</h2>
            <table>
                <tr><th>Factor</th><th>Adjustment</th></tr>
            """
            for key, value in adjustments.items():
                if isinstance(value, dict):
                    factor = value.get('name', key)
                    adjustment = self._format_percentage(value.get('percentage', 0))
                else:
                    factor = key.replace('_', ' ').title()
                    adjustment = self._format_percentage(value)
                adjustments_html += f"""
                <tr>
                    <td>{factor}</td>
                    <td>{adjustment}</td>
                </tr>
                """
            adjustments_html += "</table>"
        
        # Build recommendations
        recommendations_html = ""
        if recommendations:
            recommendations_html = "<h2>Recommendations</h2><ul>"
            for rec in recommendations:
                recommendations_html += f"<li>{rec}</li>"
            recommendations_html += "</ul>"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Vehicle Valuation Report</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                    margin: 40px; 
                    color: #1f2937;
                    max-width: 900px;
                    margin: 40px auto;
                }}
                h1 {{ color: #1a56db; text-align: center; border-bottom: 3px solid #1a56db; padding-bottom: 10px; }}
                h2 {{ color: #374151; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; margin-top: 30px; }}
                .subtitle {{ text-align: center; color: #6b7280; font-size: 16px; margin-bottom: 30px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
                th, td {{ padding: 10px 12px; text-align: left; border: 1px solid #e5e7eb; }}
                th {{ background-color: #1a56db; color: white; font-weight: 600; }}
                tr:nth-child(even) {{ background-color: #f9fafb; }}
                .value {{ font-size: 22px; color: #059669; font-weight: bold; }}
                .disclaimer {{ 
                    font-size: 10px; 
                    color: #6b7280; 
                    margin-top: 40px; 
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                }}
                .footer {{
                    text-align: center;
                    font-size: 10px;
                    color: #9ca3af;
                    margin-top: 20px;
                }}
                .confidence {{
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-weight: 600;
                }}
                .confidence-high {{ background: #d1fae5; color: #065f46; }}
                .confidence-medium {{ background: #fef3c7; color: #92400e; }}
                .confidence-low {{ background: #fee2e2; color: #991b1b; }}
                ul {{ padding-left: 20px; }}
                li {{ margin: 5px 0; }}
                @media print {{
                    body {{ margin: 20px; }}
                    .no-print {{ display: none; }}
                }}
            </style>
        </head>
        <body>
            <h1>🚗 Vehicle Valuation Report</h1>
            <div class="subtitle">
                {vehicle.get('make', 'N/A')} {vehicle.get('model', 'N/A')} {vehicle.get('variant', '')}
                <br>
                <small>Report Date: {datetime.now(timezone.utc).strftime('%B %d, %Y')}</small>
            </div>
            
            <h2>Vehicle Information</h2>
            <table>
                <tr><td><strong>Make</strong></td><td>{vehicle.get('make', 'N/A')}</td></tr>
                <tr><td><strong>Model</strong></td><td>{vehicle.get('model', 'N/A')}</td></tr>
                <tr><td><strong>Variant</strong></td><td>{vehicle.get('variant', 'N/A')}</td></tr>
                <tr><td><strong>Year</strong></td><td>{vehicle.get('year', 'N/A')}</td></tr>
                <tr><td><strong>Engine</strong></td><td>{vehicle.get('engine_cc', 'N/A')} cc</td></tr>
                <tr><td><strong>Fuel Type</strong></td><td>{vehicle.get('fuel_type', 'N/A')}</td></tr>
                <tr><td><strong>Transmission</strong></td><td>{vehicle.get('transmission', 'N/A')}</td></tr>
                <tr><td><strong>Mileage</strong></td><td>{vehicle.get('mileage', 'N/A')} km</td></tr>
                <tr><td><strong>Condition</strong></td><td>{vehicle.get('condition', 'N/A')}</td></tr>
            </table>
            
            <h2>Valuation Results</h2>
            <table>
                <tr><td><strong>Market Value</strong></td><td class="value">{self._format_kes(valuation.get('market_value', 0))}</td></tr>
                <tr><td><strong>Retail Value</strong></td><td>{self._format_kes(valuation.get('retail_value', 0))}</td></tr>
                <tr><td><strong>Trade Value</strong></td><td>{self._format_kes(valuation.get('trade_value', 0))}</td></tr>
                <tr><td><strong>Expected Range</strong></td><td>{self._format_kes(int(valuation.get('market_value', 0) * 0.92))} - {self._format_kes(int(valuation.get('market_value', 0) * 1.08))}</td></tr>
                <tr><td><strong>Confidence Score</strong></td><td><span class="confidence confidence-{'high' if valuation.get('confidence_score', 0) > 0.8 else 'medium' if valuation.get('confidence_score', 0) > 0.5 else 'low'}">{self._format_percentage(valuation.get('confidence_score', 0))}</span></td></tr>
            </table>
            
            {adjustments_html}
            {recommendations_html}
            {comparables_html}
            
            <div class="disclaimer">
                <strong>Disclaimer:</strong> This valuation is an estimate based on market data and should not be 
                considered as a definitive appraisal. Actual market prices may vary based on vehicle condition, 
                location, demand, and other factors. This report is for informational purposes only.
            </div>
            
            <div class="footer">
                Generated by Auto-D Kenya • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC
            </div>
        </body>
        </html>
        """
        return html
    
    # ─── Other Formats ─────────────────────────────────────────────
    
    def generate_json_report(self, report_data: Union[Dict, ReportData]) -> str:
        """
        Generate a JSON report.
        
        Args:
            report_data: Report data dictionary or ReportData object
            
        Returns:
            JSON string
        """
        if isinstance(report_data, ReportData):
            report_data = report_data.to_dict()
        
        return json.dumps(report_data, indent=2, default=str)
    
    def generate_csv_report(self, report_data: Union[Dict, ReportData]) -> str:
        """
        Generate a CSV report.
        
        Args:
            report_data: Report data dictionary or ReportData object
            
        Returns:
            CSV string
        """
        if isinstance(report_data, ReportData):
            report_data = report_data.to_dict()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Make', 'Model', 'Variant', 'Year', 'Mileage', 'Condition',
            'Market Value', 'Retail Value', 'Trade Value', 'Confidence Score'
        ])
        
        # Write data
        vehicle = report_data.get('vehicle', {})
        valuation = report_data.get('valuation', {})
        writer.writerow([
            vehicle.get('make', 'N/A'),
            vehicle.get('model', 'N/A'),
            vehicle.get('variant', 'N/A'),
            vehicle.get('year', 'N/A'),
            vehicle.get('mileage', 'N/A'),
            vehicle.get('condition', 'N/A'),
            valuation.get('market_value', 0),
            valuation.get('retail_value', 0),
            valuation.get('trade_value', 0),
            valuation.get('confidence_score', 0)
        ])
        
        return output.getvalue()
    
    def generate_markdown_report(self, report_data: Union[Dict, ReportData]) -> str:
        """
        Generate a Markdown report.
        
        Args:
            report_data: Report data dictionary or ReportData object
            
        Returns:
            Markdown string
        """
        if isinstance(report_data, ReportData):
            report_data = report_data.to_dict()
        
        vehicle = report_data.get('vehicle', {})
        valuation = report_data.get('valuation', {})
        
        md = f"""
# 🚗 Vehicle Valuation Report

**Generated:** {datetime.now(timezone.utc).strftime('%B %d, %Y %H:%M:%S')} UTC

---

## Vehicle Information

| Attribute | Value |
|-----------|-------|
| Make | {vehicle.get('make', 'N/A')} |
| Model | {vehicle.get('model', 'N/A')} |
| Variant | {vehicle.get('variant', 'N/A')} |
| Year | {vehicle.get('year', 'N/A')} |
| Engine | {vehicle.get('engine_cc', 'N/A')} cc |
| Fuel Type | {vehicle.get('fuel_type', 'N/A')} |
| Transmission | {vehicle.get('transmission', 'N/A')} |
| Mileage | {vehicle.get('mileage', 'N/A')} km |
| Condition | {vehicle.get('condition', 'N/A')} |

## Valuation Results

| Metric | Value |
|--------|-------|
| **Market Value** | **{self._format_kes(valuation.get('market_value', 0))}** |
| Retail Value | {self._format_kes(valuation.get('retail_value', 0))} |
| Trade Value | {self._format_kes(valuation.get('trade_value', 0))} |
| Expected Range | {self._format_kes(int(valuation.get('market_value', 0) * 0.92))} - {self._format_kes(int(valuation.get('market_value', 0) * 1.08))} |
| Confidence Score | {self._format_percentage(valuation.get('confidence_score', 0))} |

## Recommendations

"""
        for rec in report_data.get('recommendations', []):
            md += f"- {rec}\n"
        
        md += """
---

*Disclaimer: This valuation is an estimate based on market data and should not be considered as a definitive appraisal.*

---
*Generated by Auto-D Kenya*
"""
        return md
    
    # ─── Main Generation Method ──────────────────────────────────
    
    def generate_report(
        self,
        report_data: Union[Dict, ReportData],
        format: ReportFormat = ReportFormat.PDF,
        **kwargs
    ) -> str:
        """
        Generate a report in the specified format.
        
        Args:
            report_data: Report data dictionary or ReportData object
            format: Report format (pdf, html, json, csv, md)
            **kwargs: Additional format-specific arguments
            
        Returns:
            Report string (JSON, HTML, CSV, Markdown) or Base64 encoded PDF
        """
       
