from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
from datetime import datetime

def generate_pdf_report(analysis_data: dict) -> io.BytesIO:
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=22,
        textColor=HexColor('#1d4ed8'),
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor('#6b7280'),
        spaceAfter=16,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        'SectionHead',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=HexColor('#1e3a5f'),
        spaceBefore=16,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        'BodyText2',
        parent=styles['Normal'],
        fontSize=10,
        leading=15,
        textColor=HexColor('#374151'),
        spaceAfter=8
    )

    small_style = ParagraphStyle(
        'SmallText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=HexColor('#9ca3af'),
        alignment=TA_CENTER
    )

    elements = []

    # --- HEADER ---
    elements.append(Paragraph("🌍 Bhumi Drishti", title_style))
    elements.append(Paragraph("Land Due Diligence Report", subtitle_style))
    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    elements.append(Paragraph(f"Generated on {now}", small_style))
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(
        width="100%", thickness=1.5,
        color=HexColor('#2563eb'), spaceAfter=12
    ))

    # Extract quantitative data
    qd = analysis_data.get('quantitative_data', {})
    indicators = qd.get('indicators', [])
    details = qd.get('details', {})
    risk_summary = qd.get('risk_summary', 'No summary available.')

    def get_indicator(cat):
        for ind in indicators:
            if ind.get('category') == cat:
                return ind
        return {'value': 0, 'sub_value': 0}

    flood = get_indicator('flood')
    landslide = get_indicator('landslide')
    agri = get_indicator('agri')

    # --- RISK OVERVIEW ---
    elements.append(Paragraph("Risk Overview", heading_style))

    risk_data = [
        ['Category', 'Average Risk', 'Peak Risk', 'Assessment'],
        [
            'Flood Risk',
            f"{flood.get('value', 0):.0f}%",
            f"{flood.get('sub_value', 0):.0f}%",
            _risk_label(flood.get('value', 0))
        ],
        [
            'Landslide Risk',
            f"{landslide.get('value', 0):.0f}%",
            f"{landslide.get('sub_value', 0):.0f}%",
            _risk_label(landslide.get('value', 0))
        ],
        [
            'Agri Suitability',
            f"{agri.get('value', 0):.0f}%",
            '--',
            _agri_label(agri.get('value', 0))
        ],
    ]

    risk_table = Table(risk_data, colWidths=[100, 85, 75, 100])
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#d1d5db')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#f9fafb'), HexColor('#ffffff')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(risk_table)
    elements.append(Spacer(1, 6))

    elements.append(Paragraph(
        "<i>Peak values represent the worst-case scenario found at any point within your plot boundary. "
        "They indicate localized hotspots where risk is highest.</i>",
        ParagraphStyle('Note', parent=body_style, fontSize=9, textColor=HexColor('#6b7280'))
    ))

    elements.append(Paragraph("Technical Details", heading_style))

    tech_data = [
        ['Parameter', 'Value', 'Parameter', 'Value'],
        ['Slope', f"{_safe(details.get('slope'))}\u00b0", 'Elevation', f"{_safe(details.get('elevation'), 0)} m"],
        ['Land Use', str(details.get('lulc', 'Unknown')), 'Soil Clay', f"{_safe(details.get('soil_clay_pct'))}%"],
        ['Rainfall', f"{_safe(details.get('rainfall'), 0)} mm", 'TWI', _safe(details.get('twi'), 2)],
        ['SPI', _safe(details.get('spi'), 3), 'River Dist.', f"{details.get('dist_river_m', '--')} m"],
        ['NDVI-wet', _safe(details.get('ndvi_wet'), 3), 'NDVI-\u0394', _safe(details.get('ndvi_delta'), 3)],
    ]

    tech_table = Table(tech_data, colWidths=[80, 80, 80, 80])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f3f4f6')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#e5e7eb')),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(tech_table)

    elements.append(Paragraph("Factor Relationships", heading_style))

    slope_val = details.get('slope', 0) or 0
    elev_val  = details.get('elevation', 0) or 0
    clay_val  = details.get('soil_clay_pct', 0) or 0     # already in %
    rain_val  = details.get('rainfall', 0) or 0
    ndvi_wet  = details.get('ndvi_wet', 0) or 0
    ndvi_delta = details.get('ndvi_delta', 0) or 0

    elements.append(Paragraph(
        f"<b>Slope + Elevation → Landslide Risk:</b> With a slope of {slope_val:.1f}° and elevation of "
        f"{elev_val:.0f} m, "
        f"{'the terrain has significant gradient that increases landslide susceptibility, especially during heavy rains.' if slope_val > 10 else 'the relatively flat terrain reduces landslide risk significantly.'}",
        body_style
    ))

    elements.append(Paragraph(
        f"<b>Soil Clay + Rainfall → Agriculture:</b> Soil clay content at {clay_val:.1f}% "
        f"{'is in the optimal range (1.5–3.5%) for moisture retention.' if 15 <= clay_val * 10 <= 35 else 'may affect water retention for crops.'} "
        f"Annual rainfall of {rain_val:.0f} mm {'is adequate for most crops.' if rain_val > 800 else 'is low and irrigation may be needed.'}",
        body_style
    ))

    elements.append(Paragraph(
        f"<b>Vegetation (Seasonal NDVI):</b> Wet-season NDVI of {ndvi_wet:.3f} and "
        f"seasonal delta (\u0394) of {ndvi_delta:.3f} indicate "
        f"{'strong crop seasonality — a positive sign for agricultural use.' if ndvi_delta > 0.15 else 'moderate seasonality, typical for mixed cropland.'} "
        "(Raw annual NDVI is non-informative in this ROI; wet-season and delta values are used by the model.)",
        body_style
    ))

    flood_val = flood.get('value', 0)
    flood_peak = flood.get('sub_value', 0)
    elements.append(Paragraph(
        f"<b>Flood Probability:</b> Average flood probability of {flood_val:.0f}% with a peak of {flood_peak:.0f}%. "
        f"{'The low peak value means even the most vulnerable spot on your plot has minimal flood exposure.' if flood_peak < 20 else 'The elevated peak value indicates specific areas of your plot are more flood-prone and may require drainage solutions.' if flood_peak < 50 else 'The high peak value is a serious concern — parts of your plot have historically experienced significant flooding.'}",
        body_style
    ))

    elements.append(Paragraph("AI Risk Assessment", heading_style))

    clean_summary = risk_summary.replace('**', '')
    for para in clean_summary.split('\n\n'):
        para = para.strip()
        if para:
            elements.append(Paragraph(para, body_style))

    # --- FOOTER ---
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(
        width="100%", thickness=1,
        color=HexColor('#e5e7eb'), spaceAfter=8
    ))
    elements.append(Paragraph(
        "This report is generated by Bhumi Drishti using satellite imagery, global geospatial datasets, "
        "and AI analysis. Data accuracy depends on source resolution and availability. "
        "This is not a substitute for professional geological or hydrological surveys.",
        ParagraphStyle('Disclaimer', parent=small_style, alignment=TA_LEFT, fontSize=8)
    ))
    elements.append(Paragraph(
        f"© {datetime.now().year} Bhumi Drishti | Confidential",
        small_style
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def _risk_label(val):
    if val >= 50:
        return '⚠️ HIGH'
    elif val >= 20:
        return '⚡ MODERATE'
    return '✅ LOW'


def _agri_label(val):
    if val >= 70:
        return '🌿 EXCELLENT'
    elif val >= 40:
        return '🌱 MODERATE'
    return '⚠️ LOW'


def _safe(v, decimals=1):
    if v is None or not isinstance(v, (int, float)):
        return '--'
    return f"{v:.{decimals}f}"
