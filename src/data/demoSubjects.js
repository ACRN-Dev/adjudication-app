/**
 * ACRN PROTECT-Africa Adjudication Platform — 5 Gate-Test Demo Subjects
 * Change Record Item #15: Dedicated gate-test demo cases
 */

export const DEMO_EOPE_COMPLETE = {
  id: 'ZWE-DEMO-01',
  caseNo: 'ADJ-DEMO-001',
  site: '[Site blinded per SOP-ADJ-002]',
  status: 'Pending Review',
  trigger: 'DV-30 (Severe BP + Proteinuria + Organ Dysfunction)',
  pktScore: 1.0,
  gaAtEnrollment: '12+4',
  gaAtEvent: '31+2',
  edd: '2026-10-04',
  lnmp: '2025-12-28',
  firstUssDate: '2026-03-15',
  firstUssGa: '12+0',

  biomarkers: {
    sFlt1: 'BLINDED — Withheld per SOP-ADJ-002',
    plgf: 'BLINDED — Withheld per SOP-ADJ-002',
    ratio: 'BLINDED — Withheld per SOP-ADJ-002',
    pocResult: 'BLINDED — Withheld per SOP-ADJ-002',
  },

  bpLog: [
    { date: '2026-07-10', ga: '31+2', sbp: 164, dbp: 108, severe: true, source: 'eSource Vitals' },
    { date: '2026-07-10', ga: '31+2', sbp: 168, dbp: 112, severe: true, source: 'eSource Vitals (4h repeat)' },
    { date: '2026-07-11', ga: '31+3', sbp: 158, dbp: 104, severe: true, source: 'eSource Vitals' },
  ],

  proteinuriaLog: [
    { date: '2026-07-10', method: 'UPCR', result: '1.84 g/g (≥0.3 g/g threshold met)', numeric: 1.84, severe: true, source: 'Central LIMS' }
  ],

  labLog: [
    { analyte: 'Platelet Count', result: '88', unit: '×10³/µL', refRange: '150–450', severe: true, source: 'Central LIMS' },
    { analyte: 'Creatinine', result: '1.31', unit: 'mg/dL', refRange: '0.50–0.90', severe: true, source: 'Central LIMS' },
    { analyte: 'AST', result: '96', unit: 'U/L', refRange: '<40', severe: true, source: 'Central LIMS' },
    { analyte: 'ALT', result: '78', unit: 'U/L', refRange: '<35', severe: true, source: 'Central LIMS' },
    { analyte: 'LDH', result: '714', unit: 'IU/L', refRange: '<250', severe: true, source: 'Central LIMS' },
  ],

  criteria: [
    { id: 'DV-02', title: 'Severe Hypertension (≥160/110)', met: true, details: 'SBP 168 / DBP 112 mmHg' },
    { id: 'DV-03', title: 'Confirmed Hypertension', met: true, details: 'Qualifying BPs across 2 distinct dates with severe recheck' },
    { id: 'DV-07', title: 'Significant Proteinuria', met: true, details: 'UPCR 1.84 g/g (≥0.3)' },
    { id: 'DV-08', title: 'Thrombocytopenia', met: true, details: 'Platelets 88 ×10³/µL (<100)' },
    { id: 'DV-10', title: 'Renal Impairment', met: true, details: 'Creatinine 1.31 mg/dL (>1.1)' },
    { id: 'DV-11', title: 'Hepatic Dysfunction', met: true, details: 'AST 96 U/L, ALT 78 U/L (>2xULN)' },
  ],

  upcr: 1.84,
  dipstick_raw: '3+',
  platelet_count: 88,
  creatinine: 1.31,
  creatinine_unit: 'mg/dL',
  ast: 96,
  alt: 78,
  ldh: 714,
  efw_centile: 6,
  ua_aedf: true,

  derivedSubtype: 'EOPE',
  derivedSeverity: 'SEVERE_FEATURES',
  derivedOnset: '2026-07-10 (GA 31+2)',
  narrativeForm: 'FORM-ADJ-15A',

  sourceDocs: {
    ultrasound: 'USS dated 2026-07-10: EFW at 6th centile with AEDF on umbilical artery Doppler.',
    lims: 'LIMS report dated 2026-07-10: Plt 88, Cr 1.31, AST 96, ALT 78, LDH 714.',
    vitals: 'eSource Vitals log: 164/108 at 08:30, 168/112 at 12:45.',
    delivery: 'Delivery record dated 2026-07-11: Emergency C-section at GA 31+3. Liveborn 1340g.',
  },

  weightLog: [
    { date: '2026-06-15', ga: '27+4', weight_kg: 68.2 },
    { date: '2026-07-01', ga: '29+6', weight_kg: 70.8 },
    { date: '2026-07-10', ga: '31+2', weight_kg: 73.5 },
  ],

  medicationLog: [
    { name: 'Labetalol', dose: '200 mg BD', route: 'Oral', startDate: '2026-07-10' },
    { name: 'Magnesium Sulfate', dose: '4g IV bolus + 1g/h', route: 'IV', startDate: '2026-07-10' },
  ],

  delivery_date: '2026-07-11',
  ga_at_delivery: '31+3',
  gravidity: 2,
  parity: 1,
};

export const DEMO_LOPE_STANDARD = {
  id: 'KEN-DEMO-02',
  caseNo: 'ADJ-DEMO-002',
  site: '[Site blinded per SOP-ADJ-002]',
  status: 'Pending Review',
  trigger: 'DV-30 (Confirmed HTN + Proteinuria at ≥34 weeks)',
  pktScore: 1.0,
  gaAtEnrollment: '14+0',
  gaAtEvent: '36+4',
  edd: '2026-09-02',
  lnmp: '2025-11-26',
  firstUssDate: '2026-02-10',
  firstUssGa: '12+2',

  biomarkers: {
    sFlt1: 'BLINDED — Withheld per SOP-ADJ-002',
    plgf: 'BLINDED — Withheld per SOP-ADJ-002',
    ratio: 'BLINDED — Withheld per SOP-ADJ-002',
    pocResult: 'BLINDED — Withheld per SOP-ADJ-002',
  },

  bpLog: [
    { date: '2026-08-08', ga: '36+2', sbp: 144, dbp: 92, severe: false, source: 'Outpatient Clinic' },
    { date: '2026-08-10', ga: '36+4', sbp: 148, dbp: 96, severe: false, source: 'Triage' },
  ],

  proteinuriaLog: [
    { date: '2026-08-10', method: 'UPCR', result: '0.45 g/g (≥0.3 g/g threshold met)', numeric: 0.45, severe: false, source: 'Central LIMS' }
  ],

  labLog: [
    { analyte: 'Platelet Count', result: '182', unit: '×10³/µL', refRange: '150–450', severe: false, source: 'Central LIMS' },
    { analyte: 'Creatinine', result: '0.82', unit: 'mg/dL', refRange: '0.50–0.90', severe: false, source: 'Central LIMS' },
    { analyte: 'AST', result: '28', unit: 'U/L', refRange: '<40', severe: false, source: 'Central LIMS' },
    { analyte: 'ALT', result: '22', unit: 'U/L', refRange: '<35', severe: false, source: 'Central LIMS' },
  ],

  criteria: [
    { id: 'DV-03', title: 'Confirmed Hypertension', met: true, details: '144/92 and 148/96 on distinct dates' },
    { id: 'DV-07', title: 'Significant Proteinuria', met: true, details: 'UPCR 0.45 g/g' },
  ],

  upcr: 0.45,
  dipstick_raw: '2+',
  platelet_count: 182,
  creatinine: 0.82,
  creatinine_unit: 'mg/dL',
  ast: 28,
  alt: 22,
  efw_centile: 52,

  derivedSubtype: 'LOPE',
  derivedSeverity: 'STANDARD',
  derivedOnset: '2026-08-10 (GA 36+4)',
  narrativeForm: 'FORM-ADJ-15B',

  sourceDocs: {
    ultrasound: 'USS dated 2026-08-01: Normal fetal growth (52nd centile), normal Doppler.',
    lims: 'LIMS report dated 2026-08-10: Normal platelets, renal and liver function.',
    vitals: 'Outpatient BP log: 144/92, 148/96.',
    delivery: 'Delivery record dated 2026-08-15: Spontaneous vaginal delivery at 37+1. Normal neonate.',
  },

  delivery_date: '2026-08-15',
  ga_at_delivery: '37+1',
  gravidity: 1,
  parity: 0,
};

export const DEMO_INCOMPLETE_SEVERE = {
  id: 'NGA-DEMO-03',
  caseNo: 'ADJ-DEMO-003',
  site: '[Site blinded per SOP-ADJ-002]',
  status: 'Incomplete Evidence (DV-26)',
  trigger: 'DV-30 (Single Severe BP Reading)',
  pktScore: 0.17,
  gaAtEnrollment: null,
  gaAtEvent: '32+6',
  edd: null,
  lnmp: null,
  firstUssDate: null,
  firstUssGa: null,

  biomarkers: {
    sFlt1: 'BLINDED — Withheld per SOP-ADJ-002',
    plgf: 'BLINDED — Withheld per SOP-ADJ-002',
    ratio: 'BLINDED — Withheld per SOP-ADJ-002',
    pocResult: 'BLINDED — Withheld per SOP-ADJ-002',
  },

  bpLog: [
    { date: '2026-07-18', ga: '32+6', sbp: 164, dbp: 108, severe: true, source: 'Emergency Triage' },
  ],

  proteinuriaLog: [],
  labLog: [
    { analyte: 'Platelet Count', result: '91', unit: '×10³/µL', refRange: '150–450', severe: true, source: 'Emergency LIMS' }
  ],

  criteria: [
    { id: 'DV-02', title: 'Severe Hypertension (Single)', met: true, details: '164/108 mmHg' },
    { id: 'DV-08', title: 'Thrombocytopenia', met: true, details: 'Platelets 91 ×10³/µL' },
  ],

  upcr: null,
  dipstick_raw: null,
  platelet_count: 91,
  creatinine: null,
  ast: null,
  alt: null,

  derivedSubtype: 'UNCLASSIFIABLE',
  derivedSeverity: 'SEVERE_FEATURES',
  derivedOnset: '2026-07-18',
  narrativeForm: 'FORM-ADJ-15A',

  sourceDocs: {
    ultrasound: null,
    lims: 'Emergency LIMS: Platelets 91.',
    vitals: 'Triage sheet: single BP 164/108.',
    delivery: null,
  },

  delivery_date: null,
  ga_at_delivery: null,
  gravidity: 3,
  parity: 2,
};

export const DEMO_NON_CASE = {
  id: 'UGA-DEMO-04',
  caseNo: 'ADJ-DEMO-004',
  site: '[Site blinded per SOP-ADJ-002]',
  status: 'Pending Review (Possible Non-Trigger)',
  trigger: 'DV-30: Borderline - requires adjudication review',
  pktScore: 0.83,
  gaAtEnrollment: '13+1',
  gaAtEvent: '34+0',
  edd: '2026-09-18',
  lnmp: '2025-12-12',
  firstUssDate: '2026-03-01',
  firstUssGa: '12+0',

  biomarkers: {
    sFlt1: 'BLINDED — Withheld per SOP-ADJ-002',
    plgf: 'BLINDED — Withheld per SOP-ADJ-002',
    ratio: 'BLINDED — Withheld per SOP-ADJ-002',
    pocResult: 'BLINDED — Withheld per SOP-ADJ-002',
  },

  bpLog: [
    { date: '2026-08-01', ga: '33+5', sbp: 128, dbp: 82, severe: false, source: 'ANC Clinic' },
    { date: '2026-08-04', ga: '34+0', sbp: 132, dbp: 84, severe: false, source: 'ANC Clinic' },
  ],

  proteinuriaLog: [
    { date: '2026-08-04', method: 'Dipstick', result: 'Trace', numeric: null, severe: false, source: 'Dipstick' }
  ],

  labLog: [
    { analyte: 'Platelet Count', result: '240', unit: '×10³/µL', refRange: '150–450', severe: false, source: 'LIMS' },
    { analyte: 'Creatinine', result: '0.65', unit: 'mg/dL', refRange: '0.50–0.90', severe: false, source: 'LIMS' },
    { analyte: 'AST', result: '22', unit: 'U/L', refRange: '<40', severe: false, source: 'LIMS' },
    { analyte: 'ALT', result: '18', unit: 'U/L', refRange: '<35', severe: false, source: 'LIMS' },
  ],

  criteria: [],

  upcr: null,
  dipstick_raw: 'Trace',
  platelet_count: 240,
  creatinine: 0.65,
  ast: 22,
  alt: 18,
  efw_centile: 45,

  derivedSubtype: 'NON_CASE',
  derivedSeverity: 'STANDARD',
  derivedOnset: 'N/A',
  narrativeForm: 'FORM-ADJ-15B',

  sourceDocs: {
    ultrasound: 'USS dated 2026-08-01: Normal fetal growth (45th centile).',
    lims: 'Normal labs.',
    vitals: 'Normotensive BP entries.',
    delivery: 'Delivery record dated 2026-09-15: Term delivery at 39+4.',
  },

  delivery_date: '2026-09-15',
  ga_at_delivery: '39+4',
  gravidity: 1,
  parity: 0,
};

export const DEMO_POSTPARTUM = {
  id: 'ZIM-DEMO-05',
  caseNo: 'ADJ-DEMO-005',
  site: '[Site blinded per SOP-ADJ-002]',
  status: 'Pending Review',
  trigger: 'DV-30 (Postpartum HTN + Proteinuria)',
  pktScore: 0.67,
  gaAtEnrollment: '16+0',
  gaAtEvent: '39+1 (Postpartum Day 3)',
  edd: '2026-07-28',
  lnmp: '2025-10-21',
  firstUssDate: '2026-01-15',
  firstUssGa: '12+1',

  biomarkers: {
    sFlt1: 'BLINDED — Withheld per SOP-ADJ-002',
    plgf: 'BLINDED — Withheld per SOP-ADJ-002',
    ratio: 'BLINDED — Withheld per SOP-ADJ-002',
    pocResult: 'BLINDED — Withheld per SOP-ADJ-002',
  },

  bpLog: [
    { date: '2026-08-01', ga: '39+1 (PP Day 3)', sbp: 156, dbp: 104, severe: false, source: 'Postpartum Ward' },
    { date: '2026-08-02', ga: '39+1 (PP Day 4)', sbp: 162, dbp: 108, severe: true, source: 'Postpartum Ward' },
  ],

  proteinuriaLog: [
    { date: '2026-08-01', method: 'UPCR', result: '0.38 g/g (≥0.3 g/g threshold met)', numeric: 0.38, severe: true, source: 'Hospital LIMS' }
  ],

  labLog: [
    { analyte: 'Platelet Count', result: '134', unit: '×10³/µL', refRange: '150–450', severe: false, source: 'Hospital LIMS' },
    { analyte: 'Creatinine', result: '0.98', unit: 'mg/dL', refRange: '0.50–0.90', severe: false, source: 'Hospital LIMS' },
    { analyte: 'AST', result: '36', unit: 'U/L', refRange: '<40', severe: false, source: 'Hospital LIMS' },
    { analyte: 'ALT', result: '30', unit: 'U/L', refRange: '<35', severe: false, source: 'Hospital LIMS' },
  ],

  criteria: [
    { id: 'DV-02', title: 'Severe Postpartum HTN', met: true, details: '162/108 mmHg on Postpartum Day 4' },
    { id: 'DV-07', title: 'Significant Proteinuria', met: true, details: 'UPCR 0.38 g/g' },
  ],

  upcr: 0.38,
  dipstick_raw: '2+',
  platelet_count: 134,
  creatinine: 0.98,
  ast: 36,
  alt: 30,

  derivedSubtype: 'POSTPARTUM',
  derivedSeverity: 'SEVERE_FEATURES',
  derivedOnset: 'Postpartum Day 3',
  narrativeForm: 'FORM-ADJ-15A',

  sourceDocs: {
    ultrasound: null,
    lims: 'LIMS report dated 2026-08-01: UPCR 0.38 g/g, Platelets 134.',
    vitals: 'Postpartum ward BP chart: 156/104, 162/108.',
    delivery: 'Delivery record: Normal vaginal delivery on 2026-07-29 at 39+1 weeks.',
  },

  delivery_date: '2026-07-29',
  ga_at_delivery: '39+1',
  gravidity: 2,
  parity: 1,
};

export const ALL_DEMO_SUBJECTS = [
  DEMO_EOPE_COMPLETE,
  DEMO_LOPE_STANDARD,
  DEMO_INCOMPLETE_SEVERE,
  DEMO_NON_CASE,
  DEMO_POSTPARTUM,
];
