# app/services/report_generator.py
"""
Professional Report Generator for AUTO-D Kenya
Generates comprehensive PDF reports with charts, tables, and analysis
"""

import os
import io
import json
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

# Report generation libraries
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, KeepTogether, HRFlowable, FrameBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.widgets.markers import makeMarker

from app.services.supabase_service import SupabaseService
from app.services.price_aligner import PriceAligner
from app.services.price_analyzer import PriceAnalyzer

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Professional report generator for AUTO-D Kenya"""
    
    def __init__(self):
        self.supabase = SupabaseService()
        self.price_aligner = PriceAligner(self.supabase)
        self.price_analyzer = PriceAnalyzer(self.supabase)
        
        # Colors
        self.primary_color = colors.HexColor('#EAB308')
        self.secondary_color = colors.HexColor('#0A0C15')
        self.success_color = colors.HexColor('#22C55E')
        self.danger_color = colors.HexColor('#EF4444')
        self.info_color = colors.HexColor('#3B82F6')
        self.warning_color = colors.HexColor('#F59E0B')
        
        # Color palette for charts
        self.chart_colors = [
            colors.HexColor('#EAB308'),
            colors.HexColor('#3B82F6'),
            colors.HexColor('#22C55E'),
            colors.HexColor('#F472B6'),
            colors.HexColor('#8B5CF6'),
            colors.HexColor('#F97316'),
            colors.HexColor('#06B6D4'),
        ]
        
        # Set up styles
        self.styles = self._create_styles()
        
    def _create_styles(self):
        """Create custom paragraph styles"""
        styles = getSampleStyleSheet()
        
        # Title style
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor=self.primary_color,
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Heading 1
        styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=self.secondary_color,
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        ))
        
        # Heading 2
        styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=self.secondary_color,
            spaceAfter=8,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        # Body text
        styles.add(ParagraphStyle(
            name='CustomBody',
            parent=styles['BodyText'],
            fontSize=10,
            leading=14,
            spaceAfter=6,
            fontName='Helvetica'
        ))
        
        # Small text
        styles.add(ParagraphStyle(
            name='CustomSmall',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
            spaceAfter=4
        ))
        
        # Footer style
        styles.add(ParagraphStyle(
            name='CustomFooter',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.grey,
            alignment=TA_CENTER,
            spaceBefore=20
        ))
        
        # Value style (for currency)
        styles.add(ParagraphStyle(
            name='ValueStyle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=self.primary_color,
            fontName='Helvetica-Bold'
        ))
        
        return styles

    # ================================================================
    # MAIN REPORT GENERATORS
    # ================================================================

    async def generate_valuation_report(
        self,
        variant_id: str,
        year: int,
        user_id: Optional[str] = None,
        include_comparables: bool = True,
        include_history: bool = True,
        include_trends: bool = True
    ) -> bytes:
        """
        Generate a professional vehicle valuation report
        
        Returns:
            bytes: PDF report as bytes
        """
        try:
            # Get vehicle data
            variant = await self.supabase.get_vehicle_variant(variant_id)
            if not variant:
                raise ValueError(f"Vehicle variant {variant_id} not found")
            
            # Get valuation
            valuation = await self.supabase.calculate_valuation(
                variant_id=variant_id,
                year=year,
                county='Nairobi'  # Default, could be user-specified
            )
            
            if not valuation:
                raise ValueError(f"Could not calculate valuation for variant {variant_id}")
            
            # Get market data
            market_prices = await self.supabase.get_market_prices(variant_id, year)
            listings = await self.supabase.get_listings_by_variant(variant_id, year)
            
            # Get comparable vehicles
            comparables = []
            if include_comparables:
                comparables = await self.supabase.get_comparable_vehicles(variant_id, year)
            
            # Get price history
            history = []
            if include_history:
                history = await self.supabase.get_price_history(variant_id, year, months=12)
            
            # Get market trend
            trend = None
            if include_trends:
                trend = await self.supabase.get_market_trend(variant_id, year)
            
            # Create report
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72,
                title=f"Vehicle Valuation Report - {variant.get('name', 'Unknown')}"
            )
            
            # Build content
            elements = []
            
            # Header/Title
            elements.extend(self._create_header(variant))
            
            # Executive Summary
            elements.extend(self._create_executive_summary(variant, valuation, market_prices))
            
            # Valuation Summary
            elements.extend(self._create_valuation_summary(variant, valuation))
            
            # Market Analysis Chart
            elements.extend(self._create_market_analysis_chart(listings))
            
            # Price Distribution
            elements.extend(self._create_price_distribution(market_prices))
            
            # Comparable Vehicles
            if comparables:
                elements.extend(self._create_comparable_table(comparables))
            
            # Price History
            if history:
                elements.extend(self._create_price_history_chart(history))
            
            # Market Trends
            if trend:
                elements.extend(self._create_market_trends(trend))
            
            # Recommendations
            elements.extend(self._create_recommendations(valuation, trend))
            
            # Footer
            elements.extend(self._create_footer())
            
            # Build PDF
            doc.build(elements)
            
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating valuation report: {e}")
            raise

    async def generate_market_insights_report(
        self,
        make: Optional[str] = None,
        body_type: Optional[str] = None,
        county: Optional[str] = None
    ) -> bytes:
        """Generate a professional market insights report"""
        try:
            # Get market statistics
            stats = await self.supabase.get_market_statistics(make, body_type)
            
            # Get trending vehicles
            trending = await self.supabase.get_trending_vehicles(limit=10)
            
            # Get price distribution
            distribution = await self.supabase.get_price_distribution(make, body_type)
            
            # Get dealer performance
            dealer_performance = await self._get_dealer_performance(county)
            
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72,
                title="Market Insights Report - Kenya"
            )
            
            elements = []
            
            # Header
            elements.append(Paragraph("Market Insights Report", self.styles['CustomTitle']))
            elements.append(Paragraph("Kenyan Vehicle Market Analysis", self.styles['CustomBody']))
            elements.append(Spacer(1, 20))
            
            # Executive Summary
            elements.extend(self._create_market_summary(stats))
            
            # Key Metrics
            elements.extend(self._create_key_metrics(stats))
            
            # Price Distribution Chart
            elements.extend(self._create_market_distribution_chart(distribution))
            
            # Trending Vehicles
            elements.extend(self._create_trending_vehicles_section(trending))
            
            # Dealer Performance
            if dealer_performance:
                elements.extend(self._create_dealer_performance_table(dealer_performance))
            
            # Market Outlook
            elements.extend(self._create_market_outlook())
            
            # Footer
            elements.extend(self._create_footer())
            
            doc.build(elements)
            
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating market insights report: {e}")
            raise

    async def generate_ownership_cost_report(
        self,
        variant_id: str,
        year: int,
        annual_mileage: int = 20000,
        ownership_years: int = 5,
        county: str = 'Nairobi'
    ) -> bytes:
        """Generate a professional ownership cost report"""
        try:
            # Get vehicle data
            variant = await self.supabase.get_vehicle_variant(variant_id)
            if not variant:
                raise ValueError(f"Vehicle variant {variant_id} not found")
            
            # Calculate ownership costs
            costs = await self._calculate_ownership_costs(
                variant, year, annual_mileage, ownership_years, county
            )
            
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72,
                title=f"Ownership Cost Report - {variant.get('name', 'Unknown')}"
            )
            
            elements = []
            
            # Header
            elements.extend(self._create_header(variant))
            
            # Title
            elements.append(Paragraph("Total Cost of Ownership Analysis", self.styles['CustomTitle']))
            elements.append(Spacer(1, 20))
            
            # Vehicle Summary
            elements.extend(self._create_vehicle_summary(variant, year, annual_mileage))
            
            # Cost Breakdown Chart
            elements.extend(self._create_cost_breakdown_chart(costs))
            
            # Year-by-Year Cost Table
            elements.extend(self._create_year_by_year_table(costs))
            
            # Cost Per Kilometer
            elements.extend(self._create_cost_per_km_analysis(costs))
            
            # Savings Recommendations
            elements.extend(self._create_savings_recommendations(costs))
            
            # Footer
            elements.extend(self._create_footer())
            
            doc.build(elements)
            
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating ownership cost report: {e}")
            raise

    # ================================================================
    # SECTION CREATORS
    # ================================================================

    def _create_header(self, variant: Dict) -> List:
        """Create report header"""
        elements = []
        
        # Logo placeholder
        elements.append(Spacer(1, 10))
        
        # Title
        title = f"Vehicle Valuation Report"
        elements.append(Paragraph(title, self.styles['CustomTitle']))
        
        # Subtitle
        make_name = variant.get('generation', {}).get('model', {}).get('make', {}).get('name', '')
        model_name = variant.get('generation', {}).get('model', {}).get('name', '')
        variant_name = variant.get('name', '')
        
        full_name = f"{make_name} {model_name} {variant_name}"
        elements.append(Paragraph(full_name, self.styles['CustomHeading1']))
        
        # Date
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y')}",
            self.styles['CustomSmall']
        ))
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1, color=self.primary_color))
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_executive_summary(self, variant: Dict, valuation: Dict, market_prices: List[Dict]) -> List:
        """Create executive summary section"""
        elements = []
        
        elements.append(Paragraph("Executive Summary", self.styles['CustomHeading1']))
        
        market_value = valuation.get('market_value', 0)
        confidence = valuation.get('confidence_score', 0) * 100
        
        summary_text = f"""
        <para>
        This report provides a comprehensive valuation analysis for the 
        <b>{variant.get('name', '')}</b>. Based on current market data from 
        {len(market_prices)} active listings, the estimated market value is 
        <b>KES {market_value:,}</b> with a confidence score of {confidence:.0f}%.
        </para>
        """
        elements.append(Paragraph(summary_text, self.styles['CustomBody']))
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_valuation_summary(self, variant: Dict, valuation: Dict) -> List:
        """Create valuation summary section"""
        elements = []
        
        elements.append(Paragraph("Valuation Summary", self.styles['CustomHeading2']))
        
        market_value = valuation.get('market_value', 0)
        confidence = valuation.get('confidence_score', 0)
        
        # Create a table with valuation details
        data = [
            ['Metric', 'Value'],
            ['Estimated Market Value', f'KES {market_value:,}'],
            ['Confidence Score', f'{confidence * 100:.0f}%'],
            ['Sample Size', str(valuation.get('sample_size', 0))],
            ['Expected Selling Days', str(valuation.get('expected_selling_days', 'N/A'))],
            ['Market Trend', valuation.get('market_trend', 'Stable').capitalize()],
            ['Demand Index', f"{valuation.get('demand_index', 0):.2f}"],
        ]
        
        # Add price range if available
        price_range = valuation.get('price_range', {})
        if price_range:
            data.append(['Price Range (Min - Max)', f"KES {price_range.get('min', 0):,} - KES {price_range.get('max', 0):,}"])
        
        table = Table(data, colWidths=[3*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_market_analysis_chart(self, listings: List[Dict]) -> List:
        """Create market analysis chart"""
        elements = []
        
        if not listings:
            return elements
        
        elements.append(Paragraph("Market Analysis", self.styles['CustomHeading2']))
        
        # Create bar chart of price distribution by condition
        drawing = Drawing(400, 200)
        
        # Count listings by condition
        conditions = {}
        for listing in listings:
            cond = listing.get('condition', 'Unknown')
            conditions[cond] = conditions.get(cond, 0) + 1
        
        # Create chart
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 50
        chart.width = 300
        chart.height = 120
        
        chart.data = [list(conditions.values())]
        chart.categoryAxis.categoryNames = list(conditions.keys())
        
        chart.valueAxis.valueMin = 0
        chart.valueAxis.valueMax = max(conditions.values()) + 1 if conditions.values() else 10
        
        chart.bars[0].fillColor = self.primary_color
        chart.bars[0].strokeColor = None
        chart.bars[0].strokeWidth = 0
        
        drawing.add(chart)
        elements.append(drawing)
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_price_distribution(self, market_prices: List[Dict]) -> List:
        """Create price distribution section"""
        elements = []
        
        if not market_prices:
            return elements
        
        elements.append(Paragraph("Price Distribution", self.styles['CustomHeading2']))
        
        # Extract prices
        prices = [p.get('median_price', 0) for p in market_prices if p.get('median_price')]
        if not prices:
            return elements
        
        # Calculate statistics
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        median_price = sorted(prices)[len(prices) // 2]
        
        # Create distribution table
        data = [
            ['Statistic', 'Value (KES)'],
            ['Average Price', f'{int(avg_price):,}'],
            ['Median Price', f'{int(median_price):,}'],
            ['Minimum Price', f'{int(min_price):,}'],
            ['Maximum Price', f'{int(max_price):,}'],
        ]
        
        table = Table(data, colWidths=[3*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.info_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_comparable_table(self, comparables: List[Dict]) -> List:
        """Create comparable vehicles table"""
        elements = []
        
        elements.append(Paragraph("Comparable Vehicles", self.styles['CustomHeading2']))
        elements.append(Paragraph(
            "Similar vehicles in the market for price comparison",
            self.styles['CustomBody']
        ))
        elements.append(Spacer(1, 5))
        
        # Create table
        data = [
            ['Vehicle', 'Year', 'Price (KES)', 'Mileage (km)', 'Condition']
        ]
        
        for comp in comparables[:5]:  # Limit to 5
            name = comp.get('name', 'Unknown')
            year = comp.get('year', 'N/A')
            price = comp.get('current_market_value', 0)
            mileage = comp.get('mileage', 'N/A')
            condition = comp.get('condition', 'Good')
            
            data.append([
                name[:30] + '...' if len(name) > 30 else name,
                str(year),
                f"{int(price):,}",
                f"{int(mileage):,}" if mileage != 'N/A' else 'N/A',
                condition.capitalize()
            ])
        
        table = Table(data, colWidths=[2.5*inch, 0.8*inch, 1.5*inch, 1.2*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.secondary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_price_history_chart(self, history: List[Dict]) -> List:
        """Create price history chart"""
        elements = []
        
        if len(history) < 2:
            return elements
        
        elements.append(Paragraph("Price History", self.styles['CustomHeading2']))
        elements.append(Paragraph(
            "Historical price trends over the analysis period",
            self.styles['CustomBody']
        ))
        elements.append(Spacer(1, 5))
        
        # Create line chart
        drawing = Drawing(450, 200)
        
        # Prepare data
        dates = [h.get('calculated_at', '') for h in history]
        prices = [h.get('market_value', 0) for h in history]
        
        if len(dates) > 10:
            # Show every nth date to avoid crowding
            step = max(1, len(dates) // 10)
            dates = dates[::step]
            prices = prices[::step]
        
        # Format dates for display
        date_labels = []
        for d in dates:
            try:
                if isinstance(d, str):
                    d = datetime.fromisoformat(d.replace('Z', '+00:00'))
                date_labels.append(d.strftime('%b %Y'))
            except:
                date_labels.append(str(d))
        
        # Create chart
        chart = HorizontalLineChart()
        chart.x = 60
        chart.y = 50
        chart.width = 350
        chart.height = 120
        
        chart.data = [prices]
        chart.categoryAxis.categoryNames = date_labels
        
        chart.valueAxis.valueMin = min(prices) * 0.9 if prices else 0
        chart.valueAxis.valueMax = max(prices) * 1.1 if prices else 0
        
        chart.lines[0].strokeColor = self.primary_color
        chart.lines[0].strokeWidth = 2
        
        # Add markers
        chart.lines[0].marker = makeMarker('FilledCircle')
        chart.lines[0].marker.size = 3
        
        drawing.add(chart)
        elements.append(drawing)
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_recommendations(self, valuation: Dict, trend: Optional[Dict]) -> List:
        """Create recommendations section"""
        elements = []
        
        elements.append(Paragraph("Recommendations", self.styles['CustomHeading1']))
        
        recommendations = []
        
        # Generate recommendations based on valuation
        confidence = valuation.get('confidence_score', 0)
        
        if confidence > 0.8:
            recommendations.append(("✅", "High confidence in valuation. The price is well-supported by market data."))
        elif confidence > 0.6:
            recommendations.append(("⚠️", "Moderate confidence. Consider getting a professional inspection for verification."))
        else:
            recommendations.append(("⚠️", "Low confidence due to limited market data. Professional valuation recommended."))
        
        # Trend-based recommendations
        if trend:
            direction = trend.get('trend_direction', 'stable')
            if direction == 'up':
                recommendations.append(("📈", "Market prices are trending upward. Consider acting soon for best value."))
            elif direction == 'down':
                recommendations.append(("📉", "Market prices are trending downward. Consider waiting for a better price."))
            else:
                recommendations.append(("➡️", "Market is stable. Good time to buy or sell."))
        
        # Demand-based recommendations
        demand = valuation.get('demand_index', 0.5)
        if demand > 0.7:
            recommendations.append(("🔥", "High demand for this vehicle. Good time to sell."))
        elif demand < 0.3:
            recommendations.append(("💡", "Low demand for this vehicle. Consider negotiating a better price."))
        
        # Add recommendations
        for rec in recommendations:
            elements.append(Paragraph(
                f"{rec[0]} {rec[1]}",
                self.styles['CustomBody']
            ))
        
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_footer(self) -> List:
        """Create report footer"""
        elements = []
        
        elements.append(Spacer(1, 20))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
        
        footer_text = f"""
        <para align="center">
        <font size="8" color="grey">
        This report was generated by AUTO-D Kenya AI Engine v2.0<br/>
        Data sources: Jiji Kenya, Cheki Kenya, Autochek Kenya, BeepBeep, PigiaMe<br/>
        Disclaimer: This is an AI-generated estimate and should not be considered financial advice.<br/>
        Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
        </font>
        </para>
        """
        elements.append(Paragraph(footer_text, self.styles['CustomFooter']))
        
        return elements

    # ================================================================
    # OWNERSHIP COST HELPERS
    # ================================================================

    async def _calculate_ownership_costs(
        self,
        variant: Dict,
        year: int,
        annual_mileage: int,
        ownership_years: int,
        county: str
    ) -> Dict:
        """Calculate ownership costs for a vehicle"""
        
        # Get market value
        market_value = await self.supabase.get_current_market_value(variant['id'], year)
        if not market_value:
            market_value = 3500000  # Default
        
        # Calculate costs
        costs = {
            'purchase_price': market_value,
            'annual_costs': [],
            'total_cost': 0,
            'cost_per_km': 0,
            'breakdown': {}
        }
        
        # Year by year costs
        for year_num in range(1, ownership_years + 1):
            # Depreciation (15% annually)
            current_value = market_value * (0.85 ** year_num)
            depreciation = market_value * (0.15 * (0.85 ** (year_num - 1)))
            
            # Fuel cost (assuming 8L/100km)
            fuel_cost = (annual_mileage / 100) * 8 * 200  # KES 200/L
            
            # Insurance (4.5% of current value)
            insurance = current_value * 0.045
            
            # Maintenance (KES 5,000 per 10,000 km)
            maintenance = (annual_mileage / 10000) * 5000
            
            # Tyres (replace every 50,000 km)
            tyres = (annual_mileage / 50000) * 48000
            
            # Licensing (1% of value)
            licensing = current_value * 0.01
            
            yearly_total = depreciation + fuel_cost + insurance + maintenance + tyres + licensing
            
            costs['annual_costs'].append({
                'year': year_num,
                'depreciation': depreciation,
                'fuel': fuel_cost,
                'insurance': insurance,
                'maintenance': maintenance,
                'tyres': tyres,
                'licensing': licensing,
                'total': yearly_total,
                'remaining_value': current_value
            })
            
            costs['total_cost'] += yearly_total
        
        # Calculate cost per km
        total_mileage = annual_mileage * ownership_years
        costs['cost_per_km'] = costs['total_cost'] / total_mileage if total_mileage > 0 else 0
        
        # Calculate breakdown percentages
        total = costs['total_cost']
        if total > 0:
            costs['breakdown'] = {
                'depreciation': sum(c['depreciation'] for c in costs['annual_costs']) / total * 100,
                'fuel': sum(c['fuel'] for c in costs['annual_costs']) / total * 100,
                'insurance': sum(c['insurance'] for c in costs['annual_costs']) / total * 100,
                'maintenance': sum(c['maintenance'] for c in costs['annual_costs']) / total * 100,
                'tyres': sum(c['tyres'] for c in costs['annual_costs']) / total * 100,
                'licensing': sum(c['licensing'] for c in costs['annual_costs']) / total * 100,
            }
        
        return costs

    def _create_cost_breakdown_chart(self, costs: Dict) -> List:
        """Create cost breakdown pie chart"""
        elements = []
        
        elements.append(Paragraph("Cost Breakdown", self.styles['CustomHeading2']))
        
        if not costs.get('breakdown'):
            return elements
        
        # Create pie chart
        drawing = Drawing(400, 200)
        
        pie = Pie()
        pie.x = 150
        pie.y = 65
        pie.width = 100
        pie.height = 100
        
        pie.data = list(costs['breakdown'].values())
        pie.labels = [k.capitalize() for k in costs['breakdown'].keys()]
        
        pie.slices.strokeWidth = 0.5
        pie.slices[0].fillColor = self.primary_color
        pie.slices[1].fillColor = self.info_color
        pie.slices[2].fillColor = self.success_color
        pie.slices[3].fillColor = self.warning_color
        pie.slices[4].fillColor = self.danger_color
        pie.slices[5].fillColor = colors.grey
        
        drawing.add(pie)
        elements.append(drawing)
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_year_by_year_table(self, costs: Dict) -> List:
        """Create year-by-year cost table"""
        elements = []
        
        elements.append(Paragraph("Year-by-Year Cost Analysis", self.styles['CustomHeading2']))
        
        # Create table
        data = [
            ['Year', 'Depreciation', 'Fuel', 'Insurance', 'Maintenance', 'Tyres', 'Licensing', 'Total']
        ]
        
        for year in costs['annual_costs']:
            data.append([
                f"Year {year['year']}",
                f"{int(year['depreciation']):,}",
                f"{int(year['fuel']):,}",
                f"{int(year['insurance']):,}",
                f"{int(year['maintenance']):,}",
                f"{int(year['tyres']):,}",
                f"{int(year['licensing']):,}",
                f"{int(year['total']):,}"
            ])
        
        # Add total row
        data.append([
            'Total',
            f"{int(sum(c['depreciation'] for c in costs['annual_costs'])):,}",
            f"{int(sum(c['fuel'] for c in costs['annual_costs'])):,}",
            f"{int(sum(c['insurance'] for c in costs['annual_costs'])):,}",
            f"{int(sum(c['maintenance'] for c in costs['annual_costs'])):,}",
            f"{int(sum(c['tyres'] for c in costs['annual_costs'])):,}",
            f"{int(sum(c['licensing'] for c in costs['annual_costs'])):,}",
            f"{int(sum(c['total'] for c in costs['annual_costs'])):,}"
        ])
        
        # Create table with appropriate column widths
        col_widths = [0.8*inch] * 8
        table = Table(data, colWidths=col_widths)
        
        # Style the table
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), self.secondary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]
        
        # Highlight total row
        total_row = len(data) - 1
        style.append(('BACKGROUND', (0, total_row), (-1, total_row), self.primary_color))
        style.append(('TEXTCOLOR', (0, total_row), (-1, total_row), colors.white))
        style.append(('FONTNAME', (0, total_row), (-1, total_row), 'Helvetica-Bold'))
        
        table.setStyle(TableStyle(style))
        elements.append(table)
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_cost_per_km_analysis(self, costs: Dict) -> List:
        """Create cost per kilometer analysis"""
        elements = []
        
        elements.append(Paragraph("Cost Per Kilometer Analysis", self.styles['CustomHeading2']))
        
        cost_per_km = costs.get('cost_per_km', 0)
        total_cost = costs.get('total_cost', 0)
        
        # Create metrics
        data = [
            ['Metric', 'Value'],
            ['Total Cost of Ownership', f"KES {int(total_cost):,}"],
            ['Cost Per Kilometer', f"KES {cost_per_km:.2f}"],
            ['Total Distance', f"{int(total_cost / cost_per_km):,} km" if cost_per_km > 0 else 'N/A'],
        ]
        
        table = Table(data, colWidths=[3*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.success_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_savings_recommendations(self, costs: Dict) -> List:
        """Create savings recommendations"""
        elements = []
        
        elements.append(Paragraph("Savings Recommendations", self.styles['CustomHeading1']))
        
        recommendations = []
        
        # Analyze cost breakdown
        breakdown = costs.get('breakdown', {})
        
        if breakdown.get('fuel', 0) > 30:
            recommendations.append(("⛽", "Fuel is a major expense. Consider a more fuel-efficient vehicle."))
        
        if breakdown.get('depreciation', 0) > 35:
            recommendations.append(("📉", "Depreciation is high. Consider buying used to reduce initial cost."))
        
        if breakdown.get('insurance', 0) > 15:
            recommendations.append(("🛡️", "Insurance costs are significant. Compare rates from different providers."))
        
        if breakdown.get('maintenance', 0) > 15:
            recommendations.append(("🔧", "High maintenance costs. Consider regular servicing to prevent major repairs."))
        
        if not recommendations:
            recommendations.append(("✅", "Your vehicle costs are well-balanced. No immediate savings opportunities identified."))
        
        for rec in recommendations:
            elements.append(Paragraph(
                f"{rec[0]} {rec[1]}",
                self.styles['CustomBody']
            ))
        
        elements.append(Spacer(1, 10))
        
        return elements

    # ================================================================
    # MARKET INSIGHTS HELPERS
    # ================================================================

    def _create_market_summary(self, stats: Dict) -> List:
        """Create market summary section"""
        elements = []
        
        elements.append(Paragraph("Market Overview", self.styles['CustomHeading1']))
        
        summary_text = f"""
        <para>
        Current market analysis for the Kenyan vehicle market shows 
        <b>{stats.get('total_listings', 0):,}</b> active listings across 
        <b>{stats.get('total_variants', 0)}</b> vehicle variants. 
        The average market price is <b>KES {stats.get('average_price', 0):,}</b> 
        with a median price of <b>KES {stats.get('median_price', 0):,}</b>.
        </para>
        """
        elements.append(Paragraph(summary_text, self.styles['CustomBody']))
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_key_metrics(self, stats: Dict) -> List:
        """Create key metrics section"""
        elements = []
        
        elements.append(Paragraph("Key Market Metrics", self.styles['CustomHeading2']))
        
        # Create metrics cards (using table)
        data = [
            ['Metric', 'Value'],
            ['Total Active Listings', f"{stats.get('total_listings', 0):,}"],
            ['Total Vehicle Variants', str(stats.get('total_variants', 0))],
            ['Average Price', f"KES {stats.get('average_price', 0):,}"],
            ['Median Price', f"KES {stats.get('median_price', 0):,}"],
            ['Price Range', f"KES {stats.get('min_price', 0):,} - KES {stats.get('max_price', 0):,}"],
        ]
        
        table = Table(data, colWidths=[3*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.info_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_market_distribution_chart(self, distribution: Dict) -> List:
        """Create market distribution chart"""
        elements = []
        
        elements.append(Paragraph("Price Distribution by Bracket", self.styles['CustomHeading2']))
        
        if not distribution or not distribution.get('brackets'):
            elements.append(Paragraph("No distribution data available", self.styles['CustomBody']))
            elements.append(Spacer(1, 10))
            return elements
        
        # Create bar chart
        drawing = Drawing(400, 200)
        
        brackets = distribution['brackets']
        labels = list(brackets.keys())
        values = list(brackets.values())
        
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 50
        chart.width = 300
        chart.height = 120
        
        chart.data = [values]
        chart.categoryAxis.categoryNames = labels
        
        chart.valueAxis.valueMin = 0
        chart.valueAxis.valueMax = max(values) + 1 if values else 10
        
        # Set colors
        for i in range(len(chart.bars)):
            chart.bars[i].fillColor = self.chart_colors[i % len(self.chart_colors)]
            chart.bars[i].strokeColor = None
        
        drawing.add(chart)
        elements.append(drawing)
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_trending_vehicles_section(self, trending: List[Dict]) -> List:
        """Create trending vehicles section"""
        elements = []
        
        elements.append(Paragraph("Trending Vehicles", self.styles['CustomHeading2']))
        
        if not trending:
            elements.append(Paragraph("No trending data available", self.styles['CustomBody']))
            elements.append(Spacer(1, 10))
            return elements
        
        # Create table
        data = [
            ['Vehicle', 'Listings', 'Popularity']
        ]
        
        for vehicle in trending[:10]:
            name = vehicle.get('variant_name', 'Unknown')
            count = vehicle.get('count', 0)
            
            # Create simple popularity bar
            popularity = min(count / 10, 1)  # Normalize
            
            data.append([
                name[:30] + '...' if len(name) > 30 else name,
                str(count),
                f"{int(popularity * 100)}%"
            ])
        
        table = Table(data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.secondary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_dealer_performance_table(self, dealer_data: List[Dict]) -> List:
        """Create dealer performance table"""
        elements = []
        
        elements.append(Paragraph("Dealer Performance", self.styles['CustomHeading2']))
        
        if not dealer_data:
            elements.append(Paragraph("No dealer performance data available", self.styles['CustomBody']))
            elements.append(Spacer(1, 10))
            return elements
        
        # Create table
        data = [
            ['Dealer Name', 'County', 'Rating', 'Listings', 'Avg Price']
        ]
        
        for dealer in dealer_data[:10]:
            data.append([
                dealer.get('dealer_name', 'Unknown')[:25] + '...' if len(dealer.get('dealer_name', '')) > 25 else dealer.get('dealer_name', 'Unknown'),
                dealer.get('county', 'N/A'),
                f"{dealer.get('rating', 0):.1f}★",
                str(dealer.get('total_listings', 0)),
                f"KES {dealer.get('avg_price', 0):,}"
            ])
        
        table = Table(data, colWidths=[2*inch, 1*inch, 0.8*inch, 1*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.secondary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10))
        
        return elements

    def _create_market_outlook(self) -> List:
        """Create market outlook section"""
        elements = []
        
        elements.append(Paragraph("Market Outlook", self.styles['CustomHeading1']))
        
        outlook_text = """
        <para>
        The Kenyan vehicle market shows <b>stable</b> growth with increasing demand for 
        <b>SUV</b> and <b>pickup</b> vehicles. Prices are expected to remain relatively 
        stable over the next 6 months, with potential upward pressure on used vehicle 
        prices due to import restrictions.
        </para>
        <para><br/></para>
        <para>
        <b>Key Factors to Watch:</b>
        </para>
        <para>
        • Exchange rate fluctuations affecting import costs<br/>
        • Government policies on vehicle imports<br/>
        • Fuel price changes<br/>
        • Electric vehicle adoption trends
        </para>
        """
        elements.append(Paragraph(outlook_text, self.styles['CustomBody']))
        elements.append(Spacer(1, 10))
        
        return elements

    async def _get_dealer_performance(self, county: Optional[str] = None) -> List[Dict]:
        """Get dealer performance data"""
        try:
            # This would typically query a view or table
            # For now, return empty list (implementation depends on your data)
            return []
        except Exception as e:
            logger.error(f"Error getting dealer performance: {e}")
            return []

    def _create_vehicle_summary(self, variant: Dict, year: int, annual_mileage: int) -> List:
        """Create vehicle summary section"""
        elements = []
        
        elements.append(Paragraph("Vehicle Summary", self.styles['CustomHeading1']))
        
        make_name = variant.get('generation', {}).get('model', {}).get('make', {}).get('name', '')
        model_name = variant.get('generation', {}).get('model', {}).get('name', '')
        
        summary_text = f"""
        <para>
        <b>Vehicle:</b> {make_name} {model_name} {variant.get('name', '')}<br/>
        <b>Year:</b> {year}<br/>
        <b>Engine:</b> {variant.get('engine_size_cc', 'N/A')} cc, {variant.get('power_hp', 'N/A')} HP<br/>
        <b>Fuel Type:</b> {variant.get('fuel_type', 'N/A')}<br/>
        <b>Transmission:</b> {variant.get('transmission', 'N/A')}<br/>
        <b>Annual Mileage:</b> {annual_mileage:,} km
        </para>
        """
        elements.append(Paragraph(summary_text, self.styles['CustomBody']))
        elements.append(Spacer(1, 10))
        
        return elements
