"""
Report Generation Service.
Generates comprehensive downloadable PDF farm reports using ReportLab.
Compiles soil chemistry/observations, weather summaries, crop recommendations,
monitoring timeline with health scores, irrigation advice history, and agronomic disclaimers.
"""
import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_farm_pdf_report(farm_data, soil_report=None, latest_weather=None,
                             monitoring_records=None, irrigation_advice=None):
    """
    Builds a professional, comprehensive multi-page PDF farm dossier.
    Returns bytes buffer of the generated PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Brand Palette (Agricultural Emerald & Sage)
    c_primary = colors.HexColor('#1b4332')
    c_secondary = colors.HexColor('#2d6a4f')
    c_accent = colors.HexColor('#52b788')
    c_light = colors.HexColor('#d8f3dc')
    c_dark = colors.HexColor('#1f2421')
    c_muted = colors.HexColor('#6c757d')
    c_border = colors.HexColor('#e5e7eb')

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=c_primary,
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=c_secondary,
        spaceAfter=12
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=c_secondary,
        spaceBefore=10,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=c_dark
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=c_primary
    )

    badge_style = ParagraphStyle(
        'Badge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Italic'],
        fontName='Helvetica-Oblique',
        fontSize=7.5,
        leading=10,
        textColor=c_muted
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("SMART FARMING AI – CROP DOSSIER & MONITORING REPORT", title_style))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} | Decision-Support Agricultural Intelligence",
        subtitle_style
    ))
    story.append(Spacer(1, 6))

    # 2. Farm Identity Overview Table
    farm_info_data = [
        [
            Paragraph("<b>Farm Name:</b>", body_style),
            Paragraph(str(farm_data.get('farm_name', 'Smart Farm')), body_bold),
            Paragraph("<b>Crop Selected:</b>", body_style),
            Paragraph(f"{farm_data.get('crop_selected', 'General')} ({farm_data.get('variety', 'Standard')})", body_bold)
        ],
        [
            Paragraph("<b>Location:</b>", body_style),
            Paragraph(str(farm_data.get('location', 'Registered Field')), body_style),
            Paragraph("<b>Planting Date:</b>", body_style),
            Paragraph(str(farm_data.get('planting_date', 'N/A')), body_style)
        ],
        [
            Paragraph("<b>Soil Type:</b>", body_style),
            Paragraph(str(farm_data.get('soil_type', 'Loamy')), body_style),
            Paragraph("<b>Current Stage:</b>", body_style),
            Paragraph(str(farm_data.get('current_growth_stage', 'Vegetative')), body_bold)
        ]
    ]

    t_farm = Table(farm_info_data, colWidths=[1.1*inch, 2.3*inch, 1.2*inch, 2.4*inch])
    t_farm.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('BOX', (0, 0), (-1, -1), 1, c_accent),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_farm)
    story.append(Spacer(1, 10))

    # 3. Soil Analysis & Chemical Measurements
    story.append(Paragraph("1. Soil Test Assessment & Fertility Status", section_heading))
    if soil_report:
        rep_type = soil_report.get('report_type', 'test_report')
        source_label = "Optical Soil Photo" if rep_type == 'image' else "Laboratory Chemical Report / Verified Entry"
        story.append(Paragraph(f"<b>Data Source:</b> {source_label}", body_style))
        story.append(Spacer(1, 4))
        
        soil_rows = [
            [
                Paragraph("<b>Parameter</b>", body_bold),
                Paragraph("<b>Measured Value</b>", body_bold),
                Paragraph("<b>Unit</b>", body_bold),
                Paragraph("<b>Agronomic Rating & Status</b>", body_bold)
            ]
        ]

        # N, P, K, pH
        n_val = soil_report.get('nitrogen')
        p_val = soil_report.get('phosphorus')
        k_val = soil_report.get('potassium')
        ph_val = soil_report.get('ph')
        
        if n_val is not None:
            n_rating = "Low" if n_val < 280 else ("High" if n_val > 560 else "Adequate / Medium")
            soil_rows.append([Paragraph("Nitrogen (N)", body_style), Paragraph(str(n_val), body_style), Paragraph("kg/ha", body_style), Paragraph(n_rating, body_style)])
        else:
            soil_rows.append([Paragraph("Nitrogen (N)", body_style), Paragraph("<font color='#d9534f'>Missing</font>", body_style), Paragraph("kg/ha", body_style), Paragraph("Requires Lab Test", body_style)])

        if p_val is not None:
            p_rating = "Low" if p_val < 23 else ("High" if p_val > 56 else "Adequate / Medium")
            soil_rows.append([Paragraph("Phosphorus (P)", body_style), Paragraph(str(p_val), body_style), Paragraph("kg/ha", body_style), Paragraph(p_rating, body_style)])
        else:
            soil_rows.append([Paragraph("Phosphorus (P)", body_style), Paragraph("<font color='#d9534f'>Missing</font>", body_style), Paragraph("kg/ha", body_style), Paragraph("Requires Lab Test", body_style)])

        if k_val is not None:
            k_rating = "Low" if k_val < 140 else ("High" if k_val > 280 else "Adequate / Medium")
            soil_rows.append([Paragraph("Potassium (K)", body_style), Paragraph(str(k_val), body_style), Paragraph("kg/ha", body_style), Paragraph(k_rating, body_style)])
        else:
            soil_rows.append([Paragraph("Potassium (K)", body_style), Paragraph("<font color='#d9534f'>Missing</font>", body_style), Paragraph("kg/ha", body_style), Paragraph("Requires Lab Test", body_style)])

        if ph_val is not None:
            ph_rating = "Acidic" if ph_val < 6.0 else ("Alkaline" if ph_val > 7.5 else "Optimal Neutral")
            soil_rows.append([Paragraph("Soil Reaction (pH)", body_style), Paragraph(str(ph_val), body_style), Paragraph("pH units", body_style), Paragraph(ph_rating, body_style)])
        else:
            soil_rows.append([Paragraph("Soil Reaction (pH)", body_style), Paragraph("<font color='#d9534f'>Missing</font>", body_style), Paragraph("pH units", body_style), Paragraph("Requires Lab Test", body_style)])

        t_soil = Table(soil_rows, colWidths=[1.8*inch, 1.4*inch, 1.0*inch, 2.8*inch])
        t_soil.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), c_light),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
            ('BOX', (0, 0), (-1, -1), 1, c_secondary),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t_soil)
        
        # Summary text
        if soil_report.get('assessment_summary'):
            story.append(Spacer(1, 4))
            story.append(Paragraph(f"<b>Assessment Note:</b> {soil_report['assessment_summary']}", body_style))
    else:
        story.append(Paragraph("<i>No formal soil laboratory report has been linked to this farm record.</i>", body_style))

    story.append(Spacer(1, 10))

    # 4. Weather & Climate Profile
    story.append(Paragraph("2. Environmental & Climate Profile", section_heading))
    if latest_weather and latest_weather.get('success'):
        w_source = latest_weather.get('source', 'Open-Meteo Weather API')
        w_rows = [
            [
                Paragraph("<b>Current Temperature</b>", body_style),
                Paragraph(f"{latest_weather.get('temperature', 'N/A')} °C (Feels like {latest_weather.get('feels_like', 'N/A')} °C)", body_style),
                Paragraph("<b>Relative Humidity</b>", body_style),
                Paragraph(f"{latest_weather.get('humidity', 'N/A')} %", body_style)
            ],
            [
                Paragraph("<b>Recent Rain (48h)</b>", body_style),
                Paragraph(f"{latest_weather.get('recent_rain_48h', 0.0)} mm", body_style),
                Paragraph("<b>Forecast Rain (3-Day)</b>", body_style),
                Paragraph(f"{latest_weather.get('forecast_rain_next_3days', 0.0)} mm", body_style)
            ],
            [
                Paragraph("<b>Sky Condition</b>", body_style),
                Paragraph(str(latest_weather.get('condition', 'Normal')), body_style),
                Paragraph("<b>Weather Data Source</b>", body_style),
                Paragraph(str(w_source), body_style)
            ]
        ]
        t_weather = Table(w_rows, colWidths=[1.8*inch, 1.7*inch, 1.8*inch, 1.7*inch])
        t_weather.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fdfdfd')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
            ('BOX', (0, 0), (-1, -1), 1, c_secondary),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t_weather)
    else:
        story.append(Paragraph("<i>Weather conditions were entered as manual baseline during setup.</i>", body_style))

    story.append(Spacer(1, 10))

    # 5. Smart Irrigation Advisory History
    story.append(Paragraph("3. Smart Irrigation & Water Management Advisory", section_heading))
    if irrigation_advice and irrigation_advice.get('success'):
        status_txt = irrigation_advice.get('status', 'Check soil moisture before watering.')
        story.append(Paragraph(f"<b>Current Irrigation Status:</b> <font color='#1b4332'><b>{status_txt}</b></font>", body_bold))
        story.append(Spacer(1, 3))
        story.append(Paragraph(f"<b>Recommended Action:</b> {irrigation_advice.get('recommended_action', 'Inspect soil condition.')}", body_style))
        story.append(Spacer(1, 3))
        
        reasons = irrigation_advice.get('detailed_reasons', [])
        if reasons:
            story.append(Paragraph("<b>Agronomic Rationale:</b>", body_style))
            for r in reasons[:3]:
                story.append(Paragraph(f"• {r}", body_style))
    else:
        story.append(Paragraph("<i>No irrigation advice generated yet. Run the Smart Irrigation assessment on the dashboard.</i>", body_style))

    story.append(Spacer(1, 10))

    # 6. Crop Growth Observation Timeline
    story.append(Paragraph("4. Foliage Health & Observation Timeline", section_heading))
    if monitoring_records and len(monitoring_records) > 0:
        obs_rows = [
            [
                Paragraph("<b>Date</b>", body_bold),
                Paragraph("<b>Growth Stage</b>", body_bold),
                Paragraph("<b>Canopy %</b>", body_bold),
                Paragraph("<b>Yellowing %</b>", body_bold),
                Paragraph("<b>Health Rating</b>", body_bold),
                Paragraph("<b>AI Foliage Observations</b>", body_bold)
            ]
        ]
        for rec in monitoring_records:
            symptoms_str = ", ".join(rec.get('visible_symptoms', [])) or "Clean foliage"
            obs_rows.append([
                Paragraph(str(rec.get('observation_date')), body_style),
                Paragraph(str(rec.get('growth_stage')), body_style),
                Paragraph(f"{rec.get('canopy_coverage', 0.0)}%", body_style),
                Paragraph(f"{rec.get('chlorosis_yellowing', 0.0)}%", body_style),
                Paragraph(f"<b>{rec.get('health_status', 'Healthy')}</b>", body_style),
                Paragraph(symptoms_str, body_style)
            ])
            
        t_obs = Table(obs_rows, colWidths=[0.9*inch, 1.4*inch, 0.7*inch, 0.8*inch, 1.0*inch, 2.2*inch])
        t_obs.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), c_light),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
            ('BOX', (0, 0), (-1, -1), 1, c_secondary),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t_obs)
    else:
        story.append(Paragraph("<i>No growth stage photos uploaded yet. Use 'Upload New Crop Photo' to track growth.</i>", body_style))

    story.append(Spacer(1, 14))

    # 7. Comprehensive Disclaimers and Limitations
    story.append(Paragraph("5. Scientific Limitations & Legal Disclaimer", section_heading))
    disclaimer_text = (
        "<b>IMPORTANT NOTICE:</b> Smart Farming AI is a decision-support and educational tool engineered "
        "to assist agricultural recordkeeping and early symptom recognition. Optical image analysis assesses surface "
        "coloration and canopy coverage only; it does not replace laboratory wet-chemistry soil tests or certified "
        "phytopathology diagnosis. Soil nutrient values and live weather feeds are compiled from external APIs or "
        "user inputs. Always corroborate recommendations with local agricultural extension services before making "
        "financial or chemical application decisions."
    )
    story.append(Paragraph(disclaimer_text, disclaimer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
