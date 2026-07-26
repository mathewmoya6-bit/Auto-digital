# app/services/report_generator.py

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
