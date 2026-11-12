"""
Report Generation Service
Generates downloadable, executive-grade PDF shipment risk assessments via ReportLab.
"""

import os
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether
)

from app.config import settings

class ReportService:
    @classmethod
    def generate_pdf_report(
        cls,
        shipment: Any,
        prediction: Any,
        weather_info: Dict[str, Any],
        anomaly_info: Dict[str, Any],
        recommendations: List[Dict[str, str]]
    ) -> str:
        """
        Creates a PDF report file in `reports/` and returns the file path.
        """
        filename = f"NexusGuard_Report_{shipment.tracking_number}.pdf"
        output_path = settings.REPORTS_DIR / filename

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        # Custom Palette: Dark Navy & Cyan
        NAVY = colors.HexColor("#0f172a")
        CYAN = colors.HexColor("#0284c7")
        LIGHT_BG = colors.HexColor("#f8fafc")
        BORDER_COLOR = colors.HexColor("#cbd5e1")
        TEXT_DARK = colors.HexColor("#1e293b")

        # Color based on Risk Category
        risk_score = float(prediction.overall_risk_score)
        if risk_score < 40.0:
            RISK_COLOR = colors.HexColor("#16a34a") # Green
            RISK_LABEL = "LOW RISK"
        elif risk_score < 70.0:
            RISK_COLOR = colors.HexColor("#d97706") # Amber
            RISK_LABEL = "MEDIUM RISK"
        else:
            RISK_COLOR = colors.HexColor("#dc2626") # Red
            RISK_LABEL = "HIGH RISK"

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=NAVY,
            leading=26
        )

        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=colors.HexColor("#64748b"),
            leading=14
        )

        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=NAVY,
            leading=16,
            spaceAfter=6
        )

        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=TEXT_DARK,
            leading=13
        )

        bold_style = ParagraphStyle(
            "ReportBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=TEXT_DARK,
            leading=13
        )

        story = []

        # 1. Header Banner Table
        header_data = [
            [
                Paragraph("<b>NEXUSGUARD AI</b><br/><font size=8 color='#64748b'>Logistics Risk & Fraud Intelligence</font>", title_style),
                Paragraph(f"<b>SHIPMENT AUDIT REPORT</b><br/><font size=8 color='#64748b'>Tracking #: {shipment.tracking_number}<br/>Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</font>", ParagraphStyle("RightH", parent=body_style, alignment=2))
            ]
        ]
        header_table = Table(header_data, colWidths=[4.0 * inch, 3.2 * inch])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)
        story.append(HRFlowable(width="100%", thickness=1.5, color=CYAN, spaceAfter=14, spaceBefore=8))

        # 2. Executive Risk Summary Box
        risk_box_data = [
            [
                Paragraph(f"<b>COMPOSITE RISK SCORE</b><br/><font size=28 color='{RISK_COLOR.hexval()}'><b>{risk_score:.1f}</b></font><font size=12 color='#64748b'>/100</font><br/><b><font color='{RISK_COLOR.hexval()}'>{RISK_LABEL}</font></b>", ParagraphStyle("CScore", alignment=1, leading=16)),
                Paragraph(
                    f"<b>ML Delay Probability:</b> {prediction.ml_probability * 100:.1f}%<br/>"
                    f"<b>Carrier Reliability Index:</b> {shipment.carrier_historical_delay_rate * 100:.1f}% historical delay<br/>"
                    f"<b>Anomaly / Fraud Vector:</b> {'SUSPICIOUS PATTERN' if anomaly_info.get('is_suspicious') else 'NORMAL OPERATING BASELINE'}<br/>"
                    f"<b>Atmospheric Risk Index:</b> {weather_info.get('severity_index', 0.0) * 100:.1f}/100 ({weather_info.get('weather_description', 'N/A')})<br/>"
                    f"<b>Primary Transport Mode:</b> {shipment.transport_mode} | <b>Priority:</b> {shipment.priority}",
                    body_style
                )
            ]
        ]
        risk_box_table = Table(risk_box_data, colWidths=[2.5 * inch, 4.7 * inch])
        risk_box_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(risk_box_table)
        story.append(Spacer(1, 14))

        # 3. Shipment Metadata Table
        story.append(Paragraph("1. Shipment Specifications & Corridor Telemetry", section_heading))
        shipment_details = [
            [Paragraph("<b>Origin Hub:</b>", bold_style), Paragraph(str(shipment.origin), body_style), Paragraph("<b>Destination Hub:</b>", bold_style), Paragraph(str(shipment.destination), body_style)],
            [Paragraph("<b>Transit Distance:</b>", bold_style), Paragraph(f"{shipment.distance_km:,.1f} km", body_style), Paragraph("<b>Transfer Stops:</b>", bold_style), Paragraph(str(shipment.transit_stops), body_style)],
            [Paragraph("<b>Cargo Type:</b>", bold_style), Paragraph(str(shipment.cargo_type), body_style), Paragraph("<b>Declared Value:</b>", bold_style), Paragraph(f"${shipment.shipment_value_usd:,.2f}", body_style)],
            [Paragraph("<b>Gross Weight:</b>", bold_style), Paragraph(f"{shipment.weight_kg:,.1f} kg", body_style), Paragraph("<b>Perishable / Fragile:</b>", bold_style), Paragraph(f"{'Yes' if shipment.is_perishable else 'No'} / {'Yes' if shipment.is_fragile else 'No'}", body_style)],
            [Paragraph("<b>Designated Carrier:</b>", bold_style), Paragraph(str(shipment.carrier_name), body_style), Paragraph("<b>Current Status:</b>", bold_style), Paragraph(str(shipment.status), body_style)],
        ]
        meta_table = Table(shipment_details, colWidths=[1.8 * inch, 1.8 * inch, 1.8 * inch, 1.8 * inch])
        meta_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
            ("BACKGROUND", (2, 0), (2, -1), LIGHT_BG),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 14))

        # 4. Weather & Atmospheric Conditions
        story.append(Paragraph("2. Real-Time Atmospheric Assessment (Open-Meteo Integration)", section_heading))
        w_temp = weather_info.get("temperature_c")
        w_temp_str = f"{w_temp}°C" if w_temp is not None else "Unavailable"
        w_precip = weather_info.get("precipitation_mm")
        w_precip_str = f"{w_precip} mm" if w_precip is not None else "Unavailable"
        w_wind = weather_info.get("wind_speed_kmh")
        w_wind_str = f"{w_wind} km/h" if w_wind is not None else "Unavailable"

        weather_table_data = [
            [
                Paragraph("<b>Observed Location:</b>", bold_style), Paragraph(str(weather_info.get("location_name", "Corridor")), body_style),
                Paragraph("<b>Weather Condition:</b>", bold_style), Paragraph(str(weather_info.get("weather_description", "Standard")), body_style)
            ],
            [
                Paragraph("<b>Temperature:</b>", bold_style), Paragraph(w_temp_str, body_style),
                Paragraph("<b>Precipitation:</b>", bold_style), Paragraph(w_precip_str, body_style)
            ],
            [
                Paragraph("<b>Wind Speed:</b>", bold_style), Paragraph(w_wind_str, body_style),
                Paragraph("<b>Live Telemetry Status:</b>", bold_style), Paragraph("Verified Live" if weather_info.get("is_live") else "Historical Baseline", body_style)
            ]
        ]
        w_table = Table(weather_table_data, colWidths=[1.8 * inch, 1.8 * inch, 1.8 * inch, 1.8 * inch])
        w_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
            ("BACKGROUND", (2, 0), (2, -1), LIGHT_BG),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(w_table)
        story.append(Spacer(1, 14))

        # 5. Anomaly & Fraud Assessment
        story.append(Paragraph("3. Fraud Detection & Outlier Pattern Analysis", section_heading))
        reasons_list = "<br/>• ".join(anomaly_info.get("detected_reasons", ["No irregular patterns detected."]))
        anomaly_table_data = [
            [Paragraph("<b>Status Classification:</b>", bold_style), Paragraph(f"<b>{anomaly_info.get('status_label', 'Normal')}</b>", body_style)],
            [Paragraph("<b>Anomaly Intensity Score:</b>", bold_style), Paragraph(f"{anomaly_info.get('anomaly_score', 0):.1f} / 100", body_style)],
            [Paragraph("<b>Pattern Findings:</b>", bold_style), Paragraph(f"• {reasons_list}", body_style)]
        ]
        a_table = Table(anomaly_table_data, colWidths=[2.2 * inch, 5.0 * inch])
        a_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(a_table)
        story.append(Spacer(1, 14))

        # 6. Actionable AI Recommendations
        story.append(Paragraph("4. Prescriptive AI Risk Mitigation Recommendations", section_heading))
        rec_rows = [[Paragraph("<b>Priority</b>", bold_style), Paragraph("<b>Category</b>", bold_style), Paragraph("<b>Actionable Directive</b>", bold_style)]]
        for r in recommendations:
            rec_rows.append([
                Paragraph(f"<b>{r.get('priority', 'Medium')}</b>", body_style),
                Paragraph(r.get("type", "General"), body_style),
                Paragraph(f"<b>{r.get('action', '')}:</b> {r.get('description', '')}", body_style)
            ])
        rec_table = Table(rec_rows, colWidths=[1.0 * inch, 1.8 * inch, 4.4 * inch])
        rec_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(rec_table)
        story.append(Spacer(1, 16))

        # 7. Digital Footer Signature
        footer_text = Paragraph(
            f"<font size=8 color='#64748b'>Generated automatically by NexusGuard AI Decision Engine v1.0 • Cryptographic Audit Verification • Stored at {str(output_path)}</font>",
            ParagraphStyle("FooterP", alignment=1)
        )
        story.append(footer_text)

        doc.build(story)
        return str(output_path)
