# app/modules/reports/pdf.py
# Auto-D Kenya - PDF Report Generator
# ================================================================
# TYPE: MODULE - PDF generation for reports

import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT


class PDFGenerator:
    """PDF report generator."""
    
    @staticmethod
    def generate_valuation_report(data: dict) -> bytes:
        """Generate a valuation report PDF."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#eab308'),
            alignment=TA_CENTER
        )
        
        # Build content
        story = []
        
        # Title
        story.append(Paragraph("Auto-D Kenya Valuation Report", title_style))
        story.append(Spacer(1, 0.25 * inch))
        
        # Date
        story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%B %d, %Y')}", styles['Normal']))
        story.append(Spacer(1, 0.25 * inch))
        
        # Vehicle details
        vehicle = data.get("vehicle", {})
        valuation = data.get("valuation", {})
        
        vehicle_data = [
            ["Vehicle", f"{vehicle.get('make_model', 'N/A')}"],
            ["Plate", f"{vehicle.get('plate', 'N/A')}"],
            ["Year", f"{vehicle.get('year', 'N/A')}"],
            ["Mileage", f"{vehicle.get('mileage', 0):,} km"]
        ]
        
        table = Table(vehicle_data, colWidths=[2*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1a2332')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#0a0c15')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#334155'))
        ]))
        story.append(table)
        story.append(Spacer(1, 0.25 * inch))
        
        # Valuation results
        story.append(Paragraph("Valuation Results", styles['Heading2']))
        story.append(Spacer(1, 0.1 * inch))
        
        valuation_data = [
            ["Market Value", f"KES {valuation.get('market_value', 0):,.0f}"],
            ["Retail Value", f"KES {valuation.get('retail_value', 0):,.0f}"],
            ["Trade Value", f"KES {valuation.get('trade_value', 0):,.0f}"],
            ["Confidence Score", f"{valuation.get('confidence_score', 0)}%"]
        ]
        
        table2 = Table(valuation_data, colWidths=[2*inch, 3*inch])
        table2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1a2332')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#0a0c15')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#334155'))
        ]))
        story.append(table2)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
