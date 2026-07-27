# app/services/report_generator.py

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json
import logging
from pathlib import Path
import io
import base64

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generate vehicle valuation reports in multiple formats"""
    
    def __init__(self):
        """Initialize the report generator with styles"""
        # Lazy import reportlab to make it optional
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
            
            self.reportlab_available = True
            self.colors = colors
            self.pagesizes = {'letter': letter, 'A4': A4}
            self.platypus = {
                'SimpleDocTemplate': SimpleDocTemplate,
                'Paragraph': Paragraph,
                'Spacer': Spacer,
                'Table': Table,
                'TableStyle': TableStyle,
                'Image': Image
            }
            self.styles_module = getSampleStyleSheet
            self.units = {'inch': inch}
            self.enums = {'TA_CENTER': TA_CENTER, 'TA_RIGHT': TA_RIGHT, 'TA_LEFT': TA_LEFT}
            
            # Initialize styles
            self._init_styles()
            
            logger.info("✅ ReportLab loaded successfully - PDF reports available")
        except ImportError as e:
            self.reportlab_available = False
            logger.warning(f"⚠️ ReportLab not available - PDF reports disabled: {e}")
    
    def _init_styles(self):
        """Initialize report styles"""
        if not self.reportlab_available:
            return
            
        self.styles = self.styles_module()
        self.primary_color = self.colors.HexColor('#1a56db')
        self.secondary_color = self.colors.HexColor('#e5e7eb')
        
        # Add custom styles
        self.styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.colors.HexColor('#1a56db'),
            alignment=self.enums['TA_CENTER'],
            spaceAfter=20
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=self.colors.HexColor('#374151'),
            spaceAfter=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='SmallBody',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=self.colors.HexColor('#6b7280'),
            spaceAfter=4
        ))
        
        self.styles.add(ParagraphStyle(
            name='ValueText',
            parent=self.styles['Normal'],
            fontSize=20,
            textColor=self.colors.HexColor('#059669'),
            alignment=self.enums['TA_CENTER'],
            spaceAfter=10
        ))
    
    def _create_valuation_summary(self, variant: Dict, valuation: Dict) -> List:
        """Create valuation summary section"""
        if not self.reportlab_available:
            return []
            
        elements = []
        elements.append(Paragraph("Valuation Summary", self.styles['CustomHeading2']))
        
        market_value = valuation.get('market_value', 0)
        confidence = valuation.get('confidence_score', 0)
        
        # Calculate range FROM the market value
        min_price = int(market_value * 0.92)
        max_price = int(market_value * 1.08)
        
        # If the valuation has a price_range, use it but ensure market_value is within it
        price_range = valuation.get('price_range', {})
        if price_range and price_range.get('min') and price_range.get('max'):
            db_min = price_range.get('min', 0)
            db_max = price_range.get('max', 0)
            if db_min > 0 and db_max > 0:
                min_price = min(db_min, market_value)
                max_price = max(db_max, market_value)
                if market_value < db_min:
                    market_value = db_min
                elif market_value > db_max:
                    market_value = db_max
                min_price = db_min
                max_price = db_max
        
        # Format numbers properly
        def format_kes(value):
            if value is None:
                return "KES 0"
            try:
                return f"KES {int(value):,}"
            except (ValueError, TypeError):
                return f"KES {value}"
        
        # Create table with proper values
        data = [
            ['Metric', 'Value'],
            ['Estimated Market Value', format_kes(market_value)],
            ['Expected Range', f"{format_kes(min_price)} - {format_kes(max_price)}"],
            ['Confidence Score', f"{confidence * 100:.0f}%"],
            ['Sample Size', str(valuation.get('sample_size', 0))],
        ]
        
        table = Table(data, colWidths=[2.5*self.units['inch'], 3.5*self.units['inch']])
        
        table.setStyle(TableStyle([
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
            ('WORDWRAP', (0, 0), (-1, -1), False),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10))
        
        return elements
    
    def generate_pdf_report(self, valuation_data: Dict) -> str:
        """Generate a PDF report and return as base64 string"""
        if not self.reportlab_available:
            raise ImportError("ReportLab is not installed. Install with: pip install reportlab")
            
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.pagesizes['A4'],
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )
        
        # Build document elements
        story = []
        
        # Title
        title_text = f"Vehicle Valuation Report - {valuation_data.get('vehicle', {}).get('make', '')} {valuation_data.get('vehicle', {}).get('model', '')}"
        story.append(Paragraph(title_text, self.styles['CustomHeading1']))
        story.append(Spacer(1, 20))
        
        # Date
        date_text = f"Report Date: {datetime.now().strftime('%B %d, %Y')}"
        story.append(Paragraph(date_text, self.styles['CustomBody']))
        story.append(Spacer(1, 10))
        
        # Vehicle Information - simplified version without full implementation
        story.extend(self._create_vehicle_info(valuation_data.get('vehicle', {})))
        
        # Valuation Summary
        story.extend(self._create_valuation_summary(
            valuation_data.get('variant', {}),
            valuation_data.get('valuation', {})
        ))
        
        # Add disclaimer
        disclaimer_text = """
        <b>Disclaimer:</b> This valuation is an estimate based on market data and should not be considered 
        as a definitive appraisal. Actual market prices may vary based on vehicle condition, location, 
        demand, and other factors. This report is for informational purposes only and does not constitute 
        financial advice.
        """
        story.append(Paragraph(disclaimer_text, self.styles['SmallBody']))
        story.append(Spacer(1, 5))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF data and encode as base64
        pdf_data = buffer.getvalue()
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        buffer.close()
        
        return pdf_base64
    
    def _create_vehicle_info(self, vehicle: Dict) -> List:
        """Create vehicle information section"""
        if not self.reportlab_available:
            return []
            
        elements = []
        elements.append(Paragraph("Vehicle Information", self.styles['CustomHeading2']))
        
        # Simplified vehicle details
        data = [
            ['Make', vehicle.get('make', 'N/A')],
            ['Model', vehicle.get('model', 'N/A')],
            ['Year', str(vehicle.get('year', 'N/A'))],
            ['Mileage', f"{vehicle.get('mileage', 0):,} km"],
        ]
        
        table = Table(data, colWidths=[2*self.units['inch'], 4*self.units['inch']])
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), self.colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, self.colors.grey),
            ('ROWBACKGROUNDS', (1, 0), (1, -1), [self.colors.white, self.colors.whitesmoke]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10))
        
        return elements
    
    def generate_html_report(self, valuation_data: Dict) -> str:
        """Generate an HTML report"""
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
                .disclaimer {{ font-size: 10px; color: #6b7280; }}
            </style>
        </head>
        <body>
            <h1>Vehicle Valuation Report</h1>
            <p>Report Date: {datetime.now().strftime('%B %d, %Y')}</p>
            
            <h2>Vehicle Information</h2>
            <table>
                <tr><td>Make</td><td>{valuation_data.get('vehicle', {}).get('make', 'N/A')}</td></tr>
                <tr><td>Model</td><td>{valuation_data.get('vehicle', {}).get('model', 'N/A')}</td></tr>
                <tr><td>Year</td><td>{valuation_data.get('vehicle', {}).get('year', 'N/A')}</td></tr>
                <tr><td>Mileage</td><td>{valuation_data.get('vehicle', {}).get('mileage', 0):,} km</td></tr>
            </table>
            
            <h2>Valuation Summary</h2>
            <table>
                <tr><td>Estimated Market Value</td><td class="value">KES {valuation_data.get('valuation', {}).get('market_value', 0):,}</td></tr>
                <tr><td>Confidence Score</td><td>{valuation_data.get('valuation', {}).get('confidence_score', 0) * 100:.0f}%</td></tr>
            </table>
            
            <p class="disclaimer">This valuation is an estimate based on market data and should not be considered as a definitive appraisal.</p>
        </body>
        </html>
        """
        return html
    
    def generate_json_report(self, valuation_data: Dict) -> str:
        """Generate a JSON report"""
        return json.dumps(valuation_data, indent=2, default=str)
