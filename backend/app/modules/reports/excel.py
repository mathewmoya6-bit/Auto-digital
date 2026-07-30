# app/modules/reports/excel.py
# Auto-D Kenya - Excel Report Generator
# ================================================================
# TYPE: MODULE - Excel generation for reports

import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class ExcelGenerator:
    """Excel report generator."""
    
    @staticmethod
    def generate_valuation_report(data: dict) -> bytes:
        """Generate a valuation report Excel file."""
        wb = Workbook()
        
        # Get active worksheet
        ws = wb.active
        ws.title = "Valuation Report"
        
        # Styles
        header_font = Font(bold=True, color="FFFFFF", size=12)
        header_fill = PatternFill(start_color="1a2332", end_color="1a2332", fill_type="solid")
        border = Border(
            left=Side(style='thin', color='334155'),
            right=Side(style='thin', color='334155'),
            top=Side(style='thin', color='334155'),
            bottom=Side(style='thin', color='334155')
        )
        
        # Title
        ws['A1'] = "Auto-D Kenya Valuation Report"
        ws['A1'].font = Font(bold=True, size=16)
        ws.merge_cells('A1:D1')
        
        # Date
        ws['A2'] = f"Generated: {datetime.utcnow().strftime('%B %d, %Y')}"
        ws.merge_cells('A2:D2')
        
        # Blank row
        ws.append([])
        
        # Vehicle details section
        ws['A4'] = "Vehicle Details"
        ws['A4'].font = Font(bold=True, size=14)
        
        # Vehicle data
        vehicle = data.get("vehicle", {})
        ws.append(["Make/Model", vehicle.get('make_model', 'N/A')])
        ws.append(["Plate", vehicle.get('plate', 'N/A')])
        ws.append(["Year", vehicle.get('year', 'N/A')])
        ws.append(["Mileage", f"{vehicle.get('mileage', 0):,} km"])
        
        # Blank row
        ws.append([])
        
        # Valuation results section
        ws['A10'] = "Valuation Results"
        ws['A10'].font = Font(bold=True, size=14)
        
        valuation = data.get("valuation", {})
        ws.append(["Market Value", f"KES {valuation.get('market_value', 0):,.0f}"])
        ws.append(["Retail Value", f"KES {valuation.get('retail_value', 0):,.0f}"])
        ws.append(["Trade Value", f"KES {valuation.get('trade_value', 0):,.0f}"])
        ws.append(["Confidence Score", f"{valuation.get('confidence_score', 0)}%"])
        
        # Apply styles
        for row in ws.iter_rows(min_row=4, max_row=ws.max_row):
            for cell in row:
                cell.border = border
        
        # Auto-fit columns
        for col in range(1, 5):
            column_letter = get_column_letter(col)
            max_length = 0
            for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=col, max_col=col):
                for cell in row:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
            adjusted_width = min(max_length + 2, 30)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Save to bytes
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
