from pathlib import Path
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

OUT = Path(r"C:\Automation\Adjudication app\output\docx\ACRN_Synthetic_Adjudication_Source_Case_Template.docx")
OUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = "17365D"
BLUE = "DCE6F1"
PALE = "F4F7FB"
ORANGE = "F07E26"
TEAL = "82CFCD"
GRAY = "D9D9D9"
INK = "1F2937"
MUTED = "5B6573"
WHITE = "FFFFFF"


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_border(cell, color=GRAY, size="6"):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = qn(f"w:{edge}")
        element = borders.find(tag)
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:color"), color)


def set_cell_margins(cell, top=80, start=90, bottom=80, end=90):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for name, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{name}"))
        if node is None:
            node = OxmlElement(f"w:{name}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def prevent_row_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def style_run(run, size=9, bold=False, color=INK, font="Aptos"):
    run.font.name = font
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), font)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), font)
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)


def configure_styles(doc):
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    normal.font.size = Pt(9.5)
    normal.font.color.rgb = RGBColor.from_string(INK)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.08

    title = styles["Title"]
    title.font.name = "Aptos Display"
    title._element.rPr.rFonts.set(qn("w:ascii"), "Aptos Display")
    title._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos Display")
    title.font.size = Pt(28)
    title.font.bold = True
    title.font.color.rgb = RGBColor(0, 0, 0)
    title.paragraph_format.space_after = Pt(10)

    for name, size, before, after in (("Heading 1", 18, 10, 7), ("Heading 2", 13, 8, 5), ("Heading 3", 10.5, 6, 3)):
        style = styles[name]
        style.font.name = "Aptos Display"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Aptos Display")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos Display")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True


def add_table(doc, headers, rows, widths=None, font_size=8.3):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.style = "Table Grid"
    header = table.rows[0]
    set_repeat_table_header(header)
    for index, (cell, label) in enumerate(zip(header.cells, headers)):
        set_cell_shading(cell, NAVY)
        set_cell_border(cell)
        set_cell_margins(cell, 90, 100, 90, 100)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(0)
        style_run(p.add_run(label), size=font_size, bold=True, color=WHITE)
        if widths:
            cell.width = Inches(widths[index])
    for row_index, values in enumerate(rows):
        row = table.add_row()
        prevent_row_split(row)
        for index, (cell, value) in enumerate(zip(row.cells, values)):
            if row_index % 2 == 1:
                set_cell_shading(cell, PALE)
            set_cell_border(cell)
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            style_run(p.add_run(str(value)), size=font_size, color=INK)
            if widths:
                cell.width = Inches(widths[index])
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def add_labelled_paragraph(doc, label, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(5)
    style_run(p.add_run(label + " "), size=9.2, bold=True, color=INK)
    style_run(p.add_run(text), size=9.2, color=INK)
    return p


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.left_indent = Inches(0.22)
        p.paragraph_format.first_line_indent = Inches(-0.12)
        p.paragraph_format.space_after = Pt(2)
        for run in p.runs:
            style_run(run, size=8.8)
        if not p.runs:
            style_run(p.add_run(item), size=8.8)
        else:
            p.runs[0].text = item


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Page ")
    style_run(run, size=8, color=MUTED)
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = "PAGE"
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char1)
    run._r.append(instr_text)
    run._r.append(fld_char2)


cases = [
    {
        "id": "SYN-001", "title": "Normotensive pregnancy negative control", "age": "24", "gp": "G1P0", "dating": "First-trimester ultrasound 10 Jan 2026 at 11w2d", "edd": "27 Jul 2026",
        "intent": "Negative control with complete evidence and no hypertensive or proteinuric trigger.", "expected": "Does not meet protocol criteria for pre-eclampsia",
        "visits": [
            ["V1", "12 Feb 2026", "15w6d", "112/68; repeat 110/66", "Negative", "No headache, visual symptoms or epigastric pain", "Baseline assessment"],
            ["V2", "26 Mar 2026", "21w6d", "116/70", "Negative", "No symptoms; no antihypertensives", "Anatomy scan normal"],
            ["V3", "7 May 2026", "27w6d", "118/72", "Trace", "No symptoms", "Routine follow-up"],
            ["V4", "18 Jun 2026", "33w6d", "122/74; repeat 120/72", "Negative", "No symptoms", "Growth appropriate"],
            ["V5", "21 Jul 2026", "39w1d", "126/78", "Negative", "Spontaneous labour", "Vaginal delivery"],
            ["V6", "18 Aug 2026", "4 weeks postpartum", "118/70", "Negative", "Clinically well", "Postpartum review"],
        ],
        "labs": [
            ["V1", "12 Feb", "12.1", "36.5", "242", "0.62", "8", "18", "16", "178", "Not done"],
            ["V3", "7 May", "11.4", "34.8", "219", "0.66", "9", "20", "17", "184", "Not done"],
            ["V4", "18 Jun", "11.2", "34.1", "205", "0.70", "10", "22", "19", "190", "0.08 g/g"],
        ],
        "imaging": "Singleton live fetus; anatomy normal; V4 EFW 2,180 g at 45th centile; normal fluid and umbilical artery Doppler.",
        "outcomes": "Vaginal delivery; estimated blood loss 280 mL. Maternal condition stable. Liveborn female, 3,210 g, Apgar 9 at 1 minute and 10 at 5 minutes; no NICU admission.",
        "narrative": "A 24-year-old G1P0 participant entered the study at 15 weeks and 6 days, dated by first-trimester ultrasound. Blood pressure remained below 140/90 mmHg across all antenatal visits, urine protein was negative or trace, and platelet count, creatinine and liver enzymes remained within the supplied reference intervals. She delivered vaginally at 39 weeks and 1 day with no recorded maternal or neonatal complication. The supplied evidence should be presented without an automated diagnosis and should end with the adjudication question.",
        "checks": ["No normal finding may be inferred from a missing field.", "Trace protein at V3 must not be converted into proteinuria.", "Postpartum data must remain separate from antenatal data."],
    },
    {
        "id": "SYN-002", "title": "Early onset presentation with severe features", "age": "27", "gp": "G2P0", "dating": "Ultrasound 24 Mar 2026 at 12w4d", "edd": "4 Oct 2026",
        "intent": "Strong EOPE positive-control pattern with severe hypertension, organ dysfunction and fetal growth restriction.", "expected": "Expected reviewer classification PE with severe features and early onset",
        "visits": [
            ["V1", "15 Apr 2026", "15w3d", "118/74", "Negative", "No symptoms", "Baseline"],
            ["V2", "27 May 2026", "21w3d", "124/78", "Negative", "No symptoms", "Routine"],
            ["V3", "8 Jul 2026", "27w3d", "138/88", "1+", "Mild headache", "Enhanced surveillance"],
            ["V4", "3 Aug 2026", "31w2d", "162/112; repeat 168/114", "UPCR 1.84 g/g", "Persistent headache; magnesium sulfate and nifedipine", "Hospital admission"],
            ["V5", "4 Aug 2026", "31w3d", "158/106", "UPCR 1.96 g/g", "Emergency caesarean", "Delivery"],
            ["V6", "1 Sep 2026", "4 weeks postpartum", "132/84", "Negative", "On oral nifedipine", "Postpartum"],
        ],
        "labs": [
            ["V1", "15 Apr", "12.4", "37.0", "221", "0.62", "8", "18", "16", "182", "Negative"],
            ["V4", "3 Aug", "10.8", "32.0", "92", "1.31", "22", "96", "78", "680", "1.84 g/g"],
            ["V5", "4 Aug", "10.4", "31.2", "84", "1.36", "24", "104", "86", "720", "1.96 g/g"],
        ],
        "imaging": "Ultrasound at 31w2d: EFW 1,210 g at 6th centile; absent end-diastolic flow; reduced amniotic fluid. Source report date 3 Aug 2026.",
        "outcomes": "Emergency caesarean at 31w3d. Estimated blood loss 620 mL. Liveborn female, 1,200 g, Apgar 7 and 9; NICU admission for prematurity.",
        "narrative": "A 27-year-old G2P0 participant with first-trimester ultrasound dating had normal blood pressure and negative urine protein at baseline. At 31 weeks and 2 days she had blood pressures of 162/112 and 168/114 mmHg, UPCR 1.84 g/g, platelets 92 x10^3/uL, creatinine 1.31 mg/dL, AST 96 U/L and ALT 78 U/L. Ultrasound on the same date recorded EFW at the 6th centile with absent end-diastolic flow. Treatment and delivery facts should be stated, while the final diagnosis remains for the adjudicator.",
        "checks": ["V1 must not be described as hypertensive or proteinuric.", "Every abnormal laboratory value must retain date, unit and reference interval.", "The narrative must not conclude that diagnostic criteria are fulfilled."],
    },
    {
        "id": "SYN-003", "title": "Late onset hypertensive presentation", "age": "33", "gp": "G3P2", "dating": "Ultrasound 6 Jan 2026 at 9w1d", "edd": "8 Aug 2026",
        "intent": "LOPE positive-control pattern beginning after 34 weeks without laboratory severe features.", "expected": "Expected reviewer classification PE without severe features and late onset",
        "visits": [
            ["V1", "3 Mar 2026", "17w3d", "114/72", "Negative", "No symptoms", "Baseline"],
            ["V2", "14 Apr 2026", "23w3d", "120/74", "Negative", "No symptoms", "Routine"],
            ["V3", "26 May 2026", "29w3d", "126/78", "Trace", "No symptoms", "Routine"],
            ["V4", "21 Jul 2026", "37w3d", "148/94; repeat 146/92", "UPCR 0.46 g/g", "Pedal edema; no headache or visual symptoms", "Admitted for assessment"],
            ["V5", "23 Jul 2026", "37w5d", "142/90", "1+", "Induction of labour", "Delivery"],
            ["V6", "20 Aug 2026", "4 weeks postpartum", "124/78", "Negative", "No medication", "Recovered"],
        ],
        "labs": [
            ["V1", "3 Mar", "12.6", "37.8", "258", "0.58", "7", "17", "15", "170", "Negative"],
            ["V4", "21 Jul", "11.8", "35.5", "176", "0.76", "12", "28", "25", "210", "0.46 g/g"],
            ["V5", "23 Jul", "11.6", "35.0", "169", "0.79", "13", "30", "27", "224", "1+"],
        ],
        "imaging": "Growth scan at 36w6d: EFW 2,780 g at 38th centile; normal fluid and Doppler.",
        "outcomes": "Induced vaginal delivery at 37w5d; blood loss 350 mL. Liveborn male, 2,820 g, Apgar 8 and 9; no NICU admission.",
        "narrative": "A 33-year-old G3P2 participant remained normotensive through 29 weeks and 3 days. At 37 weeks and 3 days, blood pressure was 148/94 mmHg and 146/92 mmHg on repeat, with UPCR 0.46 g/g. Platelet count, creatinine and liver enzymes did not cross the supplied alert thresholds. Delivery and postpartum recovery should be described separately from the adjudication decision.",
        "checks": ["Onset must be dated to V4 rather than inferred at V1.", "EOPE or LOPE must use the approved protocol threshold.", "Pedal edema may be reported but must not be treated as a diagnostic criterion by the narrative."],
    },
    {
        "id": "SYN-004", "title": "Chronic hypertension without superimposed disease", "age": "38", "gp": "G4P3", "dating": "Ultrasound 12 Feb 2026 at 10w0d", "edd": "10 Sep 2026",
        "intent": "Negative PE control with pre-existing chronic hypertension and stable laboratory findings.", "expected": "Expected reviewer classification chronic hypertension with superimposed PE excluded",
        "visits": [
            ["V1", "26 Mar 2026", "16w0d", "146/92; repeat 142/90", "Negative", "Known chronic hypertension; labetalol", "Baseline"],
            ["V2", "7 May 2026", "22w0d", "138/86", "Negative", "No symptoms; labetalol", "Routine"],
            ["V3", "18 Jun 2026", "28w0d", "140/88", "Trace", "No symptoms", "Surveillance"],
            ["V4", "30 Jul 2026", "34w0d", "144/90; repeat 138/86", "Negative", "No symptoms", "Stable"],
            ["V5", "3 Sep 2026", "39w0d", "142/88", "Negative", "Planned caesarean", "Delivery"],
            ["V6", "1 Oct 2026", "4 weeks postpartum", "136/84", "Negative", "Continued labetalol", "Postpartum"],
        ],
        "labs": [
            ["V1", "26 Mar", "12.0", "36.1", "230", "0.72", "10", "19", "18", "190", "Negative"],
            ["V3", "18 Jun", "11.5", "34.6", "214", "0.74", "11", "21", "20", "196", "Trace"],
            ["V4", "30 Jul", "11.3", "34.0", "208", "0.75", "12", "23", "21", "204", "0.09 g/g"],
        ],
        "imaging": "Serial growth remained between the 42nd and 48th centiles with normal Doppler studies.",
        "outcomes": "Planned repeat caesarean at 39w0d; maternal outcome stable. Liveborn female, 3,340 g, Apgar 9 and 9.",
        "narrative": "A 38-year-old G4P3 participant had chronic hypertension documented before 20 weeks and was treated with labetalol. Blood pressure remained in a similar range through pregnancy, urine protein was negative or trace, and platelet count, creatinine and transaminases remained stable. The narrative should identify chronic hypertension as source-recorded history without deciding whether superimposed pre-eclampsia is present.",
        "checks": ["Do not interpret baseline hypertension as new-onset disease.", "Medication names must be displayed, not an 'available' flag.", "The absence of worsening evidence must be based on dated observations."],
    },
    {
        "id": "SYN-005", "title": "Chronic hypertension with suspected superimposed disease", "age": "35", "gp": "G2P1", "dating": "Ultrasound 2 Feb 2026 at 11w5d", "edd": "19 Aug 2026",
        "intent": "Positive pattern requiring separation of chronic hypertension from new proteinuria and organ dysfunction.", "expected": "Expected reviewer classification superimposed PE with severe features",
        "visits": [
            ["V1", "16 Mar 2026", "17w5d", "150/94; repeat 146/92", "Negative", "Chronic hypertension; nifedipine", "Baseline"],
            ["V2", "27 Apr 2026", "23w5d", "142/88", "Negative", "No symptoms", "Stable"],
            ["V3", "8 Jun 2026", "29w5d", "148/92", "Trace", "No symptoms", "Surveillance"],
            ["V4", "13 Jul 2026", "34w5d", "170/116; repeat 166/112", "UPCR 0.92 g/g", "Headache and visual disturbance; magnesium sulfate", "Hospital admission"],
            ["V5", "14 Jul 2026", "34w6d", "160/108", "2+", "Emergency caesarean", "Delivery"],
            ["V6", "11 Aug 2026", "4 weeks postpartum", "146/90", "Trace", "On nifedipine", "Follow-up"],
        ],
        "labs": [
            ["V1", "16 Mar", "12.3", "36.8", "224", "0.74", "10", "20", "18", "184", "Negative"],
            ["V4", "13 Jul", "11.0", "33.1", "118", "1.12", "19", "72", "64", "510", "0.92 g/g"],
            ["V5", "14 Jul", "10.7", "32.2", "104", "1.18", "21", "78", "70", "560", "2+"],
        ],
        "imaging": "V4 ultrasound: EFW 2,080 g at 12th centile; elevated umbilical artery resistance but forward end-diastolic flow.",
        "outcomes": "Emergency caesarean at 34w6d; blood loss 700 mL, no transfusion. Liveborn male, 2,050 g, Apgar 7 and 9; NICU admission.",
        "narrative": "A 35-year-old G2P1 participant entered pregnancy with treated chronic hypertension and negative baseline urine protein. At 34 weeks and 5 days she developed blood pressure of 170/116 mmHg with a severe-range repeat, UPCR 0.92 g/g, thrombocytopenia, increased creatinine and elevated transaminases. The chronology must show that these were new findings relative to baseline and must leave the final classification to the reviewer.",
        "checks": ["Baseline and new findings must be explicitly compared.", "Do not label the condition automatically as superimposed PE.", "Keep laboratory results separate from the reviewer interpretation."],
    },
    {
        "id": "SYN-006", "title": "Isolated gestational proteinuria", "age": "29", "gp": "G2P1", "dating": "Ultrasound 18 Dec 2025 at 12w0d", "edd": "2 Jul 2026",
        "intent": "Negative hypertensive control with persistent proteinuria and normal blood pressure.", "expected": "Expected reviewer classification transient gestational proteinuria or alternative diagnosis",
        "visits": [
            ["V1", "29 Jan 2026", "18w0d", "108/66", "Negative", "No symptoms", "Baseline"],
            ["V2", "12 Mar 2026", "24w0d", "112/68", "1+", "Dysuria", "Urine culture requested"],
            ["V3", "23 Apr 2026", "30w0d", "116/70", "UPCR 0.42 g/g", "No PE symptoms", "Proteinuria persists"],
            ["V4", "4 Jun 2026", "36w0d", "118/72", "1+", "No symptoms", "Stable"],
            ["V5", "30 Jun 2026", "39w5d", "120/74", "Trace", "Spontaneous labour", "Delivery"],
            ["V6", "28 Jul 2026", "4 weeks postpartum", "114/68", "Negative", "Well", "Protein resolved"],
        ],
        "labs": [
            ["V1", "29 Jan", "12.8", "38.4", "268", "0.60", "8", "16", "14", "172", "Negative"],
            ["V3", "23 Apr", "12.0", "36.0", "244", "0.64", "9", "18", "16", "180", "0.42 g/g"],
            ["V4", "4 Jun", "11.7", "35.2", "230", "0.66", "10", "19", "17", "188", "1+"],
        ],
        "imaging": "Normal fetal growth and Doppler studies. V4 EFW 2,650 g at 44th centile.",
        "outcomes": "Vaginal delivery at 39w5d; blood loss 300 mL. Liveborn female, 3,180 g, Apgar 9 and 9.",
        "narrative": "A 29-year-old G2P1 participant developed urine protein of 1+ and later UPCR 0.42 g/g while all recorded antenatal blood pressures remained below 140/90 mmHg. Platelet count, creatinine and liver enzymes remained within the supplied reference intervals, and urine protein was negative postpartum. The presentation must not be converted into pre-eclampsia solely because proteinuria was recorded.",
        "checks": ["Proteinuria must be shown as its actual grade or ratio.", "Normal-range claims require the displayed laboratory reference intervals.", "The narrative must not imply hypertension where none was recorded."],
    },
    {
        "id": "SYN-007", "title": "Incomplete evidence unable to determine", "age": "31", "gp": "G3P1", "dating": "EDD recorded as 30 Sep 2026; dating scan report unavailable", "edd": "30 Sep 2026 unverified",
        "intent": "Missing-data case designed to test explicit unavailable wording and certainty restrictions.", "expected": "Expected reviewer response unable to determine pending source clarification",
        "visits": [
            ["V1", "6 May 2026", "Gestational age unavailable", "138/88", "Not done", "Headache status unavailable", "Partial baseline"],
            ["V2", "17 Jun 2026", "Gestational age unavailable", "Not recorded", "1+", "Medication record unavailable", "Sparse visit"],
            ["V3", "29 Jul 2026", "Gestational age unavailable", "164/108", "2+", "Repeat BP unavailable; visual symptoms unavailable", "Trigger visit"],
            ["V4", "Not performed", "Unavailable", "Unavailable", "Unavailable", "Missed visit", "No measurements"],
            ["V5", "Delivery date unavailable", "Unavailable", "Unavailable", "Unavailable", "Hospital record not supplied", "Outcome unavailable"],
            ["V6", "Not supplied", "Postpartum", "Unavailable", "Unavailable", "Unavailable", "No follow-up record"],
        ],
        "labs": [
            ["V1", "6 May", "11.6", "34.9", "Not done", "Not done", "Not done", "Not done", "Not done", "Not done", "Not done"],
            ["V3", "29 Jul", "Not done", "Not done", "88", "Unavailable", "Unavailable", "Unavailable", "Unavailable", "Unavailable", "2+"],
            ["V5", "Unavailable", "Unavailable", "Unavailable", "Unavailable", "Unavailable", "Unavailable", "Unavailable", "Unavailable", "Unavailable", "Unavailable"],
        ],
        "imaging": "Source field unavailable; fetal growth, fluid, Doppler and dating method cannot be determined from the supplied record.",
        "outcomes": "Source field unavailable; delivery mode and maternal and neonatal outcomes cannot be determined from the supplied record.",
        "narrative": "A 31-year-old G3P1 participant had an incomplete source record. A single blood pressure of 164/108 mmHg and urine protein 2+ were recorded at V3, but repeat blood pressure, dating evidence, renal and liver results, delivery records and postpartum follow-up were unavailable. Each missing element must use explicit unavailable wording, and the interface must prevent a definite certainty classification.",
        "checks": ["Never convert unavailable values into normal or negative findings.", "Do not calculate GA from an unverified EDD.", "The case must carry an unresolved-questions section and restricted certainty."],
    },
    {
        "id": "SYN-008", "title": "Source conflict and chronology challenge", "age": "30", "gp": "G2P0", "dating": "EDC EDD 12 Jun 2026; eSource EDD 26 Jun 2026", "edd": "Conflicting source EDDs",
        "intent": "Mapping stress case containing age, dating, GA, vital-sign and coded-value conflicts.", "expected": "No automatic classification until discrepancies are resolved",
        "visits": [
            ["V1", "16 Feb 2026", "EDC 23w3d; derived 23w3d", "112/64", "Negative", "EDC age 30; eSource age 29", "Baseline conflict"],
            ["V2", "Date unavailable", "Unavailable", "116/63", "1+", "Visit date missing", "Monitor warning"],
            ["V3", "3 Mar 2026", "25w4d", "142/87; repeat 140/85", "2+", "FHR source code 1 means Yes, not 1 bpm", "Mapping test"],
            ["V4", "17 Mar 2026", "Source GA missing", "115/73; additional SBP 112", "1+", "No matching DBP for second SBP", "Chronology test"],
            ["V5", "21 May 2026", "Source 37w0d; EDD-derived 36w6d", "128/80", "Negative", "Delivery record", "One-day tolerance"],
            ["V6", "19 Jun 2026", "Postpartum", "150/90; repeat 144/88", "Negative", "Antenatal ultrasound must not appear here", "Postpartum"],
        ],
        "labs": [
            ["V1", "16 Feb", "12.2", "36.6", "236", "0.68", "9", "18", "17", "176", "Negative"],
            ["V3", "3 Mar", "11.8", "35.3", "210", "0.70", "10", "24", "22", "190", "2+"],
            ["V4", "17 Mar", "11.7", "35.0", "204", "0.71", "10", "25", "23", "194", "1+"],
        ],
        "imaging": "V3 ultrasound status says performed; numerical EFW and presentation description are missing. FHR is a coded availability response and must not be rendered as a measurement.",
        "outcomes": "Vaginal delivery recorded. Maternal blood loss unavailable. Liveborn female, 2,560 g, Apgar 9, 9 and 9. Postpartum BP remains elevated.",
        "narrative": "This case must present unresolved source conflicts rather than silently choosing values. V3 records 25 weeks and 4 days on 3 March. V4 has no source GA; calculation is prohibited while the EDD conflict remains unresolved. The source age disagreement, unmatched systolic measurement, missing ultrasound results and coded fetal-heart-rate response must appear in the discrepancy section.",
        "checks": ["Do not copy V1 GA into V4.", "Conflicting EDDs must block deterministic GA calculation.", "Do not render coded response 1 as 1 bpm.", "Age conflict must be visible and the selected value must retain provenance."],
    },
    {
        "id": "SYN-009", "title": "Postpartum hypertensive presentation", "age": "26", "gp": "G1P1", "dating": "Ultrasound 20 Nov 2025 at 10w6d", "edd": "11 Jun 2026",
        "intent": "Postpartum-only presentation testing temporal isolation of antenatal and postpartum evidence.", "expected": "Expected reviewer classification postpartum pre-eclampsia if charter permits",
        "visits": [
            ["V1", "8 Jan 2026", "17w0d", "110/68", "Negative", "No symptoms", "Baseline"],
            ["V2", "19 Feb 2026", "23w0d", "114/70", "Negative", "No symptoms", "Routine"],
            ["V3", "2 Apr 2026", "29w0d", "118/72", "Trace", "No symptoms", "Routine"],
            ["V4", "14 May 2026", "35w0d", "120/74", "Negative", "No symptoms", "Normal growth"],
            ["V5", "9 Jun 2026", "39w5d", "124/76", "Negative", "Vaginal delivery", "Uncomplicated delivery"],
            ["V6", "13 Jun 2026", "Postpartum day 4", "168/110; repeat 164/108", "UPCR 0.72 g/g", "Severe headache and visual disturbance; magnesium sulfate", "Readmission"],
        ],
        "labs": [
            ["V4", "14 May", "11.7", "35.1", "198", "0.69", "10", "21", "19", "186", "Negative"],
            ["V5", "9 Jun", "11.5", "34.6", "190", "0.72", "11", "23", "21", "192", "Negative"],
            ["V6", "13 Jun", "10.9", "32.8", "126", "1.08", "18", "68", "60", "480", "0.72 g/g"],
        ],
        "imaging": "Antenatal V4 ultrasound was normal for growth and Doppler. It must remain dated to 14 May and must not be displayed as a postpartum assessment.",
        "outcomes": "Vaginal delivery at 39w5d; blood loss 320 mL. Liveborn male, 3,260 g, Apgar 9 and 9. Maternal readmission on postpartum day 4.",
        "narrative": "A 26-year-old G1P1 participant was normotensive with negative or trace urine protein throughout pregnancy and at delivery. On postpartum day 4 she was readmitted with severe headache, visual disturbance, blood pressure 168/110 mmHg with severe-range repeat, UPCR 0.72 g/g, thrombocytopenia, increased creatinine and elevated transaminases. Antenatal imaging must be clearly labelled with its original date.",
        "checks": ["Postpartum GA must never appear as antenatal weeks.", "The V4 ultrasound must not be moved into V6.", "The narrative should state the postpartum timing without automatically adjudicating the diagnosis."],
    },
    {
        "id": "SYN-010", "title": "HELLP pattern with eclamptic seizure", "age": "22", "gp": "G1P0", "dating": "Ultrasound 14 Jan 2026 at 8w2d", "edd": "24 Aug 2026",
        "intent": "High-severity positive control testing emergency chronology, HELLP-related laboratory presentation and neonatal outcomes.", "expected": "Expected reviewer classification severe PE with HELLP pattern and eclampsia",
        "visits": [
            ["V1", "9 Mar 2026", "16w0d", "108/64", "Negative", "No symptoms", "Baseline"],
            ["V2", "20 Apr 2026", "22w0d", "116/70", "Negative", "No symptoms", "Routine"],
            ["V3", "1 Jun 2026", "28w0d", "134/84", "1+", "Intermittent headache", "Surveillance"],
            ["V4", "29 Jun 2026", "32w0d", "176/118; repeat 172/116", "3+; UPCR 2.40 g/g", "RUQ pain, visual symptoms, seizure; magnesium sulfate", "Emergency admission"],
            ["V5", "29 Jun 2026", "32w0d", "168/112", "3+", "Emergency caesarean", "Delivery same day"],
            ["V6", "27 Jul 2026", "4 weeks postpartum", "138/86", "Trace", "Recovering; on nifedipine", "Follow-up"],
        ],
        "labs": [
            ["V1", "9 Mar", "12.5", "37.4", "246", "0.60", "8", "17", "15", "174", "Negative"],
            ["V4", "29 Jun", "9.8", "29.4", "58", "1.42", "26", "220", "184", "1,180", "2.40 g/g"],
            ["V5", "29 Jun", "9.4", "28.1", "52", "1.48", "28", "238", "196", "1,260", "3+"],
        ],
        "imaging": "Emergency ultrasound: EFW 1,520 g at 8th centile; reversed end-diastolic flow; reduced fluid.",
        "outcomes": "Emergency caesarean at 32w0d; blood loss 850 mL and one unit red-cell transfusion. Liveborn male, 1,480 g, Apgar 5 and 8; NICU admission for prematurity and respiratory support.",
        "narrative": "A 22-year-old G1P0 participant had normal baseline observations. At 32 weeks she presented with severe-range hypertension, 3+ urine protein and UPCR 2.40 g/g, right upper quadrant pain, visual symptoms and a source-recorded seizure. Platelets were 58 x10^3/uL, AST 220 U/L, ALT 184 U/L and LDH 1,180 U/L. Emergency imaging, treatment, delivery, maternal blood loss, transfusion and neonatal course must be presented chronologically without replacing adjudicator judgment.",
        "checks": ["The seizure must be tied to its dated source record.", "HELLP-related values must be shown as observed results with units and ranges.", "Maternal and neonatal outcomes must remain separate sections."],
    },
]


doc = Document()
section = doc.sections[0]
section.orientation = WD_ORIENT.LANDSCAPE
section.page_width, section.page_height = section.page_height, section.page_width
section.top_margin = Inches(0.55)
section.bottom_margin = Inches(0.55)
section.left_margin = Inches(0.6)
section.right_margin = Inches(0.6)
configure_styles(doc)

footer = section.footer
footer_table = footer.add_table(rows=1, cols=2, width=Inches(10.4))
footer_table.columns[0].width = Inches(8.7)
footer_table.columns[1].width = Inches(1.7)
p = footer_table.cell(0, 0).paragraphs[0]
style_run(p.add_run("ACRN Synthetic Adjudication Source Case Template  |  UAT evidence pack"), size=8, color=MUTED)
add_page_number(footer_table.cell(0, 1).paragraphs[0])

title = doc.add_paragraph(style="Title")
title.add_run("Synthetic Adjudication Source Case Template")
subtitle = doc.add_paragraph()
subtitle.paragraph_format.space_after = Pt(14)
style_run(subtitle.add_run("Ten participant cases for mapping narrative and chronology validation"), size=14, color=MUTED)

intro = doc.add_paragraph()
intro.paragraph_format.space_after = Pt(8)
style_run(intro.add_run(
    "This editable case pack provides a controlled source template for testing the Monitor mapping layer and the Adjudicator clinical presentation. "
    "It is designed for joint review by Tariro, Panashe, the medical monitor and the implementation team before implementation clearance. "
    "All participant identifiers and clinical values are synthetic."
), size=10.2)

add_table(doc, ["Document field", "Controlled value"], [
    ["Document owner", "ACRN Adjudication Programme"],
    ["Purpose", "UAT source mapping, chronology, missingness and FDA submission-style narrative review"],
    ["Data status", "Synthetic test data only; not for clinical care"],
    ["Case count", "10 participants covering positive, negative, severe, conflicting and missing-data scenarios"],
    ["Mapping baseline", "RT-MAP-3.2 or successor approved mapping version"],
    ["Approval state", "Draft for clinical and UAT redline"],
], widths=[2.0, 8.3], font_size=9)

doc.add_heading("How reviewers should use this template", level=1)
add_bullets(doc, [
    "Confirm that every displayed value can be traced to a dated source field and source page.",
    "Redline the expected presentation narrative for clinical accuracy, completeness and neutral wording.",
    "Confirm the approved dating hierarchy, protocol or charter version, EOPE threshold and laboratory reference intervals.",
    "Record expected versus actual output for every case and link the signed evidence into the existing UAT record.",
    "Do not treat an import, mapping success or screenshot as clinical approval.",
])

doc.add_heading("Controlled source mapping", level=1)
mapping_rows = [
    ["Participant age", "Demographics / Age", "age", "years", "Source value must agree with canonical age; conflicts remain visible"],
    ["Gravidity and parity", "Obstetric History / Previous pregnancies and live births", "gravida; para_live", "count", "Derive G and P only from approved source fields"],
    ["Visit date", "Visit Date / Date of visit", "visit_date", "date time", "Bind every observation to the actual assessment date"],
    ["Gestational age", "Pregnancy Assessment / Current gestational age", "ega_weeks; ega_days", "weeks days", "Use visit source GA or deterministic approved EDD calculation; never copy another visit"],
    ["Dating anchor", "Sonographic Data / First scan date and GA; EDD", "dating_anchor_date; dating_anchor_ga; edd", "date weeks days", "Conflicting dating anchors block automatic calculation"],
    ["Blood pressure", "Vital Signs / Systolic and diastolic BP", "bp_systolic; bp_diastolic; rechecks", "mmHg", "Pair readings by source occurrence and timestamp"],
    ["Proteinuria", "Assessment of Proteinuria / Dipstick or UPCR", "ua_protein; upcr", "grade or g/g", "Show actual 1+, 2+, 3+, ratio or not done"],
    ["Full blood count", "Hematology", "haemoglobin; haematocrit; platelets; wbc", "source units", "Show value, unit, range and date"],
    ["Renal panel", "Biochemistry", "creatinine; bun", "mg/dL or source unit", "Do not transform without recorded conversion and version"],
    ["Liver and haemolysis", "Biochemistry", "ast; alt; ldh; bilirubin", "U/L or source unit", "Observed value remains separate from interpretation"],
    ["Symptoms", "Clinical Assessment", "headache; visual_disturbance; epigastric_pain", "coded response plus description", "Decode Yes or No; never display only available"],
    ["Medication", "Concomitant Medication", "medication name; dose; route; start date", "source units", "Display actual medication details"],
    ["Ultrasound", "Sonographic Data", "efw; fetal_presentation; fetal_heart_rate; afi; Doppler", "g bpm cm categorical", "Coded availability values cannot become measurements"],
    ["Delivery", "Delivery Outcome", "delivery_date; delivery_mode; ebl_ml; complication", "date categorical mL", "Keep delivery mode separate from maternal outcome"],
    ["Neonatal outcome", "Newborn Assessment", "sex; weight; Apgar; NICU; complications", "categorical g score", "Keep neonatal facts in a separate section"],
]
add_table(doc, ["Narrative element", "Source location", "Canonical field", "Unit or type", "Mapping rule"], mapping_rows, widths=[1.4, 2.2, 2.0, 1.2, 3.5], font_size=7.7)

doc.add_heading("Case coverage index", level=1)
index_rows = [[c["id"], c["title"], c["intent"], c["expected"]] for c in cases]
add_table(doc, ["Case", "Presentation", "Validation purpose", "Expected reviewer outcome"], index_rows, widths=[0.8, 2.3, 4.2, 3.0], font_size=8.1)

doc.add_heading("Laboratory display conventions", level=1)
add_labelled_paragraph(doc, "Reference intervals", "Use the approved study and laboratory-specific ranges. For this synthetic pack, the working adult pregnancy ranges are: haemoglobin 11.0 to 15.0 g/dL; haematocrit 33 to 45 percent; platelets 150 to 400 x10^3/uL; creatinine 0.50 to 0.90 mg/dL; BUN 6 to 20 mg/dL; AST 0 to 40 U/L; ALT 0 to 40 U/L; and LDH 120 to 250 U/L. These ranges require clinical confirmation before UAT sign-off.")
add_labelled_paragraph(doc, "Missing data", "Use the wording Source field unavailable; this finding cannot be determined from the supplied record. Do not translate missing values into normal, negative or zero.")
add_labelled_paragraph(doc, "Narrative boundary", "The expected narrative presents dated observations, missingness and discrepancies. It does not make the final adjudication.")

for case in cases:
    doc.add_page_break()
    doc.add_heading(f"{case['id']}  {case['title']}", level=1)
    add_table(doc, ["Age", "Obstetric history", "Approved dating source", "Expected delivery date", "Test classification"], [[case["age"], case["gp"], case["dating"], case["edd"], case["expected"]]], widths=[0.6, 1.2, 3.6, 1.6, 3.4], font_size=8.3)
    add_labelled_paragraph(doc, "Validation intent", case["intent"])

    doc.add_heading("Source chronology", level=2)
    add_table(doc, ["Visit", "Assessment date", "Gestational age", "Blood pressure", "Proteinuria", "Symptoms and medication", "Presentation or event"], case["visits"], widths=[0.55, 1.15, 1.25, 1.55, 1.15, 2.75, 2.15], font_size=7.6)

    doc.add_heading("Laboratory source results", level=2)
    add_table(doc, ["Visit", "Date", "Hb g/dL", "Hct percent", "Platelets x10^3/uL", "Creatinine mg/dL", "BUN mg/dL", "AST U/L", "ALT U/L", "LDH U/L", "Protein"], case["labs"], widths=[0.55, 0.75, 0.75, 0.75, 1.2, 1.15, 0.8, 0.7, 0.7, 0.75, 0.9], font_size=7.2)

    doc.add_heading("Imaging delivery and outcomes", level=2)
    add_table(doc, ["Section", "Source-supported content"], [["Ultrasound and fetal assessment", case["imaging"]], ["Delivery maternal and neonatal outcomes", case["outcomes"]]], widths=[2.2, 8.1], font_size=8.4)

    doc.add_heading("Expected FDA submission style presentation", level=2)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.12
    style_run(p.add_run(case["narrative"]), size=9.2)

    doc.add_heading("Case acceptance checks", level=2)
    add_bullets(doc, case["checks"])

doc.add_page_break()
doc.add_heading("UAT result recording template", level=1)
add_labelled_paragraph(doc, "Instructions", "Complete one row per case after the application rerun. Attach the full generated output, mapping trace and screenshots only as supporting evidence. Clinical approval must be recorded separately.")
uat_rows = [[c["id"], "Not run", "", "", "", ""] for c in cases]
add_table(doc, ["Case", "Run status", "Mapping result", "Narrative result", "Open defects", "Reviewer and date"], uat_rows, widths=[0.8, 1.1, 2.5, 2.5, 2.1, 1.4], font_size=8.2)

doc.add_heading("Required evidence pack", level=1)
add_bullets(doc, [
    "This editable template and the approved version record.",
    "Field-to-source mapping export with codelists, units and transformation rules.",
    "Complete generated output for all ten cases, not cropped screenshots.",
    "Expected-versus-actual test record and point-by-point defect response.",
    "Exact protocol and adjudication-charter criteria with version identifiers.",
    "Recorded clinical review and sign-off linked into the existing UAT record with Panashe.",
    "Clear separation between demonstration evidence and production validation evidence.",
])

doc.core_properties.title = "Synthetic Adjudication Source Case Template"
doc.core_properties.subject = "Ten synthetic cases for mapping narrative chronology and UAT review"
doc.core_properties.author = "ACRN Adjudication Programme"
doc.core_properties.keywords = "adjudication, synthetic cases, source mapping, UAT, clinical narrative"
doc.save(OUT)
print(OUT)
