# app/services/report_generator.py

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json
import logging
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import io
import base64

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generate vehicle valuation reports in multiple formats"""
    
    def __init__(self):
        """Initialize the report generator with styles"""
        self.styles = getSampleStyleSheet()
        self.primary_color = colors.HexColor('#1a56db')  # Primary blue color
        self.secondary_color = colors.HexColor('#e5e7eb')  # Light gray
        
        # Add custom styles
        self.styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a56db'),
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#374151'),
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
            textColor=colors.HexColor('#6b7280'),
            spaceAfter=4
        ))
        
        self.styles.add(ParagraphStyle(
            name='ValueText',
            parent=self.styles['Normal'],
            fontSize=20,
            textColor=colors.HexColor('#059669'),
            alignment=TA_CENTER,
            spaceAfter=10
        ))

    def _create_valuation_summary(self, variant: Dict, valuation: Dict) -> List:
        """Create valuation summary section - FIXED: Value range always contains the estimate"""
        elements = []
        
        elements.append(Paragraph("Valuation Summary", self.styles['CustomHeading2']))
        
        market_value = valuation.get('market_value', 0)
        confidence = valuation.get('confidence_score', 0)
        
        # ─── FIX 1: Calculate range FROM the market value ──────────────
        # The estimate MUST always lie within the range
        min_price = int(market_value * 0.92)  # 8% below
        max_price = int(market_value * 1.08)  # 8% above
        
        # If the valuation has a price_range, use it but ensure market_value is within it
        price_range = valuation.get('price_range', {})
        if price_range and price_range.get('min') and price_range.get('max'):
            db_min = price_range.get('min', 0)
            db_max = price_range.get('max', 0)
            if db_min > 0 and db_max > 0:
                # Ensure market_value is within the range
                min_price = min(db_min, market_value)
                max_price = max(db_max, market_value)
                # Or use the range but clamp the market value
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
        
        # ─── FIX 2: Wider columns to prevent truncation ──────────────
        table = Table(data, colWidths=[2.5*inch, 3.5*inch])
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ('WORDWRAP', (0, 0), (-1, -1), False),  # Prevent text wrap
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_vehicle_info(self, vehicle: Dict) -> List:
        """Create vehicle information section"""
        elements = []
        
        elements.append(Paragraph("Vehicle Information", self.styles['CustomHeading2']))
        
        # Vehicle details table
        data = [
            ['Make', vehicle.get('make', 'N/A')],
            ['Model', vehicle.get('model', 'N/A')],
            ['Variant', vehicle.get('variant', 'N/A')],
            ['Year', str(vehicle.get('year', 'N/A'))],
            ['Mileage', f"{vehicle.get('mileage', 0):,} km"],
            ['Transmission', vehicle.get('transmission', 'N/A')],
            ['Fuel Type', vehicle.get('fuel_type', 'N/A')],
            ['Engine', vehicle.get('engine_capacity', 'N/A')],
        ]
        
        table = Table(data, colWidths=[2*inch, 4*inch])
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (1, 0), (1, -1), [colors.white, colors.whitesmoke]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_market_comparison(self, comparables: List[Dict]) -> List:
        """Create market comparison section"""
        elements = []
        
        if not comparables:
            return elements
        
        elements.append(Paragraph("Market Comparison", self.styles['CustomHeading2']))
        
        # Create header and data rows
        data = [['Source', 'Price', 'Year', 'Mileage']]
        
        for comp in comparables[:5]:  # Show top 5 comparables
            data.append([
                comp.get('source', 'N/A'),
                f"KES {comp.get('price', 0):,}",
                str(comp.get('year', 'N/A')),
                f"{comp.get('mileage', 0):,} km"
            ])
        
        table = Table(data, colWidths=[1.5*inch, 1.5*inch, 1.2*inch, 2*inch])
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_conditions(self, condition_score: int, condition_details: Dict) -> List:
        """Create condition assessment section"""
        elements = []
        
        elements.append(Paragraph("Condition Assessment", self.styles['CustomHeading2']))
        
        # Condition score bar representation
        score_text = f"Overall Condition Score: {condition_score}/100"
        elements.append(Paragraph(score_text, self.styles['CustomBody']))
        
        # Condition details table
        if condition_details:
            data = [['Factor', 'Rating']]
            for factor, rating in condition_details.items():
                data.append([
                    factor.replace('_', ' ').title(),
                    f"{rating}/10" if isinstance(rating, (int, float)) else str(rating)
                ])
            
            table = Table(data, colWidths=[3*inch, 3*inch])
            
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.secondary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 10))
        
        return elements

    def _create_disclaimer(self) -> List:
        """Create disclaimer section"""
        elements = []
        
        disclaimer_text = """
        <b>Disclaimer:</b> This valuation is an estimate based on market data and should not be considered 
        as a definitive appraisal. Actual market prices may vary based on vehicle condition, location, 
        demand, and other factors. This report is for informational purposes only and does not constitute 
        financial advice.
        """
        
        elements.append(Paragraph(disclaimer_text, self.styles['SmallBody']))
        elements.append(Spacer(1, 5))
        
        return elements

    def generate_pdf_report(self, valuation_data: Dict) -> str:
        """Generate a PDF report and return as base64 string"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
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
        
        # Vehicle Information
        story.extend(self._create_vehicle_info(valuation_data.get('vehicle', {})))
        
        # Valuation Summary
        story.extend(self._create_valuation_summary(
            valuation_data.get('variant', {}),
            valuation_data.get('valuation', {})
        ))
        
        # Market Comparison
        story.extend(self._create_market_comparison(
            valuation_data.get('comparables', [])
        ))
        
        # Condition Assessment
        condition_score = valuation_data.get('condition_score', 0)
        condition_details = valuation_data.get('condition_details', {})
        story.extend(self._create_conditions(condition_score, condition_details))
        
        # Disclaimer
        story.extend(self._create_disclaimer())
        
        # Build PDF
        doc.build(story)
        
        # Get PDF data and encode as base64
        pdf_data = buffer.getvalue()
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        buffer.close()
        
        return pdf_base64

    def generate_html_report(self, valuation_data: Dict) -> str:
        """Generate an HTML report"""
        # Simplified HTML generation (you can expand this as needed)
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
                {''.join([f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>" 
                         for key, value in valuation_data.get('vehicle', {}).items()])}
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
