# app/services/report_generator.py

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json
import logging
import io
import base64

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generate vehicle valuation reports in multiple formats"""
    
    def __init__(self):
        """Initialize the report generator with styles"""
        self.reportlab_available = False
        
        # Try to import reportlab
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.enums import TA_CENTER
            
            self.colors = colors
            self.A4 = A4
            self.SimpleDocTemplate = SimpleDocTemplate
            self.Paragraph = Paragraph
            self.Spacer = Spacer
            self.Table = Table
            self.TableStyle = TableStyle
            self.getSampleStyleSheet = getSampleStyleSheet
            self.ParagraphStyle = ParagraphStyle
            self.inch = inch
            self.TA_CENTER = TA_CENTER
            
            # Initialize styles
            self._init_styles()
            self.reportlab_available = True
            logger.info("✅ ReportLab loaded successfully - PDF reports available")
        except ImportError as e:
            logger.warning(f"⚠️ ReportLab not available - PDF reports disabled: {e}")
    
    def _init_styles(self):
        """Initialize report styles"""
        if not self.reportlab_available:
            return
        
        self.styles = self.getSampleStyleSheet()
        self.primary_color = self.colors.HexColor('#1a56db')
        
        # Add custom styles
        self.styles.add(self.ParagraphStyle(
            name='CustomHeading1',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.colors.HexColor('#1a56db'),
            alignment=self.TA_CENTER,
            spaceAfter=20
        ))
        
        self.styles.add(self.ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=self.colors.HexColor('#374151'),
            spaceAfter=12
        ))
        
        self.styles.add(self.ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        ))
        
        self.styles.add(self.ParagraphStyle(
            name='SmallBody',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=self.colors.HexColor('#6b7280'),
            spaceAfter=4
        ))
    
    def _create_valuation_summary(self, variant: Dict, valuation: Dict) -> List:
        """Create valuation summary section"""
        if not self.reportlab_available:
            return []
        
        elements = []
        elements.append(self.Paragraph("Valuation Summary", self.styles['CustomHeading2']))
        
        market_value = valuation.get('market_value', 0)
        confidence = valuation.get('confidence_score', 0)
        
        # Calculate range
        min_price = int(market_value * 0.92)
        max_price = int(market_value * 1.08)
        
        # Format numbers
        def format_kes(value):
            if value is None:
                return "KES 0"
            try:
                return f"KES {int(value):,}"
            except (ValueError, TypeError):
                return f"KES {value}"
        
        # Create table
        data = [
            ['Metric', 'Value'],
            ['Estimated Market Value', format_kes(market_value)],
            ['Expected Range', f"{format_kes(min_price)} - {format_kes(max_price)}"],
            ['Confidence Score', f"{confidence * 100:.0f}%"],
        ]
        
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
            ('GRID', (0, 0), (-1, -1), 1, self.colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.colors.whitesmoke, self.colors.white]),
        ]))
        
        elements.append(table)
        elements.append(self.Spacer(1, 10))
        
        return elements
    
    def generate_pdf_report(self, valuation_data: Dict) -> str:
        """Generate a PDF report and return as base64 string"""
        if not self.reportlab_available:
            raise ImportError(
                "ReportLab is not installed. PDF reports are disabled. "
                "Install with: pip install reportlab"
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
        
        # Title
        vehicle = valuation_data.get('vehicle', {})
        title_text = f"Vehicle Valuation Report - {vehicle.get('make', '')} {vehicle.get('model', '')}"
        story.append(self.Paragraph(title_text, self.styles['CustomHeading1']))
        story.append(self.Spacer(1, 20))
        
        # Date
        date_text = f"Report Date: {datetime.now().strftime('%B %d, %Y')}"
        story.append(self.Paragraph(date_text, self.styles['CustomBody']))
        story.append(self.Spacer(1, 10))
        
        # Vehicle Info
        story.extend(self._create_valuation_summary(
            valuation_data.get('variant', {}),
            valuation_data.get('valuation', {})
        ))
        
        # Disclaimer
        disclaimer_text = """
        <b>Disclaimer:</b> This valuation is an estimate based on market data and should not be considered 
        as a definitive appraisal. Actual market prices may vary based on vehicle condition, location, 
        demand, and other factors. This report is for informational purposes only.
        """
        story.append(self.Paragraph(disclaimer_text, self.styles['SmallBody']))
        story.append(self.Spacer(1, 5))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF data and encode as base64
        pdf_data = buffer.getvalue()
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        buffer.close()
        
        return pdf_base64
    
    def generate_html_report(self, valuation_data: Dict) -> str:
        """Generate an HTML report"""
        vehicle = valuation_data.get('vehicle', {})
        valuation = valuation_data.get('valuation', {})
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Vehicle Valuation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #1a56db; text-align: center; }}
                h2 {{ color: #374151; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ padding: 10px; text-align: left; border: 1px solid #ddd; }}
                th {{ background-color: #1a56db; color: white; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .value {{ font-size: 20px; color: #059669; }}
                .disclaimer {{ font-size: 10px; color: #6b7280; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <h1>Vehicle Valuation Report</h1>
            <p><strong>Report Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
            
            <h2>Valuation Summary</h2>
            <table>
                <tr><td><strong>Vehicle</strong></td><td>{vehicle.get('make', 'N/A')} {vehicle.get('model', 'N/A')}</td></tr>
                <tr><td><strong>Year</strong></td><td>{vehicle.get('year', 'N/A')}</td></tr>
                <tr><td><strong>Estimated Market Value</strong></td><td class="value">KES {valuation.get('market_value', 0):,}</td></tr>
                <tr><td><strong>Confidence Score</strong></td><td>{valuation.get('confidence_score', 0) * 100:.0f}%</td></tr>
            </table>
            
            <p class="disclaimer"><strong>Disclaimer:</strong> This valuation is an estimate based on market data and should not be considered as a definitive appraisal.</p>
        </body>
        </html>
        """
        return html
    
    def generate_json_report(self, valuation_data: Dict) -> str:
        """Generate a JSON report"""
        return json.dumps(valuation_data, indent=2, default=str)
