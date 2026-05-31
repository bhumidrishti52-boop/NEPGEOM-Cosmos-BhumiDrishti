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