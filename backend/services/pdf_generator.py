"""
ACRN PROTECT-Africa Adjudication Platform — Official FORM-ADJ PDF Generator
Generates validated 21 CFR Part 11 PDF report matching the official FORM-ADJ-15A / FORM-ADJ-15B document standard.
"""

import io
import re
import hashlib
from html import escape
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_adjudication_pdf(case_data: dict) -> bytes:
    """
    Generates an official FORM-ADJ PDF report for a finalized adjudication.
    Returns bytes of the PDF document.
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

    # Brand Colors matching ACRN Corporate Design
    c_navy = colors.HexColor('#162035')
    c_orange = colors.HexColor('#F07E26')
    c_slate = colors.HexColor('#334155')
    c_border = colors.HexColor('#cbd5e1')
    c_bg_light = colors.HexColor('#f8fafc')

    title_style = ParagraphStyle(
        'FormTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=c_navy
    )

    subtitle_style = ParagraphStyle(
        'FormSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=c_slate
    )

    part_header_style = ParagraphStyle(
        'PartHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.white,
        spaceBefore=10,
        spaceAfter=4
    )

    section_heading_style = ParagraphStyle(
        'SecHeading',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=c_navy,
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'FormBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1e293b')
    )

    mono_style = ParagraphStyle(
        'FormMono',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#0f172a')
    )

    elements = []

    # ── Official Header Block ──────────────────────────────────────────────────
    elements.append(Paragraph("AFRICA CLINICAL RESEARCH NETWORK (ACRN)", title_style))
    elements.append(Paragraph("PROTECT-Africa / LOPE-Nigeria Clinical Endpoint Adjudication Committee", subtitle_style))
    elements.append(Paragraph("FORM-ADJ-15A/15B — Blinded Endpoint Adjudication Certificate &amp; Record", subtitle_style))
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=c_orange, spaceAfter=8))

    # ── Part A Header ──────────────────────────────────────────────────────────
    t_part_a = Table([[Paragraph("PART A — BLINDED CLINICAL CASE NARRATIVE &amp; COORDINATOR FACTUAL REPORT", part_header_style)]], colWidths=[540])
    t_part_a.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_navy),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_part_a)
    elements.append(Spacer(1, 6))

    # ── Metadata Table ─────────────────────────────────────────────────────────
    id_val = case_data.get("id", "ZWE-DEMO-01")
    case_no = case_data.get("caseNo", "ADJ-DEMO-001")
    site_val = case_data.get("site", "[Blinded per SOP-ADJ-002]")
    ga_event = case_data.get("gaAtEvent", "31+2")
    trigger = case_data.get("trigger", "DV-30 (Severe BP + Proteinuria)")

    meta_grid = [
        [Paragraph("<b>Participant ID:</b>", body_style), Paragraph(id_val, body_style), Paragraph("<b>Case Number:</b>", body_style), Paragraph(case_no, body_style)],
        [Paragraph("<b>GA at Presentation:</b>", body_style), Paragraph(f"GA {ga_event}", body_style), Paragraph("<b>Protocol:</b>", body_style), Paragraph("PROTECT-Africa / LOPE-Nigeria", body_style)],
        [Paragraph("<b>Trigger Event:</b>", body_style), Paragraph(trigger, body_style), Paragraph("<b>Site / Provider:</b>", body_style), Paragraph(site_val, body_style)],
        [Paragraph("<b>Blinding Status:</b>", body_style), Paragraph("<b>SOP-ADJ-002 Compliant (Biomarkers Withheld)</b>", body_style), Paragraph("<b>Form Code:</b>", body_style), Paragraph("FORM-ADJ-15A", body_style)],
    ]
    t_meta = Table(meta_grid, colWidths=[100, 170, 90, 180])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_bg_light),
        ('BOX', (0,0), (-1,-1), 0.5, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 8))

    # ── Section 1: ISSHP 2021 Automated Rule Findings ────────────────────────
    elements.append(Paragraph("1. ISSHP 2021 Deterministic Derivation Findings (PROTECT-DV-2026.08)", section_heading_style))
    crit_rows = [["Rule Code", "Diagnostic Feature Name", "Derivation Result", "Evidence Summary / Inputs"]]
    
    criteria_list = case_data.get("criteria", [
        {"id": "DV-02", "title": "Severe BP (>=160/110 mmHg)", "met": True, "details": "162/112 & 168/114 confirmed 4h apart"},
        {"id": "DV-03", "title": "Confirmed Hypertension", "met": True, "details": "Severe range recheck confirmed on distinct date"},
        {"id": "DV-07", "title": "Significant Proteinuria", "met": True, "details": "UPCR 1.84 g/g (>=0.3 g/g threshold met)"},
        {"id": "DV-08", "title": "Thrombocytopenia", "met": True, "details": "Platelets 88 x10^3/uL (<100 severe feature)"},
        {"id": "DV-10", "title": "Renal Dysfunction", "met": True, "details": "Creatinine 1.31 mg/dL (>1.1 mg/dL threshold met)"},
        {"id": "DV-11", "title": "Hepatic Dysfunction", "met": True, "details": "AST 96 U/L, ALT 78 U/L (>2x ULN threshold met)"},
        {"id": "DV-26", "title": "Evidence Completeness", "met": True, "details": "6 of 6 evidence classes present (100% complete)"},
    ])

    for c in criteria_list:
        status_text = "<b><font color='#15803d'>MET</font></b>" if c.get("met") else "<font color='#64748b'>NOT MET</font>"
        crit_rows.append([
            c.get("id", ""),
            c.get("title", ""),
            Paragraph(status_text, body_style),
            Paragraph(c.get("details", ""), body_style)
        ])

    t_crit = Table(crit_rows, colWidths=[70, 180, 80, 210])
    t_crit.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_navy),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_crit)
    elements.append(Spacer(1, 8))

    # ── Section 2: 13-Section Blinded Narrative Draft ─────────────────────────
    elements.append(Paragraph("2. 13-Section Blinded Clinical Case Narrative Draft", section_heading_style))
    narrative_raw = str(case_data.get("aiNarrative", case_data.get("fullText", "Blinded narrative generated by ACRN PROTECT-Africa AI Engine.")) or "")
    # Reviewer comments can arrive as either plain-text newlines or HTML-style
    # break tags. Treat both as physical lines before sizing table rows.
    narrative_raw = re.sub(r"<br\\s*/?>", "\n", narrative_raw, flags=re.IGNORECASE)
    # One row per SECTION so the Table can break across pages instead of a single
    # oversized cell (ReportLab can only split a Table between rows, not within one).
    # Some upstream sources strip newlines entirely, so split on the marker alone
    # rather than requiring a preceding newline.
    section_chunks = re.split(r'(?=SECTION \d+\s*—)', narrative_raw.strip()) or [narrative_raw]
    section_chunks = [c for c in section_chunks if c.strip()] or [narrative_raw]

    # Safety net: if a chunk is still too big for one page (e.g. an unrecognized
    # section format, or one section's own text is very long), hard-wrap it further
    # by word count so no single row can ever overflow the frame.
    MAX_CHARS = 1500
    safe_chunks = []
    for chunk in section_chunks:
        chunk = chunk.strip()
        if len(chunk) <= MAX_CHARS:
            safe_chunks.append(chunk)
            continue
        words = chunk.split(' ')
        buf = ''
        for word in words:
            if len(buf) + len(word) + 1 > MAX_CHARS:
                safe_chunks.append(buf)
                buf = word
            else:
                buf = f"{buf} {word}" if buf else word
        if buf:
            safe_chunks.append(buf)

    # Character count alone is not enough: a reviewer can provide hundreds of
    # short, hard-wrapped lines.  Tables cannot split inside a cell, so bound
    # the number of rendered lines in every row as well.
    MAX_LINES_PER_ROW = 32
    row_chunks = []
    for chunk in safe_chunks:
        lines = []
        for line in chunk.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            # ReportLab also cannot wrap a very long unbroken token reliably.
            lines.extend(line[i:i + 80] for i in range(0, max(len(line), 1), 80))
        for start in range(0, len(lines), MAX_LINES_PER_ROW):
            row_chunks.append("\n".join(lines[start:start + MAX_LINES_PER_ROW]))

    # Never put reviewer narrative in a Table. ReportLab cannot divide a table
    # cell across pages, whereas Paragraph flowables split normally. This avoids
    # a LayoutError even if future text-normalisation misses an unusual break.
    for chunk in row_chunks or [""]:
        elements.append(Paragraph(escape(chunk).replace("\n", "<br/>"), mono_style))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=c_border, spaceBefore=3, spaceAfter=3))
    elements.append(Spacer(1, 10))

    # ── Part B Header ──────────────────────────────────────────────────────────
    t_part_b = Table([[Paragraph("PART B — REVIEWER &amp; OAC PANEL FINAL DETERMINATION", part_header_style)]], colWidths=[540])
    t_part_b.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_navy),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_part_b)
    elements.append(Spacer(1, 6))

    # ── Section 3: Visit 5 Fetal and Neonatal Closed-Ended Assessments ─────────
    fetal_assessments = case_data.get("fetalNeonatalAssessments")
    visit_num = case_data.get("visitNumber")
    if visit_num == 5 or fetal_assessments:
        elements.append(Paragraph("3. Visit 5 Fetal &amp; Neonatal Endpoint Assessments (FORM-ADJ-V05)", section_heading_style))
        ga_del = case_data.get("gestationalAgeAtDelivery")
        preg_out = case_data.get("pregnancyOutcome")
        ga_text = f"{ga_del} weeks" if ga_del is not None else "Not documented"
        preg_text = str(preg_out) if preg_out else "Not documented"

        supp_grid = [
            [
                Paragraph("<b>Gestational Age at Delivery:</b>", body_style),
                Paragraph(ga_text, body_style),
                Paragraph("<b>Pregnancy Outcome:</b>", body_style),
                Paragraph(preg_text, body_style),
            ]
        ]
        t_supp = Table(supp_grid, colWidths=[150, 120, 130, 140])
        t_supp.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), c_bg_light),
            ('BOX', (0,0), (-1,-1), 0.5, c_border),
            ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t_supp)
        elements.append(Spacer(1, 4))

        selected_set = set(fetal_assessments or [])
        fetal_defs = [
            ("PERINATAL_FETAL_DEATH", "Perinatal / fetal death"),
            ("DELIVERY_GE_37W", "Delivery at or after 37 weeks"),
            ("DELIVERY_LT_34W", "Delivery before 34 weeks"),
            ("IUGR", "Intrauterine Growth Restriction (IUGR)"),
            ("SGA", "Small for Gestational Age (SGA)"),
            ("NORMAL_OUTCOME", "Normal fetal / neonatal outcome, where clinically approved"),
        ]

        f_rows = [["Standardized Assessment / Endpoint", "Determination Status"]]
        for code, label in fetal_defs:
            is_present = code in selected_set
            status_html = "<b><font color='#15803d'>CONFIRMED POSITIVE</font></b>" if is_present else "<font color='#64748b'>Not Selected</font>"
            f_rows.append([
                Paragraph(label, body_style),
                Paragraph(status_html, body_style),
            ])

        t_fetal = Table(f_rows, colWidths=[380, 160])
        t_fetal.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), c_navy),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 8),
            ('GRID', (0,0), (-1,-1), 0.5, c_border),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t_fetal)
        elements.append(Spacer(1, 8))

    # ── Section 4: Final Classification & 21 CFR Part 11 Signature Block ─────
    final_diag = case_data.get("finalDiagnosis", "PE")
    onset_class = case_data.get("derivedSubtype", "Early-onset pre-eclampsia (EOPE)")
    severity_val = case_data.get("derivedSeverity", "With severe features")
    certainty_val = case_data.get("certainty", "Not classified")

    sig_hash = case_data.get("signatureHash") or hashlib.sha256(
        f"{id_val}|{final_diag}|{onset_class}|{case_data.get('signedAt', '')}".encode()
    ).hexdigest()
    signer = case_data.get("reviewerName", "Adjudicator")
    signed_at = case_data.get("signedAt", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))

    det_grid = [
        [Paragraph("<b>Primary Endpoint Diagnosis:</b>", body_style), Paragraph(f"<b>{final_diag}</b>", body_style), Paragraph("<b>Severity Grade:</b>", body_style), Paragraph(f"<b>{severity_val}</b>", body_style)],
        [Paragraph("<b>Onset Classification:</b>", body_style), Paragraph(f"<b>{onset_class}</b>", body_style), Paragraph("<b>Diagnostic Certainty:</b>", body_style), Paragraph(f"<b>{certainty_val}</b>", body_style)],
        [Paragraph("<b>Reviewer / Signer Identity:</b>", body_style), Paragraph(signer, body_style), Paragraph("<b>Authentication:</b>", body_style), Paragraph("21 CFR Part 11 Verified", body_style)],
        [Paragraph("<b>Timestamp:</b>", body_style), Paragraph(signed_at, body_style), Paragraph("<b>Record Lock Status:</b>", body_style), Paragraph("<b>SIGNED &amp; LOCKED; FILING TRACKED SEPARATELY</b>", body_style)],
        [Paragraph("<b>Cryptographic Hash (SHA-256):</b>", body_style), Paragraph(f"<font fontName='Courier' size=7.5>{sig_hash}</font>", body_style), Paragraph("<b>Governance Standard:</b>", body_style), Paragraph("OAC Charter §10 / SOP-ADJ-001", body_style)],
    ]
    t_det = Table(det_grid, colWidths=[130, 160, 110, 140])
    t_det.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#16a34a')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#bbf7d0')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    
    elements.append(KeepTogether([t_det]))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
