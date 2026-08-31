const BLINDED_PATTERN = /sflt|sf1t|plgf|placental growth factor|poc biomarker|biomarker ratio/i;

const LAB_ALIASES = {
  PLATELETS: ['PLATELETS', 'PLATELET', 'PLATELET_COUNT', 'Platelet Count'],
  CREATININE: ['CREATININE', 'Creatinine'],
  AST: ['AST', 'SGOT'],
  ALT: ['ALT', 'SGPT'],
  LDH: ['LDH'],
};

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
  const match = String(value ?? '').replace(',', '.').match(/-?\d+(\.\d+)?/);
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
  return [src.form, src.field, src.page ? `p.${src.page}` : null].filter(Boolean).join(' / ') || row?.provenance || 'Source recorded';
}

function fromEvidence(visit, canonicalNames) {
  const evidence = visit?.evidence || {};
  const wanted = new Set(canonicalNames);
  const displayValue = (row) => row.numeric_value ?? row.raw_source_value ?? row.result ?? row.value ?? row.parsed_text_value ?? row.coded_value;
  return Object.entries(evidence).filter(([name]) => wanted.has(name)).flatMap(([name, list]) => (list || []).map((row, index) => ({
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
  const sbp = fromEvidence(visit, ['SBP', 'SYSTOLIC_BP']).filter(likelyMeasurement);
  const dbp = fromEvidence(visit, ['DBP', 'DIASTOLIC_BP']).filter(likelyMeasurement);
  const sbpRecheck = fromEvidence(visit, ['SBP_RECHECK', 'SYSTOLIC_BP_RECHECK']).filter(likelyMeasurement);
  const dbpRecheck = fromEvidence(visit, ['DBP_RECHECK', 'DIASTOLIC_BP_RECHECK']).filter(likelyMeasurement);
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
    if (toNumber(row.value) != null) return true;
    if (['pending', 'conflicting', 'blinded', 'not_available'].includes(row.evidence_state)) return true;
    const text = String(row.value ?? '').trim();
    if (!text) return false;
    return !statusOnlyPattern.test(text);
  };
  const byName = Object.entries(LAB_ALIASES).flatMap(([key, aliases]) => fromEvidence(visit, aliases).filter(isLabResult).map((row) => ({
    id: row.id,
    key,
    label: key === 'PLATELETS' ? 'Platelets' : key,
    value: toNumber(row.value),
    raw: row.value,
    unit: row.unit,
    reference: row.reference || row.reference_range || row.range,
    observed_at: row.observed_at,
    source_label: row.source_label,
    evidence_state: normalizeState(row),
  })));
  const legacy = legacyRows.filter((row) => !BLINDED_PATTERN.test(row.analyte || '')).map((row, index) => {
    const found = Object.entries(LAB_ALIASES).find(([, aliases]) => aliases.some((alias) => String(row.analyte || '').toUpperCase().includes(alias.toUpperCase())));
    return {
      id: stableId('lab-legacy', visit, index, row),
      key: found?.[0] || String(row.analyte || 'OTHER').toUpperCase(),
      label: row.analyte || 'Laboratory result',
      value: toNumber(row.result),
      raw: row.result,
      unit: row.unit,
      reference: row.reference || row.reference_range || row.range,
      observed_at: row.datetime || row.date || visit?.date || visit?.visit_date,
      source_label: sourceLabel(row),
      evidence_state: normalizeState(row),
    };
  }).filter((row) => row.raw != null || ['pending', 'conflicting', 'blinded', 'not_available'].includes(row.evidence_state));
  return [...byName, ...legacy];
}

function normalizeProteinuria(visit, legacyRows = []) {
  return [
    ...fromEvidence(visit, ['UPCR', 'DIPSTICK_PROTEIN', 'PROTEINURIA', 'PROT_24H']).map((row) => ({
      id: row.id,
      method: row.canonical,
      value: row.value,
      numeric: toNumber(row.value),
      unit: row.unit,
      observed_at: row.observed_at,
      source_label: row.source_label,
      evidence_state: normalizeState(row),
    })),
    ...legacyRows.map((row, index) => ({
      id: stableId('protein-legacy', visit, index, row),
      method: row.method || 'Proteinuria',
      value: row.result ?? row.value,
      numeric: toNumber(row.numeric ?? row.result),
      unit: row.unit,
      observed_at: row.datetime || row.date || visit?.date || visit?.visit_date,
      source_label: sourceLabel(row),
      evidence_state: normalizeState(row),
    })),
  ];
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
    const maternal = textEvidence(visit, ['MATERNAL_OUTCOME', 'DELIVERY_MODE', 'DELIVERY_COMPLICATION', 'MATERNAL_STATUS'], []);
    const neonatal = textEvidence(visit, ['NEONATAL_OUTCOME', 'BIRTH_WEIGHT', 'APGAR', 'NICU_ADMISSION', 'STILLBIRTH'], []);
    return {
      ...visit,
      id: visit.id || `${caseData.id || 'case'}-${visitLabel(visit, index)}`,
      label: visitLabel(visit, index),
      date: visit.date || visit.visit_date,
      gestationalLabel: visit.ga || visit.gestational_age || (visit.ga_days ? `${Math.floor(visit.ga_days / 7)}+${visit.ga_days % 7}` : caseData.gaAtEvent),
      bp,
      labs,
      proteinuria,
      symptoms,
      medications,
      fetal,
      maternal,
      neonatal,
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
    confirmedBp ? 'Confirmed hypertension' : htn ? 'Hypertension documented, confirmation not assessable in this visit' : null,
    severeBp ? 'Severe-range BP documented' : null,
    proteinPositive ? 'Proteinuria support present' : null,
    abnormalLabs.length ? `${abnormalLabs.length} abnormal laboratory result(s)` : null,
  ].filter(Boolean);
  const classification = severeBp && (proteinPositive || abnormalLabs.length)
    ? 'Pre-eclampsia with severe features support'
    : htn && proteinPositive
      ? 'Pre-eclampsia support'
      : htn
        ? 'Hypertension support'
        : missing.length
          ? 'Not assessable'
          : 'No PE support identified';
  const total = 4;
  const complete = total - missing.length;
  return {
    summary: criteria.length ? criteria.join('; ') : 'No qualifying structured findings are documented for this visit.',
    criteriaMet: criteria,
    missing,
    classification,
    certainty: missing.length ? 'Probable or lower until missing evidence is resolved' : (criteria.length ? 'Definite evidence package for this visit' : 'No qualifying criteria documented'),
    completeness: Math.max(0, Math.round((complete / total) * 100)),
    queries: queryCount ? [`${queryCount} evidence item(s) pending, blinded, unavailable or conflicting`] : [],
    automatedContext: caseData.derivedSubtype ? `${caseData.derivedSubtype} / ${caseData.derivedSeverity || 'severity not assessable'}` : null,
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
