# app/modules/reports/pdf.py

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


class PDFGenerator:

    PRIMARY = colors.HexColor("#0F172A")
    GOLD = colors.HexColor("#F59E0B")
    GREEN = colors.HexColor("#16A34A")
    LIGHT = colors.HexColor("#F8FAFC")
    BORDER = colors.HexColor("#CBD5E1")

    @staticmethod
    def money(value):
        try:
            return f"KES {float(value):,.0f}"
        except:
            return "KES 0"

    @staticmethod
    def generate_valuation_report(report):

        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.2 * cm,
            leftMargin=1.2 * cm,
            topMargin=1.2 * cm,
            bottomMargin=1.2 * cm,
        )

        styles = getSampleStyleSheet()

        title = ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            alignment=TA_CENTER,
            textColor=PDFGenerator.PRIMARY,
            fontSize=22,
            spaceAfter=12,
        )

        heading = ParagraphStyle(
            "Heading",
            parent=styles["Heading2"],
            textColor=PDFGenerator.GOLD,
            spaceAfter=6,
        )

        normal = styles["BodyText"]

        story = []

        valuation = report.get("valuation", {})
        vehicle = valuation.get("vehicle", {})

        story.append(
            Paragraph(
                "<b>AUTO-D KENYA</b><br/>Vehicle Valuation Report",
                title,
            )
        )

        story.append(
            Paragraph(
                datetime.now().strftime(
                    "Generated %d %B %Y %H:%M"
                ),
                normal,
            )
        )

        story.append(Spacer(1, 0.5 * cm))

        # Main Value

        value = valuation.get(
            "estimated_vehicle_value",
            valuation.get("market_value", 0),
        )

        big = ParagraphStyle(
            "big",
            parent=styles["Heading1"],
            alignment=TA_CENTER,
            textColor=PDFGenerator.GREEN,
            fontSize=30,
        )

        story.append(
            Paragraph(
                PDFGenerator.money(value),
                big,
            )
        )

        story.append(
            Paragraph(
                "<b>Estimated Market Value</b>",
                ParagraphStyle(
                    "center",
                    alignment=TA_CENTER,
                ),
            )
        )

        story.append(Spacer(1, 0.4 * cm))

        vr = valuation.get("estimated_value_range", {})

        confidence = valuation.get("confidence_score", 0)

        summary_table = Table(
            [
                [
                    "Confidence",
                    f"{confidence}%",
                ],
                [
                    "Value Range",
                    f"{PDFGenerator.money(vr.get('minimum',0))}  -  {PDFGenerator.money(vr.get('maximum',0))}",
                ],
                [
                    "Retail",
                    PDFGenerator.money(
                        valuation.get("retail_value", 0)
                    ),
                ],
                [
                    "Dealer",
                    PDFGenerator.money(
                        valuation.get("dealer_value", 0)
                    ),
                ],
                [
                    "Trade In",
                    PDFGenerator.money(
                        valuation.get("trade_value", 0)
                    ),
                ],
            ],
            colWidths=[5 * cm, 10 * cm],
        )

        summary_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.3, PDFGenerator.BORDER),
                    ("BACKGROUND", (0, 0), (0, -1), PDFGenerator.LIGHT),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        story.append(summary_table)

        story.append(Spacer(1, 0.5 * cm))

        story.append(Paragraph("Vehicle Profile", heading))

        vehicle_table = Table(
            [
                ["Make", vehicle.get("make", "")],
                ["Model", vehicle.get("model", "")],
                ["Variant", vehicle.get("variant", "")],
                ["Year", vehicle.get("year", "")],
                ["Mileage", f"{vehicle.get('mileage',0):,} km"],
                ["Fuel", vehicle.get("fuel_type", "")],
                ["Transmission", vehicle.get("transmission", "")],
                ["Engine", f"{vehicle.get('engine_size_cc',0)} cc"],
                ["Body", vehicle.get("body_type", "")],
                ["Condition", vehicle.get("condition", "")],
                ["Location", vehicle.get("location", "")],
            ],
            colWidths=[5 * cm, 10 * cm],
        )

        vehicle_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, PDFGenerator.BORDER),
                    ("BACKGROUND", (0, 0), (0, -1), PDFGenerator.LIGHT),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        story.append(vehicle_table)

        story.append(Spacer(1, 0.5 * cm))

        story.append(
            Paragraph("Valuation Factors", heading)
        )

        factors = Table(
            [
                ["Mileage", valuation.get("mileage_factor", 1)],
                ["Condition", valuation.get("condition_factor", 1)],
                ["Accident", valuation.get("accident_factor", 1)],
                ["Location", valuation.get("location_factor", 1)],
                ["Demand", valuation.get("demand_factor", 1)],
                ["Trend", valuation.get("trend_factor", 1)],
                ["Features", valuation.get("feature_factor", 1)],
            ],
            colWidths=[5 * cm, 10 * cm],
        )

        factors.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, PDFGenerator.BORDER),
                    ("BACKGROUND", (0, 0), (0, -1), PDFGenerator.LIGHT),
                ]
            )
        )

        story.append(factors)

        story.append(Spacer(1, 0.5 * cm))

        story.append(
            Paragraph(
                "Valuation Summary",
                heading,
            )
        )

        story.append(
            Paragraph(
                valuation.get(
                    "price_explanation",
                    {},
                ).get(
                    "summary",
                    "Vehicle valued using AUTO-D market valuation engine.",
                ),
                normal,
            )
        )

        story.append(Spacer(1, 0.5 * cm))

        story.append(
            Paragraph(
                "Methodology",
                heading,
            )
        )

        story.append(
            Paragraph(
                """
                This valuation is calculated using the AUTO-D valuation engine
                based on verified market transactions, dealer pricing,
                depreciation modelling, mileage analysis,
                regional market demand and vehicle condition.
                """,
                normal,
            )
        )

        story.append(Spacer(1, 0.5 * cm))

        story.append(
            Paragraph(
                "Disclaimer",
                heading,
            )
        )

        story.append(
            Paragraph(
                """
                This report provides an indicative market value only.
                It is not a guarantee of sale price or insurance settlement.
                Final value may vary following physical inspection,
                maintenance history and prevailing market conditions.
                """,
                normal,
            )
        )

        doc.build(story)

        pdf = buffer.getvalue()
        buffer.close()

        return pdf
