// Fresh Presentation Dataset — Empty initial queue for live presentation / fresh CSV upload
export const MOCK_CASES = [];

// Real PDF Lab Report extracted dataset (ZWE0010240 V03)
export const ZWE0010240_PDF_CASE = {
  id: "ZWE0010240 V03",
  caseNo: "ADJ-0240",
  site: "Mutala Trust Clinic (ZWE001)",
  status: "Pending Review",
  trigger: "LIMS Lab PDF Uploaded (Jun 03, 2026)",
  pktScore: 1.0,
  qcStatus: "FORM-ADJ-01 QC Passed (Blinding Verified)",
  gaAtEnrollment: "14+0",
  gaAtEvent: "32+1",
  edd: "2026-10-18",
  lnmp: "2025-12-30",
  firstUssDate: "2026-03-30",
  firstUssGa: "14+0",

  biomarkers: {
    sFlt1: "BLINDED — Withheld Until Database Lock (SOP-ADJ-002)",
    plgf: "BLINDED — Withheld Until Database Lock (SOP-ADJ-002)",
    ratio: "BLINDED — Withheld Until Database Lock (SOP-ADJ-002)",
    pocResult: "BLINDED (SOP-ADJ-002)"
  },

  bpLog: [
    { date: "2026-06-02 17:05", ga: "32+0", sbp: 138, dbp: 86, severe: false, source: "Mutala Clinic Vitals" },
    { date: "2026-06-03 09:15", ga: "32+1", sbp: 144, dbp: 92, severe: false, source: "Mutala Clinic Vitals (Repeat)" }
  ],

  proteinuriaLog: [
    { date: "2026-06-03", method: "Urine Chemistry Dipstick", result: "Trace (0.5+)", severe: false, source: "LIMS Report #ZWE0010240" }
  ],

  labLog: [
    { analyte: "Platelet Count", result: "169", unit: "10^3/µL", refRange: "150 - 400", severe: false, source: "LIMS Report #ZWE0010240" },
    { analyte: "Creatinine", result: "65.82", unit: "µmol/L (0.74 mg/dL)", refRange: "48 - 131", severe: false, source: "LIMS Report #ZWE0010240 (Rule G-13 Converted)" },
    { analyte: "AST", result: "17.56", unit: "U/L", refRange: "10 - 30", severe: false, source: "LIMS Report #ZWE0010240" },
    { analyte: "ALT", result: "5.82", unit: "U/L", refRange: "5 - 44", severe: false, source: "LIMS Report #ZWE0010240" },
    { analyte: "LDH", result: "178.22", unit: "U/L", refRange: "180 - 325", severe: false, source: "LIMS Report #ZWE0010240" },
    { analyte: "Hemoglobin", result: "12.12", unit: "g/dL", refRange: "11.5 - 16.5", severe: false, source: "LIMS Report #ZWE0010240" }
  ],

  criteria: [
    { id: "HTN-01", title: "Hypertension (≥140/90 mmHg, 4h apart)", met: true, details: "Confirmed: 144/92 mmHg @ 03-Jun 09:15" },
    { id: "HTN-02", title: "Severe-range BP (≥160/110 mmHg)", met: false, details: "Max BP 144/92 (Mild/Moderate HTN)" },
    { id: "PROT-01", title: "Proteinuria (UPCR ≥ 0.3 or 2+ dipstick)", met: false, details: "Proteins: Trace (below 2+ threshold)" },
    { id: "HAEM-01", title: "Thrombocytopenia (Platelets < 100 x10³/µL)", met: false, details: "Platelets 169 x10³/µL (Normal)" },
    { id: "RENAL-01", title: "Renal Impairment (Creatinine > 1.1 mg/dL)", met: false, details: "Creatinine 65.82 µmol/L = 0.74 mg/dL (Normal)" }
  ],

  derivedSubtype: "Gestational HTN",
  derivedSeverity: "WITHOUT_SEVERE_FEATURES",
  derivedOnset: "2026-06-03 (GA 32+1)",

  narrativeForm: "FORM-ADJ-15B",
  aiNarrative: "SECTION 1: CLINICAL HISTORY & DATING ANCHOR\nParticipant ZWE0010240 V03 is a 31-year-old female at 32+1 weeks gestation presenting at Mutala Trust Clinic. Dating anchor established by ultrasound (EDD 18-Oct-2026).\n\nSECTION 2: BLOOD PRESSURE & PROTEINURIA TIMELINE\nDocumented mild hypertension (144/92 mmHg). Urine chemistry demonstrated Trace proteinuria.\n\nSECTION 3: LABORATORY ANALYTICS & ORGAN DYSFUNCTION\nLaboratory investigations from LIMS PDF (03-Jun-2026) confirmed normal platelet count (169 x10³/µL), normal serum creatinine (65.82 µmol/L / 0.74 mg/dL), normal AST (17.56 U/L), and normal ALT (5.82 U/L).\n\nSECTION 4: FETAL GROWTH & UTEROPLACENTAL DOPPLER\nUltrasound scan demonstrates normal fetal growth parameters and reassuring Doppler indices.\n\nSECTION 5: DELIVERY DETAILS & NEONATAL OUTCOMES\nClassified as Gestational Hypertension without severe features. Patient monitored on routine outpatient protocol.",

  sourceDocs: {
    ultrasound: "Fetal Scan (03-Jun-2026): Normal EFW for GA 32+1. Reassuring Umbilical Artery Doppler.",
    lims: "Extracted from LIMS PDF 'ZWE0010240 V03-Female31 years-485.pdf' (03-Jun-2026): Platelets 169, Creatinine 65.82 µmol/L, AST 17.56, ALT 5.82, Urine Proteins Trace.",
    delivery: "Pending — Ongoing pregnancy.",
    vitals: "Mutala Clinic Vitals: 02-Jun 17:05 138/86; 03-Jun 09:15 144/92 mmHg."
  }
};

// Partial Evidence Case — Demonstrates DV-26 Score (60%) & DV-27 Certainty Gate Lock
export const PARTIAL_DATA_DEMO_CASE = {
  id: "NGA002-0044",
  caseNo: "ADJ-0088",
  site: "Ibadan University College Hospital (NGA002)",
  status: "Incomplete Evidence (DV-26)",
  trigger: "DV-30 (BP 164/108 mmHg — Single Reading)",
  pktScore: 0.6,
  qcStatus: "FORM-ADJ-01 QC Passed (Partial Package)",
  gaAtEnrollment: null,
  gaAtEvent: "33+0",
  edd: null,
  lnmp: null,
  firstUssDate: null,
  firstUssGa: null,

  biomarkers: {
    sFlt1: "BLINDED — Withheld Until Database Lock (SOP-ADJ-002)",
    plgf: "BLINDED — Withheld Until Database Lock (SOP-ADJ-002)",
    ratio: "BLINDED — Withheld Until Database Lock (SOP-ADJ-002)",
    pocResult: "BLINDED (SOP-ADJ-002)"
  },

  bpLog: [
    { date: "2026-07-28 10:15", ga: "33+0", sbp: 164, dbp: 108, severe: true, source: "eSource Vitals (Single Reading)" }
  ],

  proteinuriaLog: [
    { date: "2026-07-28", method: "Dipstick", result: "2+", severe: true, source: "EDC Entry" }
  ],

  labLog: [
    { analyte: "Platelet Count", result: "88", unit: "10^3/µL", refRange: "150 - 450", severe: true, source: "LIMS Export" }
  ],

  criteria: [
    { id: "HTN-01", title: "Hypertension (≥140/90 mmHg)", met: false, details: "Only 1 BP reading documented (164/108) — Repeat reading missing" },
    { id: "PROT-01", title: "Proteinuria (Dipstick 2+)", met: true, details: "Dipstick 2+ documented" },
    { id: "HAEM-01", title: "Thrombocytopenia (<100)", met: true, details: "Platelets 88 x10³/µL" }
  ],

  derivedSubtype: "EOPE (Provisional)",
  derivedSeverity: "SEVERE_FEATURES",
  derivedOnset: "2026-07-28 (GA 33+0)",

  narrativeForm: "FORM-ADJ-15A",
  aiNarrative: "SECTION 1: CLINICAL HISTORY & DATING ANCHOR\nParticipant NGA002-0044 presented at 33+0 weeks gestation. Dating anchor missing (1st trimester USS / LMP not uploaded).\n\nSECTION 2: BLOOD PRESSURE & PROTEINURIA TIMELINE\nSingle BP reading 164/108 mmHg. Repeat BP missing. Dipstick proteinuria 2+.\n\nSECTION 3: LABORATORY ANALYTICS & ORGAN DYSFUNCTION\nPlatelets 88 x10³/µL (Thrombocytopenia). Creatinine and liver enzymes NOT DOCUMENTED.\n\nSECTION 4: FETAL GROWTH & UTEROPLACENTAL DOPPLER\nUltrasound report NOT DOCUMENTED.\n\nSECTION 5: DELIVERY DETAILS & NEONATAL OUTCOMES\nOutcome pending. Case incomplete under DV-26 (60% Completeness Score).",

  sourceDocs: {
    ultrasound: null,
    lims: "Partial LIMS Export: Platelets 88 x10^3/uL. Creatinine absent.",
    vitals: "eSource Vitals: 28-Jul 10:15 164/108 mmHg (Single reading).",
    delivery: null
  }
};

// Reference template case for 1-click sample demo load during presentation
export const SAMPLE_PRESENTATION_CASE = {
  id: "ZWE001-0292",
  caseNo: "ADJ-0412",
  site: "Mutala Clinical Research Site (ZWE001)",
  status: "Pending Review",
  trigger: "DV-30 (Severe BP + Proteinuria)",
  pktScore: 1.0,
  qcStatus: "FORM-ADJ-01 QC Passed (Blinding Verified)",
  gaAtEnrollment: "12+4",
  gaAtEvent: "31+2",
  edd: "2026-10-04",
  lnmp: "2025-12-28",
  firstUssDate: "2026-03-24",
  firstUssGa: "12+4",

  biomarkers: {
    sFlt1: "BLINDED — Withheld Until Database Lock (SOP-ADJ-002)",
    plgf: "BLINDED — Withheld Until Database Lock (SOP-ADJ-002)",
    ratio: "BLINDED — Withheld Until Database Lock (SOP-ADJ-002)",
    pocResult: "BLINDED (SOP-ADJ-002)"
  },

  bpLog: [
    { date: "2026-06-12 09:00", ga: "28+0", sbp: 118, dbp: 74, severe: false, source: "EDC Visit 2" },
    { date: "2026-07-04 08:14", ga: "31+2", sbp: 162, dbp: 112, severe: true, source: "eSource Vitals" },
    { date: "2026-07-04 12:40", ga: "31+2", sbp: 168, dbp: 114, severe: true, source: "eSource Vitals (Repeat)" }
  ],

  proteinuriaLog: [
    { date: "2026-06-12", method: "Dipstick", result: "1+", severe: false, source: "EDC Assessment" },
    { date: "2026-07-04", method: "UPCR", result: "1.84 g/g", numeric: 1.84, severe: true, source: "Crelio LIMS (LOINC 2889-4)" }
  ],

  labLog: [
    { analyte: "Platelet Count", result: "92", unit: "10^3/µL", refRange: "150 - 450", severe: true, source: "Crelio LIMS" },
    { analyte: "Creatinine", result: "1.31", unit: "mg/dL", refRange: "0.50 - 0.90", severe: true, source: "Crelio LIMS (Baseline: 0.62)" },
    { analyte: "AST", result: "96", unit: "U/L", refRange: "10 - 40", severe: true, source: "Crelio LIMS" },
    { analyte: "ALT", result: "78", unit: "U/L", refRange: "7 - 35", severe: true, source: "Crelio LIMS" },
    { analyte: "Hemoglobin", result: "11.8", unit: "g/dL", refRange: "11.5 - 15.0", severe: false, source: "Crelio LIMS" }
  ],

  criteria: [
    { id: "HTN-01", title: "Hypertension (≥140/90 mmHg, 4h apart)", met: true, details: "Confirmed: 162/112 @ 08:14 and 168/114 @ 12:40 (4h 26m apart)" },
    { id: "HTN-02", title: "Severe-range BP (≥160/110 mmHg)", met: true, details: "Severe: 168/114 confirmed on repeat" },
    { id: "PROT-01", title: "Proteinuria (UPCR ≥ 0.3 or 2+ dipstick)", met: true, details: "UPCR 1.84 g/g (threshold ≥ 0.3)" },
    { id: "HAEM-01", title: "Thrombocytopenia (Platelets < 100 x10³/µL)", met: true, details: "Platelets 92 x10³/µL (< 100 threshold)" },
    { id: "RENAL-01", title: "Renal Impairment (Creatinine > 1.1 mg/dL)", met: true, details: "Creatinine 1.31 mg/dL (Baseline 0.62 mg/dL)" },
    { id: "HEP-01", title: "Hepatic Dysfunction (AST/ALT > 2x ULN)", met: true, details: "AST 96 U/L (ULN 40 U/L)" },
    { id: "FGR-01", title: "Fetal Growth Restriction / Doppler", met: true, details: "EFW 6th centile, Absent End-Diastolic Flow (AEDF)" }
  ],

  derivedSubtype: "EOPE",
  derivedSeverity: "SEVERE_FEATURES",
  derivedOnset: "2026-07-04 (GA 31+2)",

  narrativeForm: "FORM-ADJ-15A",
  aiNarrative: "SECTION 1: CLINICAL HISTORY & DATING ANCHOR\nParticipant ZWE001-0292 is a 27-year-old G2P0 at 31+2 weeks gestation. Dating anchor established by 1st-trimester ultrasound at 12+4 weeks (24-Mar-2026), EDD 04-Oct-2026.\n\nSECTION 2: BLOOD PRESSURE & PROTEINURIA TIMELINE\nPresented at 31+2 weeks with new-onset severe hypertension (162/112 mmHg at 08:14), confirmed on repeat measurement (168/114 mmHg at 12:40). Proteinuria UPCR 1.84 g/g (04-Jul-2026).\n\nSECTION 3: LABORATORY ANALYTICS & ORGAN DYSFUNCTION\nLaboratory investigations demonstrated thrombocytopenia (platelets 92 x10³/µL), elevated serum creatinine at 1.31 mg/dL against baseline 0.62 mg/dL, and transaminitis (AST 96 U/L, ALT 78 U/L).\n\nSECTION 4: FETAL GROWTH & UTEROPLACENTAL DOPPLER\nObstetric ultrasound confirmed fetal growth restriction (EFW 1,210g, 6th centile) with Absent End-Diastolic Flow (AEDF) on umbilical artery Doppler.\n\nSECTION 5: DELIVERY DETAILS & NEONATAL OUTCOMES\nIntravenous Magnesium Sulfate started for seizure prophylaxis. Delivered by emergency caesarean section at 31+3 weeks. Liveborn female 1,200g, Apgar 7/9.",

  sourceDocs: {
    ultrasound: "Ultrasound Report (04-Jul-2026): Single live fetus, GA 31+2 by 12w scan. EFW 1,210g (6th percentile for GA). Umbilical Artery Doppler demonstrates Absent End-Diastolic Flow (AEDF). Amniotic fluid index 8.2 cm.",
    lims: "Crelio LIMS Specimen #LMS-9941 (04-Jul-2026 14:05): Platelets: 92 x10^3/uL [L], Creatinine: 1.31 mg/dL [H], AST: 96 U/L [H], UPCR: 1.84 g/g [H]. Baseline Creatinine (12-Jun-2026): 0.62 mg/dL.",
    delivery: "Delivery Record (05-Jul-2026 09:22): Emergency Caesarean Section under spinal anesthesia. Indication: EOPE with severe features and AEDF. Liveborn female, 1,200g, Apgar 7/9. Magnesium Sulfate infusion maintained for 24h postpartum.",
    vitals: "eSource Vitals Log: 04-Jul 08:14 SBP 162 DBP 112 mmHg (Nurse M. Moyo); 04-Jul 12:40 SBP 168 DBP 114 mmHg (Nurse M. Moyo)."
  }
};
