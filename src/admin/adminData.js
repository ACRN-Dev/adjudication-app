export const demoUsers = [
  ['Tariro Moyo','tech.admin.demo@acrnhealth.com','Technical Administrator','Platform-wide','Zimbabwe','Current','31 Jan 2027','Active'],
  ['Amara Okafor','clinical.ops.demo@acrnhealth.com','Clinical Operations Administrator','PROTECT-Africa, LOPE-Nigeria','Nigeria','Current','17 Sep 2026','Active'],
  ['Lindiwe Dube','pending.demo@acrnhealth.com','Access requested','PROTECT-Africa','South Africa','Incomplete','Pending','Pending approval'],
  ['Kofi Mensah','qa.auditor.demo@acrnhealth.com','QA/Auditor','All governed studies','Ghana','Current','15 Aug 2026','Active']
];

export const studies = [
  ['PROTECT-Africa','PROTECT-Africa EOPE Study','A202501 v1.2','Zimbabwe, South Africa, Ghana','Active','v3','DV-ISSHP-2021-1.0','MAP-PROTECT-2.1'],
  ['LOPE-Nigeria','LOPE Nigeria','ACRN-202503 v1.1','Nigeria','Validation','v2','DV-ISSHP-2021-1.0','MAP-LOPE-1.1']
];

export const sites = [
  ['ZWE001','Site ZW-01 (Harare Central)','Zimbabwe','PROTECT-Africa','Active','ZWE001','EDC, eSource, LIMS'],
  ['ZWE002','Site ZW-02 (Parirenyatwa)','Zimbabwe','PROTECT-Africa','Active','ZWE002','EDC, eSource'],
  ['NGA004','Site NG-04 (Lagos University)','Nigeria','LOPE-Nigeria','Active','NGA004','EDC, eSource, LIMS'],
  ['ZAF001','Site ZA-01 (Groote Schuur)','South Africa','PROTECT-Africa','Active','ZAF001','EDC, eSource, LIMS'],
  ['GHA001','Site GH-01 (Korle Bu)','Ghana','PROTECT-Africa','Active','GHA001','EDC, eSource']
];

export const rules = Array.from({length:30},(_,i)=>[
  `DV-${String(i+1).padStart(2,'0')}`,
  i === 0 ? 'Systolic BP Threshold Check (≥140 mmHg)' :
  i === 1 ? 'Diastolic BP Threshold Check (≥90 mmHg)' :
  i === 2 ? 'Severe Hypertension Verification (≥160/110)' :
  i === 3 ? 'Proteinuria Dipstick Conversion & Corroboration' :
  i === 4 ? 'Thrombocytopenia Detection (<100 x10⁹/L)' :
  i === 5 ? 'Serum Creatinine Elevation (>90 µmol/L)' :
  i === 6 ? 'Hepatic Transaminase Doubling (>40 U/L)' :
  i === 7 ? 'Early vs Late Onset Gestational Window (≤34w vs >34w)' :
  i === 8 ? 'Superimposed PE in Chronic HTN Derivation' :
  i === 9 ? 'Fetal Growth Restriction / Doppler Verification' :
  `Controlled clinical derivation ${i+1}`,
  'ISSHP-aligned deterministic rule',
  '1.0',
  '04 Apr 2026',
  'Active',
  'Clinical + QA',
  'Passed'
]);

export const mappings = [
  ['EDC / eSource','SYSBP','systolic_bp','Number','mmHg','Required','PROTECT-Africa','2.1','Active','Visible'],
  ['EDC / eSource','DIABP','diastolic_bp','Number','mmHg','Required','PROTECT-Africa','2.1','Active','Visible'],
  ['LIMS','PLT','platelet_count','Number','×10⁹/L','Optional','Both studies','2.1','Active','Visible'],
  ['LIMS','CREAT','serum_creatinine','Number','µmol/L','Required','Both studies','2.1','Active','Visible'],
  ['LIMS','ALT','alt_enzyme','Number','U/L','Required','Both studies','2.1','Active','Visible'],
  ['LIMS','AST','ast_enzyme','Number','U/L','Required','Both studies','2.1','Active','Visible'],
  ['EDC','UPROTDIP','urine_protein_dipstick','Text','Grade (Neg/Trace/1+/2+/3+)','Required','Both studies','2.1','Active','Visible'],
  ['EDC','GESTAGE','gestational_age_days','Integer','Days','Required','Both studies','2.1','Active','Visible'],
  ['EDC','DELIVMOD','delivery_mode','Categorical','C-Section/SVD/Assisted','Required','Both studies','2.1','Active','Visible'],
  ['EDC','BWGHT','birth_weight_grams','Number','Grams','Required','Both studies','2.1','Active','Visible'],
  ['LIMS [RESTRICTED]','SFLT1','sflt1_concentration','Number','pg/mL','Prohibited (Blinded)','Both studies','2.1','Withheld','Prohibited'],
  ['LIMS [RESTRICTED]','PLGF','plgf_concentration','Number','pg/mL','Prohibited (Blinded)','Both studies','2.1','Withheld','Prohibited']
];

export const forms = [
  ['FORM-ADJ-01','QC checklist & pre-release blinding audit','1.0','Both studies','Active','SOP-ADJ-004'],
  ['FORM-ADJ-05','Clinical data query & site clarification request','1.0','Both studies','Active','SOP-ADJ-004'],
  ['FORM-ADJ-08','Adjudicator recusal & conflict declaration','1.0','Both studies','Active','SOP-ADJ-003'],
  ['FORM-ADJ-09','Unblinding incident & protocol breach log','1.0','Both studies','Active','SOP-ADJ-002'],
  ['FORM-ADJ-11','Clinical narrative modification audit trail','1.0','Both studies','Active','SOP-ADJ-004'],
  ['FORM-ADJ-15A','EOPE standardized case narrative packet','1.0','PROTECT-Africa','Active','SOP-ADJ-002'],
  ['FORM-ADJ-15B','LOPE standardized case narrative packet','1.0','LOPE-Nigeria','Active','SOP-ADJ-002']
];

export const integrations = [
  ['REDCap EDC Gateway','EDC / eCRF','DEMO','Healthy','Today 06:15','Configured & Validated','Enabled'],
  ['eSource Clinical Adapter','eSource Tablets','DEMO','Warning','02 Aug 2026','Configured','Enabled'],
  ['Central LIMS Gateway','Laboratory HL7/FHIR','DEMO','Healthy','Today 05:52','Configured & Validated','Enabled'],
  ['Microsoft Entra ID (SSO)','Identity Provider','DEMO','Healthy','Today 04:30','Configured (SAML 2.0)','Enabled'],
  ['SharePoint Document Hub','Trial Master File','DEMO','Healthy','Yesterday 22:10','Configured (Graph API)','Enabled'],
  ['eTMF Export Adapter (Veeva)','Regulatory Archive','DEMO','Warning','01 Aug 2026','Synthetic Staging','Enabled']
];

export const audits = [
  ['AUD-DEMO-1048','22 Sep 2026 14:10','tech.admin.demo@acrnhealth.com','TECHNICAL_ADMIN','SOP_VERSION_REVIEWED','SOP-ADJ-001 v1.0','Annual periodic review verified','Success'],
  ['AUD-DEMO-1047','22 Sep 2026 11:25','clinical.ops.demo@acrnhealth.com','CLINICAL_OPS_ADMIN','TRAINING_CERT_VERIFIED','Dr. Miriam Ndlovu','GCP Refresher 2026 verified','Success'],
  ['AUD-DEMO-1046','21 Sep 2026 19:15','clinical.ops.demo@acrnhealth.com','CLINICAL_OPS_ADMIN','ENDPOINT_SPEC_UPDATED','EP-EOPE (ISSHP 2021)','Guideline cross-reference added','Success'],
  ['AUD-DEMO-1045','20 Sep 2026 16:40','tech.admin.demo@acrnhealth.com','TECHNICAL_ADMIN','PROHIBITED_FIELD_CHECK','LIMS Gateway Ingestion','Zero unblinding biomarkers detected','Success'],
  ['AUD-DEMO-1042','03 Aug 2026 09:18','clinical.ops.demo@acrnhealth.com','CLINICAL_OPS_ADMIN','STUDY_VERSION_CREATED','PROTECT-Africa v3','Protocol alignment','Success'],
  ['AUD-DEMO-1041','03 Aug 2026 08:47','qa.auditor.demo@acrnhealth.com','QA_AUDITOR','MAPPING_APPROVED','MAP-PROTECT 2.1','Validation reviewed','Success'],
  ['AUD-DEMO-1040','02 Aug 2026 16:04','tech.admin.demo@acrnhealth.com','TECHNICAL_ADMIN','ACCESS_REJECTED','pending.demo','Training incomplete','Success'],
  ['AUD-DEMO-1039','02 Aug 2026 14:31','unknown.demo@acrnhealth.com','ADJUDICATOR','ADMIN_ROUTE_DENIED','/api/admin/users','Role not permitted','Failed']
];

export const workflow = [
  'Imported',
  'Mapping Review',
  'Reconciliation Required',
  'Packet Preparation',
  'Pre-QC',
  'Query Open',
  'QC Released',
  'Assigned',
  'Reviewer In Progress',
  'Reviewer Submitted',
  'Concordance Check',
  'Discordant',
  'Committee Review',
  'Committee Locked',
  'Final QC',
  'Ready for Release',
  'Released',
  'Archived'
];

// Governed Clinical Adjudication Datasets

export const training = [
  {
    name: 'Prof. Tariro Moyo',
    email: 'tariro.moyo@acrnhealth.com',
    role: 'CHAIRPERSON',
    study: 'PROTECT-Africa & LOPE-Nigeria',
    gcpCert: 'ICH-GCP E6(R2)',
    gcpCompleted: '14 Jan 2026',
    gcpExpiry: '14 Jan 2028',
    protocolCharter: 'Completed (v2.0)',
    isshpCriteria: 'Certified Expert',
    coiStatus: 'Disclosed (No Conflict)',
    coiDate: '10 Jan 2026',
    status: 'Current'
  },
  {
    name: 'Dr. Fatima Al-Mansoor',
    email: 'fatima.almansoor@acrnhealth.com',
    role: 'ADJUDICATOR',
    study: 'PROTECT-Africa',
    gcpCert: 'ICH-GCP E6(R2)',
    gcpCompleted: '05 Feb 2026',
    gcpExpiry: '05 Feb 2028',
    protocolCharter: 'Completed (v2.0)',
    isshpCriteria: 'Certified',
    coiStatus: 'Disclosed (No Conflict)',
    coiDate: '01 Feb 2026',
    status: 'Current'
  },
  {
    name: 'Dr. Kwame Appiah',
    email: 'kwame.appiah@acrnhealth.com',
    role: 'ADJUDICATOR',
    study: 'PROTECT-Africa',
    gcpCert: 'ICH-GCP E6(R2)',
    gcpCompleted: '12 Nov 2025',
    gcpExpiry: '12 Nov 2027',
    protocolCharter: 'Completed (v2.0)',
    isshpCriteria: 'Certified',
    coiStatus: 'Disclosed (No Conflict)',
    coiDate: '10 Nov 2025',
    status: 'Current'
  },
  {
    name: 'Dr. Miriam Ndlovu',
    email: 'miriam.ndlovu@acrnhealth.com',
    role: 'ADJUDICATOR',
    study: 'PROTECT-Africa',
    gcpCert: 'ICH-GCP E6(R2)',
    gcpCompleted: '20 Sep 2024',
    gcpExpiry: '20 Sep 2026',
    protocolCharter: 'Completed (v2.0)',
    isshpCriteria: 'Certified',
    coiStatus: 'Disclosed (Site ZWE001 Recused)',
    coiDate: '15 Jan 2026',
    status: 'Expiring Soon'
  },
  {
    name: 'Dr. Babatunde Adeleke',
    email: 'babatunde.adeleke@acrnhealth.com',
    role: 'ADJUDICATOR',
    study: 'LOPE-Nigeria',
    gcpCert: 'ICH-GCP E6(R2)',
    gcpCompleted: '18 Mar 2025',
    gcpExpiry: '18 Mar 2027',
    protocolCharter: 'Completed (v1.1)',
    isshpCriteria: 'Certified',
    coiStatus: 'Disclosed (No Conflict)',
    coiDate: '15 Mar 2026',
    status: 'Current'
  },
  {
    name: 'Amara Okafor',
    email: 'clinical.ops.demo@acrnhealth.com',
    role: 'MONITOR',
    study: 'Both Studies',
    gcpCert: 'ICH-GCP E6(R2)',
    gcpCompleted: '10 Jan 2026',
    gcpExpiry: '10 Jan 2028',
    protocolCharter: 'Completed (v2.0)',
    isshpCriteria: 'Certified',
    coiStatus: 'Disclosed (No Conflict)',
    coiDate: '08 Jan 2026',
    status: 'Current'
  },
  {
    name: 'Lindiwe Dube',
    email: 'pending.demo@acrnhealth.com',
    role: 'MONITOR',
    study: 'PROTECT-Africa',
    gcpCert: 'Not Submitted',
    gcpCompleted: '—',
    gcpExpiry: '—',
    protocolCharter: 'Pending Review',
    isshpCriteria: 'Pending',
    coiStatus: 'Pending Submission',
    coiDate: '—',
    status: 'Incomplete'
  }
];

export const endpoints = [
  {
    code: 'EP-EOPE',
    name: 'Early-Onset Pre-eclampsia (EOPE)',
    standard: 'ISSHP 2021 / 2022 Criteria',
    window: '≤ 34 weeks, 0 days gestation',
    consensus: '2 Concordant Reviewers or Committee Consensus',
    type: 'Primary Endpoint',
    description: 'Gestational hypertension developing after 20 weeks with new-onset proteinuria and/or maternal end-organ dysfunction (renal, hepatic, hematologic, or neurological) presenting at or prior to 34+0 weeks GA.',
    status: 'Active'
  },
  {
    code: 'EP-LOPE',
    name: 'Late-Onset Pre-eclampsia (LOPE)',
    standard: 'ISSHP 2021 / 2022 Criteria',
    window: '> 34 weeks, 0 days gestation',
    consensus: '2 Concordant Reviewers or Committee Consensus',
    type: 'Primary Endpoint',
    description: 'Gestational hypertension developing after 20 weeks with new-onset proteinuria and/or maternal end-organ dysfunction presenting after 34+0 weeks GA up to delivery.',
    status: 'Active'
  },
  {
    code: 'EP-GH',
    name: 'Gestational Hypertension (GH)',
    standard: 'ISSHP 2021 / 2022 Criteria',
    window: '> 20 weeks, 0 days gestation',
    consensus: '2 Concordant Reviewers or Committee Consensus',
    type: 'Secondary Endpoint',
    description: 'New-onset persistent hypertension (SBP ≥ 140 or DBP ≥ 90 mmHg) after 20 weeks gestation in the absence of proteinuria or systemic end-organ dysfunction.',
    status: 'Active'
  },
  {
    code: 'EP-SPE',
    name: 'Superimposed Pre-eclampsia in Chronic HTN',
    standard: 'ISSHP 2021 / 2022 Criteria',
    window: 'Antenatal through postpartum',
    consensus: '2 Concordant Reviewers or Committee Consensus',
    type: 'Primary Co-Endpoint',
    description: 'Sudden severe exacerbation of hypertension, new-onset proteinuria, or new biochemical end-organ failure in a patient with documented chronic hypertension.',
    status: 'Active'
  },
  {
    code: 'EP-SEV',
    name: 'Pre-eclampsia with Severe Features',
    standard: 'ISSHP 2021 / ACOG Guidelines',
    window: 'Any gestational age',
    consensus: '2 Concordant Reviewers or Committee Consensus',
    type: 'Secondary Severity Endpoint',
    description: 'Severe hypertension (SBP ≥ 160 or DBP ≥ 110 mmHg on 2 occasions), thrombocytopenia (<100 x10⁹/L), impaired liver function, progressive renal insufficiency, pulmonary edema, or persistent cerebral/visual disturbances.',
    status: 'Active'
  },
  {
    code: 'EP-MAO',
    name: 'Severe Maternal Adverse Outcomes',
    standard: 'WHO Near-Miss / Maternal Morbidity',
    window: 'Pregnancy through 42 days postpartum',
    consensus: 'Full Committee Consensus Mandatory',
    type: 'Safety Endpoint',
    description: 'Eclampsia, HELLP syndrome, stroke, acute kidney injury requiring dialysis, liver rupture, ICU admission, or maternal death.',
    status: 'Active'
  },
  {
    code: 'EP-PND',
    name: 'Perinatal / Fetal / Neonatal Death',
    standard: 'WHO Stillbirth & Neonatal Death Def.',
    window: '≥ 20 weeks GA to 28 days post-delivery',
    consensus: 'Full Committee Consensus Mandatory',
    type: 'Fetal / Neonatal Safety Endpoint',
    description: 'Intrauterine fetal demise, intrapartum stillbirth, or early/late neonatal death within trial follow-up.',
    status: 'Active'
  }
];

export const visitWindows = [
  { visit: 'Visit 1 (V01)', name: 'Baseline / Screening', targetGa: '12 – 20 weeks', permittedWindow: '11w0d – 21w6d', mandatoryLabs: 'Full Blood Count, Renal (Creatinine), Liver (ALT/AST), Urinalysis Dipstick, Dating Ultrasound' },
  { visit: 'Visit 2 (V02)', name: 'Anatomy / Routine Follow-up', targetGa: '18 – 24 weeks', permittedWindow: '18w0d – 25w6d', mandatoryLabs: 'Sitting Blood Pressure (duplicate), Urinalysis Dipstick, Fetal Anatomy Scan' },
  { visit: 'Visit 3 (V03)', name: 'Second Trimester Surveillance', targetGa: '26 – 28 weeks', permittedWindow: '25w0d – 29w6d', mandatoryLabs: 'Blood Pressure, Urine Protein, Full Blood Count, Clinical Adverse Event Review' },
  { visit: 'Visit 4 (V04)', name: 'Third Trimester Escalation', targetGa: '32 – 34 weeks', permittedWindow: '31w0d – 35w6d', mandatoryLabs: 'Blood Pressure, Urine Protein, Full Blood Count, Renal & Liver Panel, Growth Biometry' },
  { visit: 'Visit 5 (V05)', name: 'Delivery / Hospital Admission', targetGa: '37 – 41 weeks', permittedWindow: 'Onset of Labor / Planned Delivery', mandatoryLabs: 'Delivery mode, Indication, Maternal blood loss, Newborn sex, Birth weight, Apgar scores (1 & 5 min)' },
  { visit: 'Visit 6 (V06)', name: 'Postnatal Follow-up', targetGa: '4 – 6 weeks postpartum', permittedWindow: '28 – 56 days post-delivery', mandatoryLabs: 'Postpartum Blood Pressure, Maternal recovery assessment, Infant disorder screening status' }
];

export const terminology = [
  { parameter: 'Systolic Blood Pressure', canonicalUnit: 'mmHg', acceptedUnits: 'mmHg', conversion: '1 : 1', range: '90 – 220 mmHg', validation: 'Sitting position, calibrated sphygmomanometer, duplicate reading if ≥140' },
  { parameter: 'Diastolic Blood Pressure', canonicalUnit: 'mmHg', acceptedUnits: 'mmHg', conversion: '1 : 1', range: '50 – 140 mmHg', validation: 'Phase V Korotkoff sound, duplicate reading if ≥90' },
  { parameter: 'Serum Creatinine', canonicalUnit: 'µmol/L', acceptedUnits: 'mg/dL, µmol/L', conversion: 'mg/dL × 88.4 = µmol/L', range: '20 – 350 µmol/L', validation: 'Flag if >90 µmol/L (ISSHP renal threshold)' },
  { parameter: 'Platelet Count', canonicalUnit: '×10⁹/L', acceptedUnits: '×10³/µL, ×10⁹/L', conversion: '1 : 1', range: '20 – 600 ×10⁹/L', validation: 'Flag if <100 ×10⁹/L (Thrombocytopenia threshold)' },
  { parameter: 'ALT (Alanine Aminotransferase)', canonicalUnit: 'U/L', acceptedUnits: 'U/L, µkat/L', conversion: 'µkat/L × 60 = U/L', range: '2 – 300 U/L', validation: 'Flag if >40 U/L (Liver injury threshold)' },
  { parameter: 'AST (Aspartate Aminotransferase)', canonicalUnit: 'U/L', acceptedUnits: 'U/L, µkat/L', conversion: 'µkat/L × 60 = U/L', range: '2 – 300 U/L', validation: 'Flag if >40 U/L (Liver injury threshold)' },
  { parameter: 'Total Bilirubin', canonicalUnit: 'µmol/L', acceptedUnits: 'mg/dL, µmol/L', conversion: 'mg/dL × 17.1 = µmol/L', range: '2 – 100 µmol/L', validation: 'Flag if >20 µmol/L' },
  { parameter: 'LDH (Lactate Dehydrogenase)', canonicalUnit: 'U/L', acceptedUnits: 'U/L', conversion: '1 : 1', range: '80 – 800 U/L', validation: 'Flag if >600 U/L (HELLP hemolysis threshold)' },
  { parameter: 'Urine Protein Dipstick', canonicalUnit: 'Grade', acceptedUnits: 'Negative, Trace, 1+, 2+, 3+, 4+', conversion: 'Categorical mapping', range: 'Negative to 4+', validation: 'Trace or ≥1+ triggers corroborative review' },
  { parameter: 'Urine Protein:Creatinine Ratio', canonicalUnit: 'mg/mmol', acceptedUnits: 'mg/mg, mg/mmol', conversion: 'mg/mg × 113.1 = mg/mmol', range: '5 – 800 mg/mmol', validation: '≥30 mg/mmol meets ISSHP significant proteinuria' },
  { parameter: 'Estimated Fetal Weight', canonicalUnit: 'grams', acceptedUnits: 'grams, kg, lbs', conversion: 'kg × 1000 = g; lbs × 453.59 = g', range: '100 – 5500 g', validation: 'Hadlock formula standardized percentile calculation' }
];

export const dictionaries = [
  { code: 'DICT-MEDDRA', name: 'MedDRA (Medical Dictionary for Regulatory Activities)', authority: 'ICH / MSSO', version: 'v27.0 (English)', releaseDate: 'March 2024', status: 'Active (Standard)', scope: 'Adverse Events, Medical History, Maternal Morbidity Coding' },
  { code: 'DICT-WHODRUG', name: 'WHO Drug Global Dictionary', authority: 'Uppsala Monitoring Centre', version: 'March 2026 B3', releaseDate: 'March 2026', status: 'Active (Standard)', scope: 'Concomitant Medications, Antihypertensives, Insulin, Aspirin' },
  { code: 'DICT-LOINC', name: 'LOINC Laboratory Assay Terminology', authority: 'Regenstrief Institute', version: 'v2.76', releaseDate: 'December 2025', status: 'Active (Standard)', scope: 'Laboratory Analyte Mapping & Canonical Harmonization' },
  { code: 'DICT-ICD11', name: 'ICD-11 MMS (Mortality and Morbidity Statistics)', authority: 'World Health Organization', version: '2024-01 Release', releaseDate: 'January 2024', status: 'Active (Standard)', scope: 'Obstetrical Diagnosis & Perinatal Death Classification' },
  { code: 'DICT-ISSHP', name: 'ISSHP Preeclampsia Diagnostic Classification', authority: 'ISSHP International Society', version: '2021 / 2022 Update', releaseDate: 'August 2021', status: 'Active (Standard)', scope: 'Authoritative Diagnostic Standard for Adjudication Engine' },
  { code: 'DICT-BLINDING', name: 'Prohibited Unblinding Terms Registry', authority: 'ACRN Governance Board', version: 'v3.0 (Enforced)', releaseDate: 'May 2026', status: 'Active (Enforced)', scope: 'Automated String Scanner for Narratives & Raw Uploads' }
];

export const prohibitedWords = [
  'sFlt-1', 'sFlt1', 'PlGF', 'PIGF', 'sFlt-1/PlGF', 'sEng', 'Endoglin',
  'POC biomarker', 'Point-of-care test', 'Biomarker ratio', 'Active arm',
  'Control arm', 'Treatment allocation', 'Randomization group', 'Arm A', 'Arm B',
  'Study drug kit', 'Placebo kit', 'Investigational batch'
];

export const importContracts = [
  {
    channel: 'REDCap EDC Gateway',
    source: 'Oracle Clinical One / Site REDCap instances',
    protocol: 'REST API (OAuth 2.0 Mutual TLS)',
    format: 'JSON / CDISC ODM XML',
    frequency: 'Automated Real-Time Webhook + Hourly Sync',
    checksum: 'SHA-256 Payload Hash Verification',
    quarantine: 'Missing required visits, invalid participant ID checksum, or unblinding token present',
    status: 'Operational (Active)'
  },
  {
    channel: 'GCP-Sense Mobile eSource',
    source: 'Offline Tablet Point-of-Care Enrolment',
    protocol: 'Encrypted Sync Service (WSS / TLS 1.3)',
    format: 'Structured FHIR Observation Bundles',
    frequency: 'Near Real-time upon network reconnection',
    checksum: 'ECDSA Digital Signature per Record',
    quarantine: 'Signature mismatch, missing vital timestamp, or out-of-range maternal pulse (>220 bpm)',
    status: 'Operational (Warning on latency)'
  },
  {
    channel: 'Central Laboratory LIMS',
    source: 'Barcoded Clinical Analyzers (Roche / Abbott)',
    protocol: 'HL7 v2.5.1 / MLLP Gateway over IPsec Tunnel',
    format: 'HL7 ORU^R01 Unsolicited Observation Message',
    frequency: 'Event-driven on result release',
    checksum: 'Specimen Barcode & Accession Verification',
    quarantine: 'Unblinding biomarker analytes automatically dropped; accession mismatch quarantined',
    status: 'Operational (Active)'
  },
  {
    channel: 'Ultrasound Imaging eSource',
    source: 'GE Voluson / Philips Ultrasound Systems',
    protocol: 'DICOM C-STORE / Structured Report Import',
    format: 'DICOM SR (Ultrasound OB-GYN) + Anonymized PNGs',
    frequency: 'Batch upload per scheduled scan visit',
    checksum: 'De-identification Hash Verification',
    quarantine: 'Burned-in maternal identifying text or missing biometric gestational dating',
    status: 'Operational (Active)'
  },
  {
    channel: 'CSV Adjudication Dossier Upload',
    source: 'Coordinated Clinical Trial Operations Team',
    protocol: 'Web Portal Upload with Dual Authorization',
    format: 'CSV RFC 4180 UTF-8 with Strict Header Schema',
    frequency: 'Ad-hoc per patient cohort batch',
    checksum: 'Row-level MD5 + Header Signature Match',
    quarantine: 'Unmapped header columns, malformed dates, or invalid participant format',
    status: 'Operational (Active)'
  }
];

export const sops = [
  {
    code: 'SPEC-AI-001',
    title: 'ACRN AI Adjudication Agent Master Specification',
    version: 'v1.0',
    effectiveDate: '01 Jan 2026',
    reviewCycle: 'Annual',
    scope: 'Decision-Support Boundary, Source Hierarchy, Non-Negotiable Human Primacy',
    status: 'Governed & Enforced',
    summary: 'Defines the non-negotiable governance boundaries of the advisory AI assistant: never votes, never breaks ties, never self-unblinds, and maintains dual independent human review standard.'
  },
  {
    code: 'OAC Charter',
    title: 'Outcomes Adjudication Committee Master Charter',
    version: 'v2.0',
    effectiveDate: '15 Jan 2026',
    reviewCycle: 'Bi-annual',
    scope: 'Committee Composition, Quorum (3/5), Discordance Arbitration, Chairperson Sign-Off',
    status: 'Governed & Enforced',
    summary: 'Governs independent clinical endpoint adjudicators, voting mechanisms, mandatory 3-of-5 quorum, recusal rules for treating physicians, and final Part 11 electronic signature sign-off.'
  },
  {
    code: 'SOP-ADJ-001',
    title: 'Adjudication Process, Case Selection & Concordance Management',
    version: 'v1.0',
    effectiveDate: '01 Feb 2026',
    reviewCycle: 'Annual',
    scope: 'Case Routing, Dual Reviewer Blinded Pairing, Discordance Resolution',
    status: 'Governed & Enforced',
    summary: 'Standard operating procedure detailing step-by-step workflow from coordinator packet release to dual independent reviewer assessment and tie-breaker routing.'
  },
  {
    code: 'SOP-ADJ-002',
    title: 'Blinding Architecture & Prohibited Biomarker Withholding',
    version: 'v1.0',
    effectiveDate: '01 Feb 2026',
    reviewCycle: 'Annual',
    scope: 'Biomarker Withholding (sFlt-1/PlGF, sEng, POC), Blinding Integrity, Breach Reporting',
    status: 'Governed & Enforced',
    summary: 'Enforces programmatic redaction and suppression of study biomarkers and randomized treatment arms across all adjudicator-facing portals until database lock.'
  },
  {
    code: 'SOP-ADJ-003',
    title: 'Adjudicator Conflict of Interest & Mandatory Recusal Protocol',
    version: 'v1.0',
    effectiveDate: '01 Feb 2026',
    reviewCycle: 'Annual',
    scope: 'Site Separation, Clinical Care Exclusion, Financial COI Declarations',
    status: 'Governed & Enforced',
    summary: 'Protocol governing annual and case-by-case disclosures; mandates automatic recusal of physicians who provided direct care or served as trial investigators at the subject’s enrolling site.'
  },
  {
    code: 'SOP-ADJ-004',
    title: 'Clinical Data Queries, Reconciliation & Narrative Modification',
    version: 'v1.0',
    effectiveDate: '01 Feb 2026',
    reviewCycle: 'Annual',
    scope: 'Pre-QC Checklist (FORM-ADJ-01), Clinical Query Routing (FORM-ADJ-05), Narrative Audit',
    status: 'Governed & Enforced',
    summary: 'Defines communication between adjudicators and site coordinators when clinical data packets are ambiguous or contradictory.'
  },
  {
    code: 'SOP-ADJ-005',
    title: 'Electronic Signatures, 21 CFR Part 11 & Audit Trail Governance',
    version: 'v1.0',
    effectiveDate: '01 Feb 2026',
    reviewCycle: 'Annual',
    scope: 'Digital Signatures, Passphrase Re-authentication, Immutable Event Ledger',
    status: 'Governed & Enforced',
    summary: 'Ensures compliance with US FDA 21 CFR Part 11 and ICH-GCP for electronic signatures, tamper-evident audit logs, and non-repudiation.'
  },
  {
    code: 'SOP-ADJ-006',
    title: 'Quality Assurance, Periodic Access Reviews & Regulatory Inspection Readiness',
    version: 'v1.0',
    effectiveDate: '01 Feb 2026',
    reviewCycle: 'Annual',
    scope: 'Quarterly Access Certification, System Health, Audit Trail Archival',
    status: 'Governed & Enforced',
    summary: 'Governs quarterly access certifications, automated anomaly detection, system migration logs, and inspection readiness for regulatory audits.'
  }
];
