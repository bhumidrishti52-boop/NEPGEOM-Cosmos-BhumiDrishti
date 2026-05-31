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