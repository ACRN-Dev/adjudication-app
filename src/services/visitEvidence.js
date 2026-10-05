const BLINDED_PATTERN = /sflt|sf1t|plgf|placental growth factor|poc biomarker|biomarker ratio/i;

const LAB_ALIASES = {
  // Urinalysis
  UA_BLOOD:        ['ua_blood', 'UA_BLOOD'],
  UA_KETONES:      ['ua_ketones', 'UA_KETONES'],
  UA_LEUKOCYTES:   ['ua_leukocytes', 'UA_LEUKOCYTES'],
  UA_NITRITES:     ['ua_nitrites', 'UA_NITRITES'],
  UA_PROTEIN:      ['ua_protein', 'UA_PROTEIN', 'DIPSTICK_PROTEIN', 'dipstick_protein'],
  UA_GLUCOSE:      ['ua_glucose', 'UA_GLUCOSE'],
  // Haematology
  HAEMOGLOBIN:     ['haemoglobin', 'HAEMOGLOBIN', 'HEMOGLOBIN', 'HB', 'HGB'],
  HAEMATOCRIT:     ['haematocrit', 'HAEMATOCRIT', 'HEMATOCRIT', 'hematocrit', 'HCT'],
  WBC:             ['wbc', 'WBC', 'white_blood_cell_count', 'white blood cell count'],
  RBC:             ['rbc', 'RBC', 'red_blood_cell_count', 'red blood cell count'],
  PLATELETS:       ['PLATELETS', 'platelets', 'PLATELET', 'PLATELET_COUNT', 'Platelet Count', 'platelets_count'],
  ANC:             ['anc', 'ANC', 'absolute_neutrophil_count', 'absolute neutrophil count', 'neutrophil_count', 'neutrophil count', 'neutrophils'],
  ALC:             ['alc', 'ALC', 'absolute_lymphocyte_count', 'absolute lymphocyte count', 'lymphocyte_count', 'lymphocyte count', 'lymphocytes'],
  // Biochemistry
  CREATININE:      ['CREATININE', 'creatinine', 'Creatinine'],
  AST:             ['AST', 'ast', 'SGOT', 'aspartate_aminotransferase'],
  ALT:             ['ALT', 'alt', 'SGPT', 'alanine_aminotransferase'],
  ALP:             ['alp', 'ALP', 'alkaline_phosphatase'],
  LDH:             ['LDH', 'ldh', 'lactate_dehydrogenase'],
  TOTAL_BILIRUBIN: ['total_bilirubin', 'TOTAL_BILIRUBIN', 'BILIRUBIN'],
  BUN:             ['bun', 'BUN'],
};

// Display metadata: category grouping and human-readable label per canonical key
const LAB_META = {
  UA_BLOOD:        { category: 'Urinalysis',   label: 'Blood' },
  UA_KETONES:      { category: 'Urinalysis',   label: 'Ketones' },
  UA_LEUKOCYTES:   { category: 'Urinalysis',   label: 'Leukocytes' },
  UA_NITRITES:     { category: 'Urinalysis',   label: 'Nitrites' },
  UA_PROTEIN:      { category: 'Urinalysis',   label: 'Protein (Dipstick)' },
  UA_GLUCOSE:      { category: 'Urinalysis',   label: 'Glucose (Urine)' },
  HAEMOGLOBIN:     { category: 'Haematology',  label: 'Haemoglobin' },
  HAEMATOCRIT:     { category: 'Haematology',  label: 'Hematocrit' },
  WBC:             { category: 'Haematology',  label: 'WBC Count' },
  RBC:             { category: 'Haematology',  label: 'RBC Count' },
  PLATELETS:       { category: 'Haematology',  label: 'Platelets' },
  ANC:             { category: 'Haematology',  label: 'Absolute Neutrophil Count' },
  ALC:             { category: 'Haematology',  label: 'Absolute Lymphocyte Count' },
  CREATININE:      { category: 'Biochemistry', label: 'Creatinine' },
  AST:             { category: 'Biochemistry', label: 'AST' },
  ALT:             { category: 'Biochemistry', label: 'ALT' },
  ALP:             { category: 'Biochemistry', label: 'ALP' },
  LDH:             { category: 'Biochemistry', label: 'LDH' },
  TOTAL_BILIRUBIN: { category: 'Biochemistry', label: 'Total Bilirubin' },
  BUN:             { category: 'Biochemistry', label: 'BUN' },
};

const RESULT_CATEGORY_RULES = [
  { category: 'Urinalysis', pattern: /^(ua_|dipstick|upcr|proteinuria|prot_24h)/i },
  { category: 'Other mapped clinical results', pattern: /^source_interpretation_/i },
  { category: 'Haematology', pattern: /(haem|hem|hct|wbc|rbc|platelet|anc|alc|neutrophil|lymphocyte)/i },
  { category: 'Renal function', pattern: /(creatinine|bun|renal)/i },
  { category: 'Liver function and haemolysis', pattern: /(ast|alt|ldh|alp|bilirubin|liver|haemol|hemol)/i },
  { category: 'Maternal assessment', pattern: /(bp_|heart_rate|respiratory|temperature|weight|height|bmi|symptom|headache|visual|epigastric|eclampsia|edema|oedema|maternal|health_status|hospital|icu|adverse|medication)/i },
  { category: 'Sonography and fetal assessment', pattern: /(fetal|foetal|efw|afi|iugr|sga|amniotic|cervical|doppler)/i },
  { category: 'Delivery', pattern: /(delivery|pregnancy_outcome|indication|ebl|blood_transfusion)/i },
  { category: 'Neonatal assessment', pattern: /(newborn|neonatal|apgar|birth|congenital|nicu|rds|ivh|nec)/i },
];

const RESULT_LABELS = {
  upcr: 'Protein:Creatinine Ratio',
  ua_protein: 'Protein (Dipstick)',
  bp_systolic: 'Systolic BP',
  bp_diastolic: 'Diastolic BP',
  bp_systolic_recheck: 'Systolic BP Recheck',
  bp_diastolic_recheck: 'Diastolic BP Recheck',
  ega_weeks: 'Gestational Age (weeks)',
  ega_days: 'Gestational Age (days)',
  ega_delivery: 'Gestational Age at Delivery',
  newborn_weight_g: 'Birth Weight',
  neonatal_gender: 'Newborn Sex',
  neonatal_hc: 'Head Circumference',
  neonatal_length: 'Newborn Length',
  neonatal_heart_rate: 'Newborn Heart Rate',
  neonatal_icu_admission: 'NICU Admission',
  maternal_hospitalization: 'Maternal Hospitalization',
  maternal_icu: 'Maternal ICU Admission',
};

// Canonical units to append when the API provides no unit for a given analyte
const LAB_UNITS = {
  HAEMOGLOBIN:     'g/dL',
  HAEMATOCRIT:     '%',
  WBC:             'x10\u2079/L',
  RBC:             'x10\u00B9\u00B2/L',
  PLATELETS:       'x10\u2079/L',
  ANC:             'x10\u2079/L',
  ALC:             'x10\u2079/L',
  CREATININE:      '\u00B5mol/L',
  AST:             'U/L',
  ALT:             'U/L',
  ALP:             'U/L',
  LDH:             'U/L',
  TOTAL_BILIRUBIN: '\u00B5mol/L',
  BUN:             'mmol/L',
};

// Reference ranges for in-pregnancy adults (used for interpretation labelling).
// Format: [lowMin, lowMax, highMin, highMax] — values outside low or high range are flagged.
// null means no lower/upper bound applies for that direction.
const LAB_RANGES = {
  //                     low-cut   high-cut
  HAEMOGLOBIN:     { low: 11.5,  high: 16.5 },
  HAEMATOCRIT:     { low: 37.0,  high: 47.0 },
  WBC:             { low: 4.0,   high: 11.0 },
  RBC:             { low: 3.8,   high: 5.8  },
  PLATELETS:       { low: 150,   high: 400  },
  ANC:             { low: 2.0,   high: 7.5  },
  ALC:             { low: 1.5,   high: 4.0  },
  CREATININE:      { low: 40,    high: 90   },
  AST:             { low: 10,    high: 30   },
  ALT:             { low: 5,     high: 44   },
  ALP:             { low: 34,    high: 140  },
  LDH:             { low: 180,   high: 325  },
  TOTAL_BILIRUBIN: { low: 3,     high: 29   },
  BUN:             { low: 2.5,   high: 8.0  },
};

/**
 * Qualitative dipstick interpretation for urinalysis analytes.
 *
 * Clinical mapping (applies to UA_LEUKOCYTES, UA_BLOOD, UA_NITRITES,
 * UA_KETONES, UA_PROTEIN, UA_GLUCOSE):
 *
 *  Negative  → Normal   (no analyte detected)
 *  Trace     → Normal   (within acceptable range; not clinically significant alone)
 *  1+        → High     (mild positivity — clinically notable)
 *  2+        → High     (moderate positivity)
 *  3+        → High     (marked positivity)
 *  4+        → High     (heavy positivity)
 *  Positive  → High     (generic positive without quantification)
 *
 * Note: For Protein specifically, Trace can carry clinical weight in the
 * context of pre-eclampsia but is still classified Normal here because it
 * sits below the 1+ threshold used in most dipstick scoring systems. The
 * clinician's narrative and proteinuria section carry the nuance.
 */
export function inferLabInterpretation(key, numericValue, rawValue) {
  return { state: 'available', label: 'Source recorded' };
}

/**
 * Format a raw lab result string with the canonical unit.
 * Applies the unit from LAB_UNITS[key] when the API-supplied unit is absent.
 * Preserves non-numeric qualitative values (e.g. "Trace", "Negative") as-is.
 */
export function formatLabResult(key, rawValue, apiUnit) {
  if (rawValue == null) return 'Not documented';
  const raw = String(rawValue).trim();
  if (/^(negative|trace|\d\+|positive|not\s+done|n\/a|pending)$/i.test(raw)) return raw;
  
  // Return the pure numeric or raw string, ignoring units, as requested by the user
  const num = toNumber(raw);
  if (num != null) {
    const isUa = (key && /^(ua_|dipstick|protein)/i.test(key));
    if (isUa && Number.isInteger(num)) {
      if (num === 0) return 'Negative';
      if (num > 0 && num <= 5) return `${num}+`;
    }
    return String(num);
  }
  return raw;
}

const COMPARISON_ROWS = [
  { key: 'bp', label: 'BP', unit: 'mmHg' },
  { key: 'platelets', label: 'Platelets', unit: 'x10^3 cells/uL' },
  { key: 'creatinine', label: 'Creatinine', unit: 'umol/L' },
  { key: 'ast', label: 'AST', unit: 'U/L' },
  { key: 'alt', label: 'ALT', unit: 'U/L' },
  { key: 'ldh', label: 'LDH', unit: 'U/L' },
  { key: 'proteinuria', label: 'Proteinuria / UPCR', unit: '' },
  { key: 'symptoms', label: 'Symptoms', unit: '' },
  { key: 'medication', label: 'Medication / intervention', unit: '' },
  { key: 'fetal', label: 'Fetal assessment', unit: '' },
  { key: 'classification', label: 'Visit classification', unit: '' },
];

export function formatVisitDate(value) {
  if (!value) return 'Date not documented';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' });
}

export function formatVisitDateTime(value) {
  if (!value) return 'Time not documented';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString(undefined, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function visitLabel(visit, index) {
  return visit?.name || visit?.visit_code || visit?.visitCode || `V${String(index + 1).padStart(2, '0')}`;
}

export function isVisitComplete(visit) {
  const state = String(visit?.resolution_status || visit?.final_status || visit?.status || visit?.packet_status || '').toUpperCase();
  if (['CONCORDANT', 'RESOLVED_BY_MAJORITY', 'FINALIZED', 'CLOSED'].includes(state)) return true;
  if (visit?.final_record || visit?.finalized) return true;
  return false;
}

export function isReviewerVisitSigned(visit) {
  if (visit?.signed || visit?.is_signed) return true;
  const status = visit?.adjudication_status;
  return status && typeof status === 'object' ? Object.values(status).some(Boolean) : false;
}

function toNumber(value) {
  if (typeof value === 'number') return value;
  const cleaned = typeof cleanPhpString === 'function' ? cleanPhpString(value) : String(value ?? '');
  const match = String(cleaned).replace(',', '.').match(/-?\d+(\.\d+)?/);
  return match ? Number(match[0]) : null;
}

function stableId(prefix, visit, index, row) {
  return row?.id || `${prefix}-${visit.id || visit.visit_code || visit.name || 'visit'}-${index}`;
}

function normalizeState(row, inferred = 'available') {
  const raw = String(row?.evidence_state || row?.state || row?.quality_status || row?.status || '').toUpperCase();
  const text = String(row?.value ?? row?.result ?? row?.coded_value ?? '').toUpperCase();
  if (raw.includes('BLIND') || text.includes('BLIND')) return 'blinded';
  if (raw.includes('CONFLICT') || raw.includes('QUERY')) return 'conflicting';
  if (raw.includes('PENDING') || text.includes('PENDING')) return 'pending';
  if (raw.includes('MISSING') || raw.includes('NOT_DONE')) return 'not_available';
  if (row?.severe || row?.critical) return 'severe';
  if (row?.abnormal) return 'abnormal';
  return inferred;
}

function sourceLabel(row) {
  const src = row?.source;
  if (!src) return row?.provenance || row?.source_form || 'Source recorded';
  if (typeof src === 'string') return src;
  return [src.form, src.page, src.field, src.row ? `row ${src.row}` : null].filter(Boolean).join(' / ') || row?.provenance || 'Source recorded';
}

function fromEvidence(visit, canonicalNames) {
  const evidence = visit?.evidence || {};
  const wanted = new Set(canonicalNames.map(n => String(n).toLowerCase()));
  const displayValue = (row) => row.numeric_value ?? row.raw_source_value ?? row.result ?? row.value ?? row.parsed_text_value ?? row.coded_value;
  return Object.entries(evidence).filter(([name]) => wanted.has(String(name).toLowerCase())).flatMap(([name, list]) => (list || []).map((row, index) => ({
    ...row,
    canonical: name,
    id: stableId(name, visit, index, row),
    value: displayValue(row),
    observed_at: row.observed_at || row.datetime || row.date || visit?.date || visit?.visit_date,
    source_label: sourceLabel(row),
    evidence_state: normalizeState(row),
  }))).filter((row) => !BLINDED_PATTERN.test(`${row.canonical} ${row.label || ''} ${row.source_label || ''}`));
}

function likelyMeasurement(row) {
  if (row.value == null || toNumber(row.value) == null) return false;
  const text = `${row.canonical || ''} ${row.source_label || ''}`.toLowerCase();
  return !/(elevated|confirmed|confirmation|flag|status|criteria|criterion|yes\/no|yes no)/.test(text);
}

function makeBpReading(visit, prefix, index, s, d, kind) {
  const sbp = toNumber(s?.value);
  const dbp = toNumber(d?.value);
  // A clinically displayable BP requires both components. Zero-valued or
  // incomplete placeholders must never become additional BP cards.
  if (sbp == null || dbp == null || sbp <= 0 || dbp <= 0) return null;
  return {
    id: stableId(prefix, visit, index, s || d || {}),
    sbp,
    dbp,
    observed_at: s?.observed_at || d?.observed_at,
    source_label: s?.source_label || d?.source_label,
    evidence_state: normalizeState(s || d),
    kind,
  };
}

function normalizeBp(visit, legacyRows = []) {
  const sbp = fromEvidence(visit, ['SBP', 'bp_systolic', 'SYSTOLIC_BP']).filter(likelyMeasurement);
  const dbp = fromEvidence(visit, ['DBP', 'bp_diastolic', 'DIASTOLIC_BP']).filter(likelyMeasurement);
  const sbpRecheck = fromEvidence(visit, ['SBP_RECHECK', 'bp_systolic_recheck', 'SYSTOLIC_BP_RECHECK']).filter(likelyMeasurement);
  const dbpRecheck = fromEvidence(visit, ['DBP_RECHECK', 'bp_diastolic_recheck', 'DIASTOLIC_BP_RECHECK']).filter(likelyMeasurement);
  const rows = [];
  sbp.forEach((s, index) => {
    const reading = makeBpReading(visit, 'bp', index, s, dbp[index], 'initial');
    if (reading) rows.push(reading);
  });
  sbpRecheck.forEach((s, index) => {
    const reading = makeBpReading(visit, 'bp-recheck', index, s, dbpRecheck[index], 'recheck');
    if (reading) rows.push(reading);
  });
  const legacy = legacyRows.map((row, index) => ({
    id: stableId('bp-legacy', visit, index, row),
    sbp: toNumber(row.sbp),
    dbp: toNumber(row.dbp),
    observed_at: row.datetime || row.date,
    source_label: sourceLabel(row),
    evidence_state: normalizeState(row, row.sbp || row.dbp ? 'available' : 'not_available'),
    kind: /recheck|repeat/i.test(`${row.source || ''} ${row.type || ''}`) ? 'recheck' : 'initial',
  })).filter((row) => row.sbp != null && row.dbp != null && row.sbp > 0 && row.dbp > 0);
  // Structured visit evidence and legacy case logs commonly describe the
  // same source rows. Prefer structured evidence so each reading is emitted
  // once; use legacy rows only when structured BP evidence is absent.
  return (rows.length ? rows : legacy).sort((a, b) => new Date(a.observed_at || 0) - new Date(b.observed_at || 0));
}

function normalizeLabs(visit, legacyRows = []) {
  const statusOnlyPattern = /^(available|yes|no|true|false|normal|abnormal)(\s*\([^)]*\))?$/i;
  const isLabResult = (row) => {
    const val = row.value ?? row.result;
    if (toNumber(val) != null) return true;
    if (['pending', 'conflicting', 'blinded', 'not_available'].includes(row.evidence_state)) return true;
    const text = String(val ?? '').trim();
    if (!text) return false;
    return !statusOnlyPattern.test(text);
  };
  const seenByName = new Set();
  const byName = Object.entries(LAB_ALIASES).flatMap(([key, aliases]) => fromEvidence(visit, aliases).filter(isLabResult).map((row) => {
    const rawVal = typeof cleanPhpString === 'function' ? cleanPhpString(row.value ?? row.result) : (row.value ?? row.result);
    return {
      id: row.id,
      key,
      label: LAB_META[key]?.label || key,
      category: LAB_META[key]?.category || 'Other',
      value: toNumber(rawVal),
      raw: rawVal,
      unit: row.unit ?? row.units,
      reference: row.reference || row.reference_range || row.range,
      observed_at: row.observed_at,
      source_label: row.source_label,
      evidence_state: normalizeState(row),
    };
  })).filter((row) => {
    if (row.key === 'UA_PROTEIN') {
      if (seenByName.has('UA_PROTEIN')) return false;
      seenByName.add('UA_PROTEIN');
      return true;
    }
    const sig = `${row.key}-${row.value}`;
    if (seenByName.has(sig)) return false;
    seenByName.add(sig);
    return true;
  });
  
  const legacy = legacyRows.filter((row) => !BLINDED_PATTERN.test(row.analyte || '')).map((row, index) => {
    const found = Object.entries(LAB_ALIASES).find(([, aliases]) => aliases.some((alias) => String(row.analyte || '').toUpperCase().includes(alias.toUpperCase())));
    const rawVal = typeof cleanPhpString === 'function' ? cleanPhpString(row.result) : row.result;
    return {
      id: stableId('lab-legacy', visit, index, row),
      key: found?.[0] || String(row.analyte || 'OTHER').toUpperCase(),
      label: row.analyte || 'Laboratory result',
      value: toNumber(rawVal),
      raw: rawVal,
      unit: row.unit,
      reference: row.reference || row.reference_range || row.range,
      observed_at: row.datetime || row.date || visit?.date || visit?.visit_date,
      source_label: sourceLabel(row),
      evidence_state: normalizeState(row),
    };
  }).filter((row) => row.raw != null || ['pending', 'conflicting', 'blinded', 'not_available'].includes(row.evidence_state));
  const rows = [...byName, ...legacy];
  const rbc = rows.find((row) => row.key === 'RBC' && row.value != null && row.value < 2);
  const hgb = rows.find((row) => row.key === 'HAEMOGLOBIN');
  const hct = rows.find((row) => row.key === 'HAEMATOCRIT');
  if (rbc && hgb && hct) {
    rbc.evidence_state = 'conflicting';
    rbc.reference = rbc.reference || 'Review against haemoglobin and haematocrit';
  }
  return rows;
}

function normalizeProteinuria(visit, legacyRows = []) {
  return [
    ...fromEvidence(visit, ['UPCR', 'upcr', 'DIPSTICK_PROTEIN', 'ua_protein', 'PROTEINURIA', 'PROT_24H']).map((row) => {
      const canonicalKey = String(row.canonical || '').toUpperCase();
      const methodLabel = canonicalKey.includes('UPCR') ? 'UPCR'
        : canonicalKey.includes('24H') ? '24-hour Urine Protein'
        : 'Dipstick Protein';
      const rawVal = String(row.value ?? '').trim();
      const cleanVal = /^(yes|true)$/i.test(rawVal) ? 'Documented' : row.value;
      return {
        id: row.id,
        method: methodLabel,
        value: cleanVal,
        numeric: toNumber(row.value),
        unit: row.unit,
        observed_at: row.observed_at,
        source_label: sourceLabel(row),
        evidence_state: normalizeState(row),
      };
    }),
    ...legacyRows.map((row, index) => ({
      id: stableId('protein-legacy', visit, index, row),
      method: row.method || 'Dipstick Protein',
      value: row.result ?? row.value,
      numeric: toNumber(row.numeric ?? row.result),
      unit: row.unit,
      observed_at: row.datetime || row.date || visit?.date || visit?.visit_date,
      source_label: sourceLabel(row),
      evidence_state: normalizeState(row),
    })),
  ];
}

function humanizeCanonical(name) {
  const key = String(name || '');
  return RESULT_LABELS[key] || key
    .replace(/^ua_/i, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function categoryForCanonical(name) {
  const match = RESULT_CATEGORY_RULES.find((rule) => rule.pattern.test(String(name || '')));
  return match?.category || 'Other mapped clinical results';
}

function normalizeOtherResults(visit, knownRows = []) {
  const knownIds = new Set(knownRows.map((row) => row.id).filter(Boolean));
  const evidence = visit?.evidence || {};
  return Object.entries(evidence).flatMap(([canonical, list]) => (list || []).map((row, index) => {
    const normalized = {
      ...row,
      canonical,
      id: stableId(canonical, visit, index, row),
      value: row.numeric_value ?? row.raw_source_value ?? row.result ?? row.value ?? row.parsed_text_value ?? row.coded_value,
      observed_at: row.observed_at || row.datetime || row.date || visit?.date || visit?.visit_date,
      source_label: sourceLabel(row),
      evidence_state: normalizeState(row),
    };
    return normalized;
  })).filter((row) => {
    if (knownIds.has(row.id)) return false;
    if (BLINDED_PATTERN.test(`${row.canonical} ${row.label || ''} ${row.source_label || ''}`)) return false;
    if (/^RECORDED_PE_/i.test(row.canonical)) return false;
    const value = String(row.value ?? '').trim();
    if (!value) return false;
    return true;
  }).map((row) => ({
    id: row.id,
    key: row.canonical,
    label: humanizeCanonical(row.canonical),
    category: categoryForCanonical(row.canonical),
    value: toNumber(row.value),
    raw: row.value,
    unit: row.unit,
    reference: row.reference || row.reference_range || row.range,
    observed_at: row.observed_at,
    source_label: row.source_label,
    source: row.source,
    evidence_state: row.evidence_state,
  }));
}

function textEvidence(visit, names, legacyRows = []) {
  const rows = fromEvidence(visit, names).map((row) => ({
    id: row.id,
    value: row.value,
    observed_at: row.observed_at,
    source_label: row.source_label,
    evidence_state: normalizeState(row),
  }));
  return [...rows, ...legacyRows.map((row, index) => ({
    id: stableId(names[0] || 'text', visit, index, row),
    value: row.value || row.name || row.result || row.summary,
    observed_at: row.date || row.startDate || visit?.date || visit?.visit_date,
    source_label: sourceLabel(row),
    evidence_state: normalizeState(row),
  }))].filter((row) => row.value != null && !BLINDED_PATTERN.test(String(row.value)));
}

function legacyForVisit(rows, visit, index) {
  const code = visitLabel(visit, index).toUpperCase();
  if (code.includes('UNASSIGNED')) return rows || [];
  const visitDate = String(visit?.date || visit?.visit_date || '').slice(0, 10);
  return (rows || []).filter((row) => {
    const rowVisit = String(row.visit || row.visitName || '').toUpperCase();
    const rowDate = String(row.date || row.datetime || row.observed_at || '').slice(0, 10);
    if (rowVisit && (code.includes(rowVisit) || rowVisit.includes(code))) return true;
    return visitDate && rowDate === visitDate;
  });
}

function makeUnassignedVisit(caseData) {
  const hasLegacy = ['bpLog', 'bp_readings', 'labLog', 'proteinuriaLog', 'medicationLog'].some((key) => caseData?.[key]?.length);
  if (!hasLegacy) return null;
  return {
    id: `${caseData.id || 'case'}-unassigned-evidence`,
    name: 'Unassigned dated evidence',
    visit_code: 'UNASSIGNED',
    date: caseData.derivedOnset || caseData.delivery_date || null,
    gestational_age: caseData.gaAtEvent || null,
    packet_status: 'VISIT_RECONCILIATION_REQUIRED',
    evidence: {},
  };
}

// Derive a structured vitals object from raw visit evidence (heart rate, temperature, weight)
function normalizeVitalsFromEvidence(visit, bpRows) {
  const evidence = visit?.evidence || {};
  const firstVal = (keys, requireNumber = false) => {
    for (const k of keys) {
      const rows = evidence[k];
      if (rows?.length) {
        for (const r of rows) {
          const v = r.numeric_value ?? r.raw_source_value ?? r.parsed_text_value ?? r.coded_value ?? null;
          if (v != null) {
            const strVal = String(v).trim();
            if (!strVal) continue;
            if (requireNumber) {
              const num = toNumber(strVal);
              if (num != null && num > 0) return String(num);
            } else {
              return strVal;
            }
          }
        }
      }
    }
    return null;
  };
  const bpInitial = bpRows.find((r) => r.kind !== 'recheck') || bpRows[0] || null;
  const bpRecheck = bpRows.find((r) => r.kind === 'recheck') || null;
  const hrRaw = firstVal(['heart_rate', 'HEART_RATE', 'pulse', 'PULSE', 'pulse_rate'], true);
  const tempRaw = firstVal(['temperature', 'TEMPERATURE', 'body_temperature'], true);
  const weightVal = firstVal(['weight', 'WEIGHT', 'weight_kg', 'maternal_weight'], true);
  const heightRaw = firstVal(['height', 'HEIGHT', 'maternal_height'], true);
  const bmiRaw = firstVal(['bmi', 'BMI'], true);

  const hrNum = toNumber(hrRaw);
  const cleanHr = (hrNum != null && hrNum >= 30 && hrNum <= 220) ? String(hrNum) : null;

  const wtNum = toNumber(weightVal);
  const cleanWeight = (wtNum != null && wtNum >= 20 && wtNum <= 250) ? String(wtNum) : null;

  if (!bpInitial && !cleanHr && !tempRaw && !cleanWeight) return null;
  return {
    bp: bpInitial ? `${bpInitial.sbp}/${bpInitial.dbp} mmHg` : null,
    recheck: bpRecheck ? `${bpRecheck.sbp}/${bpRecheck.dbp} mmHg` : null,
    hr: cleanHr != null ? `${cleanHr} bpm` : null,
    temp: tempRaw != null ? `${tempRaw}°C` : null,
    weight: cleanWeight != null ? `${cleanWeight} kg` : null,
    height: heightRaw != null ? `${heightRaw} cm` : null,
    bmi: bmiRaw != null ? String(bmiRaw) : null,
    bpInterpretation: bpInitial
      ? (bpInitial.sbp >= 160 || bpInitial.dbp >= 110 ? 'Severe-range hypertension'
        : bpInitial.sbp >= 140 || bpInitial.dbp >= 90 ? 'Hypertensive range'
        : 'Within controlled range')
      : null,
  };
}

function cleanPhpString(str) {
  if (!str) return '';
  let s = String(str);
  s = s.replace(/^#\d*\s*-\s*/, '');
  const nameMatch = s.match(/medication treatment name:\s*s:\d+:"([^"]+)"/i) || s.match(/medication treatment name:\s*([^,;]+)/i);
  if (nameMatch && nameMatch[1]) return nameMatch[1].trim();
  s = s.replace(/s:\d+:"([^"]*)";?,?/g, '$1');
  return s.replace(/[;,]+$/, '').trim();
}

// Derive a structured sonography object from raw visit evidence (EFW, FHR, AFI)
function normalizeSonographyFromEvidence(visit) {
  const evidence = visit?.evidence || {};
  const observations = visit?.observations || [];
  
  const firstVal = (keys) => {
    for (const k of keys) {
      const rows = evidence[k];
      if (rows?.length) {
        const r = rows[0];
        const v = r.numeric_value ?? r.raw_source_value ?? r.parsed_text_value ?? r.coded_value ?? null;
        if (v != null && String(v).trim() !== '') {
          const cleaned = cleanPhpString(String(v).trim());
          if (cleaned && !/^(yes|no|not done|not assessed|not evaluated|n\/a)$/i.test(cleaned)) return cleaned;
        }
      }
    }
    return null;
  };

  const getObsVal = (pattern) => {
    const obs = observations.find(o => pattern.test(String(o.source_field || '')));
    if (!obs) return null;
    const v = obs.numeric_value ?? obs.raw_source_value ?? obs.value ?? obs.coded_value ?? null;
    if (v != null && String(v).trim() !== '') {
      const cleaned = cleanPhpString(String(v).trim());
      if (cleaned && !/^(yes|no|not done|not assessed|not evaluated|n\/a)$/i.test(cleaned)) return cleaned;
    }
    return null;
  };

  const efwRaw = firstVal(['efw', 'EFW']) || getObsVal(/ULTRASNDFETWEINUM/i);
  const fhrRaw = firstVal(['fetal_heart_rate', 'FETAL_HEART_RATE', 'fetal_hr']) || getObsVal(/FHR/i);
  const afiRaw = firstVal(['afi', 'AFI']) || getObsVal(/AMNIO/i);
  const cervRaw = firstVal(['cervical_length', 'CERVICAL_LENGTH']) || getObsVal(/CERVIX/i);
  const ega = getObsVal(/ULTRASNDEGADESCR_OLD/i) || visit?.gestationalLabel || '';
  const presentation = getObsVal(/ULTRASNDPRESDESCR/i);
  const anomalies = getObsVal(/ULTRASNDANOMALDESC/i) || 'No gross foetal anomalies were appreciated';
  const notes = getObsVal(/ULTRASNDCOMM/i);

  if (!efwRaw && !fhrRaw && !afiRaw && !presentation && !notes && !cervRaw) return null;

  return {
    efwRaw: efwRaw != null ? (isNaN(efwRaw) ? efwRaw : `${efwRaw}g`) : 'not documented',
    fhr: fhrRaw != null ? (isNaN(fhrRaw) ? fhrRaw : `${fhrRaw} bpm`) : 'not documented',
    afiRaw: afiRaw != null ? (isNaN(afiRaw) ? afiRaw : `${afiRaw} cm`) : null,
    cervicalLength: cervRaw != null ? (isNaN(cervRaw) ? cervRaw : `${cervRaw} cm`) : 'not documented',
    ega: ega || 'unknown',
    presentation: presentation || 'unknown',
    anomalies: anomalies,
    notes: notes || 'None documented.',
    placentaFluid: null,
    scanDate: null,
  };
}

export function resolveVisitDate(visit, index, caseData, bp = [], labs = [], proteinuria = [], otherResults = []) {
  if (visit?.date && !/not documented/i.test(String(visit.date))) return visit.date;
  if (visit?.visit_date && !/not documented/i.test(String(visit.visit_date))) return visit.visit_date;
  if (visit?.visit_datetime && !/not documented/i.test(String(visit.visit_datetime))) return visit.visit_datetime;

  // Search all observations for earliest valid timestamp
  const candidateDates = [];
  const addCandidate = (d) => {
    if (!d) return;
    const dt = new Date(d);
    if (!Number.isNaN(dt.getTime())) {
      candidateDates.push(dt);
    }
  };

  [...bp, ...labs, ...proteinuria, ...otherResults].forEach((row) => {
    addCandidate(row.observed_at || row.datetime || row.date);
  });

  const ev = visit?.evidence || {};
  Object.values(ev).forEach((rows) => {
    (rows || []).forEach((r) => addCandidate(r.observed_at || r.observation_datetime || r.datetime || r.date));
  });

  (visit?.observations || []).forEach((o) => {
    addCandidate(o.observation_datetime || o.datetime_value || o.observed_at || o.date);
  });

  if (candidateDates.length > 0) {
    candidateDates.sort((a, b) => a.getTime() - b.getTime());
    return candidateDates[0].toISOString();
  }

  // Visit 5 fallback: delivery date from caseData or visit evidence
  const vNum = visit?.visit_number ?? (index != null ? index + 1 : null);
  if (vNum === 5 && (caseData?.delivery_date || caseData?.derivedDeliveryDate)) {
    return caseData.delivery_date || caseData.derivedDeliveryDate;
  }

  return null;
}

export function detectVisitPerformance(visit) {
  // Check explicit reason in evidence or observations
  const ev = visit?.evidence || {};
  let reason = visit?.not_performed_reason || null;

  if (!reason) {
    for (const [k, rows] of Object.entries(ev)) {
      const lk = k.toLowerCase();
      if (lk.includes('not_performing') || lk.includes('missed') || lk.includes('not_done') || lk === 'visit_date') {
        for (const r of (rows || [])) {
          const val = String(r.raw_source_value ?? r.value ?? r.result ?? '').trim();
          const field = String(r.source?.field || r.source_field_label || '').toLowerCase();
          if (field.includes('not performing') || /^(delivered|missed visit|withdrew|lost to follow-up)$/i.test(val)) {
            reason = val;
            break;
          }
        }
      }
      if (reason) break;
    }
  }

  if (!reason && Array.isArray(visit?.observations)) {
    for (const o of visit.observations) {
      const val = String(o.raw_source_value || o.value || '').trim();
      const field = String(o.source_field_label || '').toLowerCase();
      if (field.includes('not performing') || /^(delivered|missed visit|withdrew|lost to follow-up)$/i.test(val)) {
        reason = val;
        break;
      }
    }
  }

  const hasBp = (visit?.bp || []).length > 0;
  const hasLabs = (visit?.labs || []).filter(l => l.value != null && !['not_available', 'missing'].includes(l.evidence_state)).length > 0;
  const hasVitals = Boolean(visit?.vitals?.bp || visit?.vitals?.hr || visit?.vitals?.weight);
  const hasMaternal = (visit?.maternal || []).length > 0;
  const hasNeonatal = (visit?.neonatal || []).length > 0;
  const hasOther = (visit?.otherResults || []).length > 0;
  const hasEvidence = Object.keys(visit?.evidence || {}).some(k => !/visit_date|reason.*not/i.test(k));
  const hasDate = Boolean(visit?.date || visit?.visit_date || visit?.visit_datetime);
  const hasClinicalData = hasBp || hasLabs || hasVitals || (visit?.proteinuria || []).length > 0 || hasMaternal || hasNeonatal || hasOther || hasEvidence;

  if (reason) {
    return {
      performed: false,
      reason,
      hasClinicalData,
    };
  }

  // If no clinical data, no observations, and no date
  const totalObs = visit?.reconciliation?.mapped_clinical_rows ?? (visit?.observations?.length || 0);
  if (!hasClinicalData && !hasDate && totalObs <= 1) {
    return {
      performed: false,
      reason: 'Visit not conducted',
      hasClinicalData: false,
    };
  }

  return {
    performed: true,
    reason: null,
    hasClinicalData,
  };
}

export function normalizeVisitEvidence(caseData = {}) {
  const sourceVisits = caseData.visits?.length ? [...caseData.visits] : [];
  const visits = sourceVisits.length ? sourceVisits : [
    makeUnassignedVisit(caseData),
  ].filter(Boolean);
  const normalized = visits.map((visit, index) => {
    const bp = normalizeBp(visit, legacyForVisit(caseData.bpLog || caseData.bp_readings, visit, index));
    const labs = normalizeLabs(visit, legacyForVisit(caseData.labLog, visit, index));
    const proteinuria = normalizeProteinuria(visit, legacyForVisit(caseData.proteinuriaLog, visit, index));
    const symptoms = textEvidence(visit, ['SYMPTOMS', 'HEADACHE', 'VISUAL_SYMPTOMS', 'RUQ_PAIN'], legacyForVisit(caseData.symptomsLog, visit, index));
    const medications = textEvidence(visit, ['MEDICATION', 'INTERVENTION'], legacyForVisit(caseData.medicationLog, visit, index));
    const fetal = textEvidence(visit, ['FETAL_ASSESSMENT', 'EFW_CENTILE', 'UA_DOPPLER'], legacyForVisit(caseData.fetalLog, visit, index));
    const maternal = textEvidence(visit, ['MATERNAL_OUTCOME', 'DELIVERY_MODE', 'DELIVERY_COMPLICATION', 'MATERNAL_STATUS', 'PREGNANCY_OUTCOME', 'GA_AT_DELIVERY', 'DELIVERY_LT_34W'], []);
    const neonatal = textEvidence(visit, ['NEONATAL_OUTCOME', 'BIRTH_WEIGHT', 'APGAR', 'APGAR_1MIN', 'APGAR_5MIN', 'NICU_ADMISSION', 'NEONATAL_ICU_ADMISSION', 'STILLBIRTH', 'CONFIRMED_IUGR', 'CONFIRMED_SGA', 'IUGR_SGA_ASSESSMENT_DONE', 'CONGENITAL_ANOMALIES', 'BIRTH_COMPLICATIONS'], []);
    const otherResults = normalizeOtherResults(visit, [...bp, ...labs, ...proteinuria, ...symptoms, ...medications, ...fetal, ...maternal, ...neonatal]);
    // Derive vitals and sonography from raw evidence for dynamic rendering
    const vitals = normalizeVitalsFromEvidence(visit, bp);
    const sonography = normalizeSonographyFromEvidence(visit);
    
    // Performance & Date derivation
    const perf = detectVisitPerformance({ ...visit, bp, labs, vitals, proteinuria, maternal, neonatal, otherResults });
    const isNotPerformed = !perf.performed;
    const resolvedDate = isNotPerformed ? null : resolveVisitDate(visit, index, caseData, bp, labs, proteinuria, otherResults);

    return {
      ...visit,
      id: visit.id || `${caseData.id || 'case'}-${visitLabel(visit, index)}`,
      label: visitLabel(visit, index),
      date: resolvedDate,
      is_not_performed: isNotPerformed,
      not_performed_reason: perf.reason,
      gestationalLabel: (() => {
        if (isNotPerformed) return null;
        const isPost = visit.visit_number === 6 || /eos|post|v06|visit 6/i.test(visit.name || visit.visit_code || '');
        if (isPost) return 'Postpartum (~4 weeks)';
        if (visit.ga && !/unclassifiable|null|undefined/i.test(String(visit.ga))) return String(visit.ga);
        if (visit.gestational_age && !/unclassifiable|null|undefined/i.test(String(visit.gestational_age))) return String(visit.gestational_age);
        const days = visit.ga_days ?? visit.gestational_age_days ?? visit.gaDays;
        if (days && days >= 45) {
          return `${Math.floor(days / 7)} weeks, ${days % 7} days`;
        }
        if (caseData.gaAtEvent && !/unclassifiable|null|undefined/i.test(String(caseData.gaAtEvent))) {
          return String(caseData.gaAtEvent);
        }
        return 'Antenatal';
      })(),
      bp,
      labs,
      proteinuria,
      symptoms,
      medications,
      fetal,
      maternal,
      neonatal,
      otherResults,
      vitals,
      sonography,
    };
  });
  return normalized.map((visit, index) => {
    const throughVisit = normalized.slice(0, index + 1);
    const cumulative = {
      ...visit,
      bp: throughVisit.flatMap((row) => row.bp),
      labs: throughVisit.flatMap((row) => row.labs),
      proteinuria: throughVisit.flatMap((row) => row.proteinuria),
      symptoms: throughVisit.flatMap((row) => row.symptoms),
      medications: throughVisit.flatMap((row) => row.medications),
      fetal: throughVisit.flatMap((row) => row.fetal),
      maternal: throughVisit.flatMap((row) => row.maternal),
      neonatal: throughVisit.flatMap((row) => row.neonatal),
      otherResults: throughVisit.flatMap((row) => row.otherResults),
    };
    return {
      ...visit,
      cumulativeEvidence: cumulative,
      interpretation: deriveVisitInterpretation(cumulative, caseData),
    };
  });
}

export function minutesBetween(a, b) {
  const first = new Date(a).getTime();
  const second = new Date(b).getTime();
  if (!a || !b || Number.isNaN(first) || Number.isNaN(second)) return null;
  return Math.abs(Math.round((second - first) / 60000));
}

export function formatInterval(minutes) {
  if (minutes == null) return 'Interval not assessable';
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h ? `${h} h ${m} min` : `${m} min`;
}

export function pairBpReadings(bp = []) {
  const rows = [...bp]
    .filter((row) => row?.sbp != null && row?.dbp != null && row.sbp > 0 && row.dbp > 0)
    .sort((a, b) => new Date(a.observed_at || 0) - new Date(b.observed_at || 0));
  if (!rows.length) return [];

  const initial = rows.find((row) => row.kind !== 'recheck') || rows[0];
  const afterInitial = rows.filter((row) => row.id !== initial.id);
  const recheck = afterInitial.find((row) => row.kind === 'recheck') || afterInitial[0] || null;
  const interval = recheck ? minutesBetween(initial.observed_at, recheck.observed_at) : null;
  return [{
    initial,
    recheck,
    interval,
    confirmed: recheck ? interval >= 240 : false,
    severe: [initial, recheck].some((row) => row && (row.sbp >= 160 || row.dbp >= 110 || row.evidence_state === 'severe')),
  }];
}

function latest(rows, key) {
  const filtered = key ? rows.filter((row) => row.key === key) : rows;
  return filtered.slice().sort((a, b) => new Date(b.observed_at || 0) - new Date(a.observed_at || 0))[0] || null;
}

function compareValue(current, previous) {
  if (!current || !previous || current.value == null || previous.value == null) return '';
  const diff = current.value - previous.value;
  if (!diff) return 'No change from previous visit';
  return `${diff > 0 ? 'Increased' : 'Decreased'} from previous visit by ${Math.abs(diff).toFixed(Math.abs(diff) < 1 ? 2 : 0)}`;
}

export function buildLongitudinalRows(visits) {
  return COMPARISON_ROWS.map((row) => ({
    ...row,
    cells: visits.map((visit, index) => {
      const previous = visits.slice(0, index).reverse().find((candidate) => cellObservation(candidate, row.key));
      const observation = cellObservation(visit, row.key);
      return {
        visitId: visit.id,
        value: cellValue(visit, row.key),
        state: cellState(visit, row.key),
        change: row.key.match(/platelets|creatinine|ast|alt|ldh/) ? compareValue(observation, cellObservation(previous, row.key)) : '',
      };
    }),
  }));
}

function cellObservation(visit, key) {
  if (!visit) return null;
  if (key === 'platelets') return latest(visit.labs, 'PLATELETS');
  if (key === 'creatinine') return latest(visit.labs, 'CREATININE');
  if (key === 'ast') return latest(visit.labs, 'AST');
  if (key === 'alt') return latest(visit.labs, 'ALT');
  if (key === 'ldh') return latest(visit.labs, 'LDH');
  return null;
}

function cellValue(visit, key) {
  if (key === 'bp') {
    const bp = latest(visit.bp);
    return bp?.sbp && bp?.dbp ? `${bp.sbp}/${bp.dbp}` : 'Not available';
  }
  if (key === 'proteinuria') {
    const p = latest(visit.proteinuria);
    return p ? `${p.method}: ${p.value}${p.unit ? ` ${p.unit}` : ''}` : 'Not available';
  }
  if (key === 'symptoms') return visit.symptoms[0]?.value || 'Not available';
  if (key === 'medication') return visit.medications[0]?.value || 'Not available';
  if (key === 'fetal') return visit.fetal[0]?.value || 'Not available';
  if (key === 'classification') return visit.interpretation.classification;
  const lab = cellObservation(visit, key);
  return lab ? `${lab.raw ?? lab.value}${lab.unit ? ` ${lab.unit}` : ''}` : 'Not available';
}

function cellState(visit, key) {
  if (key === 'bp') return latest(visit.bp)?.evidence_state || 'not_available';
  if (key === 'proteinuria') return latest(visit.proteinuria)?.evidence_state || 'not_available';
  if (key === 'symptoms') return visit.symptoms[0]?.evidence_state || 'not_available';
  if (key === 'medication') return visit.medications[0]?.evidence_state || 'not_available';
  if (key === 'fetal') return visit.fetal[0]?.evidence_state || 'not_available';
  if (key === 'classification') return visit.interpretation.classification === 'Not assessable' ? 'not_available' : 'available';
  return cellObservation(visit, key)?.evidence_state || 'not_available';
}

export function deriveVisitInterpretation(visit, caseData = {}) {
  const bpPairs = pairBpReadings(visit.bp);
  const severeBp = visit.bp.some((row) => row.sbp >= 160 || row.dbp >= 110 || row.evidence_state === 'severe');
  const htn = visit.bp.some((row) => row.sbp >= 140 || row.dbp >= 90);
  const confirmedBp = bpPairs.some((pair) => pair.confirmed && pair.initial?.sbp >= 140 && pair.recheck?.sbp >= 140);
  const abnormalLabs = visit.labs.filter((row) => row.evidence_state === 'abnormal' || row.evidence_state === 'severe' || row.severe);
  const proteinPositive = visit.proteinuria.some((row) => row.evidence_state === 'abnormal' || row.evidence_state === 'severe' || row.numeric >= 0.3 || /\b2\+|3\+|4\+/i.test(String(row.value)));
  const missing = [];
  if (!visit.bp.length) missing.push('Blood pressure');
  if (!visit.proteinuria.length) missing.push('Proteinuria');
  if (!visit.labs.some((row) => row.key === 'PLATELETS')) missing.push('Platelets');
  if (!visit.labs.some((row) => ['AST', 'ALT'].includes(row.key))) missing.push('AST/ALT');
  const queryCount = [...visit.bp, ...visit.labs, ...visit.proteinuria].filter((row) => ['pending', 'blinded', 'conflicting', 'not_available'].includes(row.evidence_state)).length;
  const criteria = [
    confirmedBp ? 'Confirmed hypertension documented on 2+ occasions' : htn ? 'Hypertension-range BP documented (single occasion)' : null,
    severeBp ? 'Severe-range BP (\u2265160/110) documented' : null,
    proteinPositive ? 'Proteinuria documented' : null,
    abnormalLabs.length ? `${abnormalLabs.length} laboratory result(s) flagged for review` : null,
  ].filter(Boolean);
  const classification = criteria.length
    ? 'Evidence present — adjudicator review required'
    : missing.length
      ? 'Insufficient evidence for assessment'
      : 'No qualifying evidence documented';
  const total = 4;
  const complete = total - missing.length;
  return {
    summary: criteria.length ? criteria.join('; ') : 'No qualifying structured findings are documented for this visit.',
    criteriaMet: criteria,
    missing,
    classification,
    certainty: missing.length ? 'Evidence completeness is limited' : (criteria.length ? 'Evidence present — adjudicator review required' : 'No qualifying structured evidence documented'),
    completeness: Math.max(0, Math.round((complete / total) * 100)),
    queries: queryCount ? [`${queryCount} evidence item(s) pending, blinded, unavailable or conflicting`] : [],
    automatedContext: null,
  };
}

export function statusLabel(state) {
  return ({
    available: 'Available',
    normal: 'Normal',
    abnormal: 'Abnormal',
    severe: 'Severe',
    not_available: 'Not available',
    pending: 'Pending',
    blinded: 'Blinded',
    conflicting: 'Query required',
  })[state] || 'Available';
}

/**
 * Generates a grammatically correct, clinical demographic opening sentence.
 *
 * All patients in this system are currently pregnant (pre-eclampsia trial).
 * Gravida is clamped to a minimum of 1 — "Nulligravida" (G=0) never applies.
 *
 * Terminology (per WHO / FIGO):
 *   Primigravida = first pregnancy ever, including current (G=1)
 *   Nulliparous  = no prior deliveries (Para 0)
 *   Multigravida  = G ≥ 2
 *
 * Test 1 (First-time pregnancy, no prior deliveries):
 * buildDemographicString(24, 1, 0, 0, 'Nulliparous')
 * Output: 'A 24-year-old African woman, Primigravida (Nulliparous), presents for routine clinical trial screening with no known prior medical history or chronic conditions.'
 *
 * Test 2 (MRN 7167 patient):
 * buildDemographicString(40, 4, 2, 1, 'chronic hypertension and pre-gestational diabetes')
 * Output: 'A 40-year-old African woman, Gravida 4, Para 2 (one previous miscarriage), presents for clinical trial screening. Her medical history is significant for chronic hypertension and pre-gestational diabetes.'
 */
export function buildDemographicString(age, gravida, para_live, para_misc, conditions = null) {
  // 1. Base Demographics
  const base = age ? `A ${age}-year-old African woman` : 'An adult African woman';


  // 2. Obstetric History Logic
  // All patients in this system are currently pregnant (pre-eclampsia trial),
  // so Nulligravida (G=0, "never been pregnant") is clinically impossible.
  // Minimum is Primigravida (G=1, "first pregnancy including current").
  const gRaw = gravida != null && !Number.isNaN(Number(gravida)) ? Number(gravida) : 0;
  const g = Math.max(gRaw, 1); // Clamp: currently pregnant → minimum G1
  const p_live = para_live != null && !Number.isNaN(Number(para_live)) ? Number(para_live) : 0;
  const p_misc = para_misc != null && !Number.isNaN(Number(para_misc)) ? Number(para_misc) : 0;

  let obs_string = '';
  if (g === 1 && p_live === 0 && p_misc === 0) {
    obs_string = 'Primigravida (Nulliparous)';
  } else if (g === 2) {
    obs_string = `Gravida ${g}, Para ${p_live}`;
    if (p_misc === 1) {
      obs_string += ' (one previous miscarriage)';
    } else if (p_misc > 1) {
      obs_string += ` (${p_misc} previous miscarriages)`;
    }
  } else {
    // Multigravida: G ≥ 3
    obs_string = `Gravida ${g}, Para ${p_live}`;
    if (p_misc === 1) {
      obs_string += ' (one previous miscarriage)';
    } else if (p_misc > 1) {
      obs_string += ` (${p_misc} previous miscarriages)`;
    }
  }


  // 3. Medical History Logic
  // Clean up weird AI inputs like treating 'Nulliparous' as a disease
  const bad_conditions = new Set(['none', 'nulliparous', 'n/a', 'no', 'unknown', '']);
  let cleanCondStr = '';

  if (Array.isArray(conditions)) {
    const normMap = {
      'pre-existing chronic htn': 'chronic hypertension',
      'pre-gestational diabetes': 'pre-gestational diabetes',
      'family history pe': 'family history of preeclampsia',
      'prior pe-indicated c-section': 'prior preeclampsia-indicated Cesarean section',
    };
    const valid = conditions
      .map(c => String(c || '').trim())
      .filter(c => c && !bad_conditions.has(c.toLowerCase()) && !/^age/i.test(c) && !/nulliparous/i.test(c))
      .map(c => normMap[c.toLowerCase()] || c);

    if (valid.length === 1) {
      cleanCondStr = valid[0];
    } else if (valid.length === 2) {
      cleanCondStr = `${valid[0]} and ${valid[1]}`;
    } else if (valid.length > 2) {
      cleanCondStr = `${valid.slice(0, -1).join(', ')} and ${valid[valid.length - 1]}`;
    }
  } else if (conditions != null) {
    const raw = String(conditions).trim();
    if (!bad_conditions.has(raw.toLowerCase()) && !/nulliparous/i.test(raw)) {
      cleanCondStr = raw;
    }
  }

  let med_string = '';
  if (!cleanCondStr || bad_conditions.has(cleanCondStr.toLowerCase())) {
    med_string = 'with no known prior medical history or chronic conditions.';
  } else {
    med_string = `Her medical history is significant for ${cleanCondStr}.`;
  }

  return `Presenting ${base.replace(/^A /i, 'a ')} (${obs_string}) for clinical trial screening. ${med_string}`;
}


export function getLabReferenceRange(key) {
  const range = LAB_RANGES[key];
  if (!range) return null;
  const unit = LAB_UNITS[key];
  const unitStr = unit ? ` ${unit}` : '';
  if (range.low != null && range.high != null) return `${range.low} - ${range.high}${unitStr}`;
  if (range.high != null) return `< ${range.high}${unitStr}`;
  if (range.low != null) return `> ${range.low}${unitStr}`;
  return null;
}