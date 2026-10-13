/**
 * ACRN PROTECT-Africa Adjudication Platform
 * ═══════════════════════════════════════════════════════════════
 * Clinical Narrative Engine v2.0 — Rule-Based Prose Generator
 *
 * Generates two narrative styles from normalised visit evidence:
 *
 *   1. OVERALL SUMMARY  (FORM-ADJ-PROSE-v2.0)
 *      A comprehensive, flowing prose document that synthesises
 *      the full longitudinal clinical course: demographics,
 *      hemodynamic trajectory, proteinuria surveillance,
 *      laboratory investigations, fetal assessment, delivery,
 *      neonatal outcome, evidence gaps, and adjudication framing.
 *
 *   2. PER-VISIT NARRATIVE
 *      A concise, structured clinical presentation per visit
 *      with opening sentence, vitals line, sonographic data
 *      line, lab synopsis, and clinical context — modelled
 *      after the registrar-to-consultant handover format.
 *
 * Design rules:
 *   - ALL prose is generated from data; no placeholder fiction.
 *   - Missing evidence is stated explicitly ("not documented").
 *   - Biomarker data (sFlt-1, PlGF, sEng, POC) EXCLUDED.
 *   - Site/provider identifiers EXCLUDED per SOP-ADJ-002.
 *   - The system PRESENTS evidence; it does NOT adjudicate.
 *
 * Rule Version: FORM-ADJ-PROSE-v2.0
 */

import { buildDemographicString, formatVisitDate, pairBpReadings, inferLabInterpretation, formatLabResult } from './visitEvidence.js';

export const NARRATIVE_VERSION = 'FORM-ADJ-PROSE-v2.0';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function safe(v, fallback = 'not documented') {
  if (v == null || (typeof v === 'string' && !v.trim())) return fallback;
  return String(v).trim();
}

function num(v) {
  if (typeof v === 'number') return v;
  const match = String(v ?? '').replace(',', '.').match(/-?\d+(\.\d+)?/);
  return match ? Number(match[0]) : null;
}

function plural(n, singular, pluralForm) {
  return n === 1 ? singular : (pluralForm || singular + 's');
}

function bpClassify(sbp, dbp) {
  if (sbp >= 160 || dbp >= 110) return 'severe';
  if (sbp >= 140 || dbp >= 90) return 'hypertensive';
  return 'normotensive';
}

function bpStr(sbp, dbp) {
  return `${sbp}/${dbp} mmHg`;
}

function formatGa(gaLabel) {
  if (!gaLabel || /unclassifiable|null|undefined|antenatal/i.test(String(gaLabel))) return null;
  return String(gaLabel);
}

function ordinal(n) {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

/**
 * Format a value with a unit, ensuring the unit is not duplicated
 * if it already appears in the value (e.g. preventing '36.1°C°C' or '65 kg kg').
 */
export function formatWithUnit(val, unit, spacing = ' ') {
  if (val == null || val === '') return '';
  const str = String(val).trim();
  const escaped = unit.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const rx = new RegExp(`\\s*${escaped}\\s*$`, 'i');
  if (rx.test(str)) {
    return str;
  }
  return `${str}${spacing}${unit}`;
}

// ─── Medication Extraction ────────────────────────────────────────────────────

export function cleanPhpString(str) {
  if (!str) return '';
  let s = String(str);
  s = s.replace(/^#\d*\s*-\s*/, '');
  // Extract embedded structured medication names if present
  const nameMatch = s.match(/medication treatment name:\s*s:\d+:"([^"]+)"/i) || s.match(/medication treatment name:\s*([^,;]+)/i);
  if (nameMatch && nameMatch[1]) return nameMatch[1].trim();
  
  // Clean standard PHP serialized strings
  s = s.replace(/s:\d+:"([^"]*)";?,?/g, '$1');
  return s.replace(/[;,]+$/, '').trim();
}

function extractMedications(visit) {
  const meds = [];
  const isNonMedicationValue = (value) => /^(yes|no|true|false|none|not applicable|not documented|not done|n\/a|unspecified medication)$/i.test(String(value || '').trim());
  const ev = visit?.evidence || {};
  const medKeys = Object.keys(ev).filter(k => /medication|drug|treatment|therapy/i.test(k));
  for (const k of medKeys) {
    const rows = Array.isArray(ev[k]) ? ev[k] : [];
    for (const r of rows) {
      const val = cleanPhpString(r?.raw_source_value ?? r?.parsed_text_value ?? r?.value);
      if (val && !isNonMedicationValue(val)) {
        meds.push(val);
      }
    }
  }
  // Also from explicit medications array
  const visitMeds = Array.isArray(visit?.medications) ? visit.medications : [];
  if (visitMeds.length) {
    for (const m of visitMeds) {
      const val = cleanPhpString(m?.value || m?.name || m?.description);
      if (val && !isNonMedicationValue(val)) {
        meds.push(val);
      }
    }
  }
  return [...new Set(meds)];
}

// ─── Symptom Extraction ───────────────────────────────────────────────────────

function extractSymptoms(visit) {
  const symptoms = [];
  const obs = Array.isArray(visit?.symptoms) ? visit.symptoms : [];
  for (const s of obs) {
    const val = cleanPhpString(s?.value);
    if (val && !/^(no|none|false|normal|unchanged|negative)$/i.test(val)) {
      symptoms.push(val);
    }
  }
  return symptoms;
}

// ─── Lab Synopsis ─────────────────────────────────────────────────────────────

function labValue(labs, key) {
  const safeLabs = Array.isArray(labs) ? labs : [];
  const row = safeLabs.find(l => l?.key === key && l?.value != null);
  return row ? row.value : null;
}

function labRow(labs, key) {
  const safeLabs = Array.isArray(labs) ? labs : [];
  return safeLabs.find(l => l?.key === key && l?.value != null) || null;
}

// ─── Evidence Helper for Visit ────────────────────────────────────────────────

function firstEvidence(visit, keys) {
  const ev = visit?.evidence || {};
  for (const k of keys) {
    const rows = Array.isArray(ev[k]) ? ev[k] : [];
    if (rows.length) {
      const r = rows[0];
      return r?.numeric_value ?? r?.raw_source_value ?? r?.parsed_text_value ?? r?.coded_value ?? null;
    }
  }
  return null;
}

function sourceValue(row) {
  if (!row) return null;
  const raw = row.raw_source_value ?? row.parsed_text_value ?? row.value ?? row.coded_value ?? null;
  const preferred = raw != null && /(?:^|\s)#?\d*\s*-\s*s:\d+:"/i.test(String(raw))
    ? raw
    : (raw != null && /^(?:trace|negative|positive|\d\+|\+{1,4})$/i.test(String(raw).trim())
      ? raw
      : (row.numeric_value ?? raw));
  const cleaned = cleanPhpString(preferred);
  return cleaned === '' ? null : cleaned;
}

function evidenceRows(visit, keys) {
  const evidence = visit?.evidence || {};
  return keys.flatMap((key) => Array.isArray(evidence[key]) ? evidence[key] : []);
}

function usableEvidenceValue(visit, keys, fieldPattern = null) {
  for (const row of evidenceRows(visit, keys)) {
    const field = String(row?.source?.field || row?.source_field_label || '');
    if (fieldPattern && !fieldPattern.test(field)) continue;
    const value = sourceValue(row);
    if (value && !/^(yes|no|not done|not assessed|not evaluated|not applicable|not documented|n\/a)$/i.test(value)) return value;
  }
  return null;
}

function unavailableEvidence(visit, keys, fieldPattern = null) {
  return evidenceRows(visit, keys).some((row) => {
    const field = String(row?.source?.field || row?.source_field_label || '');
    if (fieldPattern && !fieldPattern.test(field)) return false;
    return /^(no|not done|not assessed|not evaluated|not applicable|not documented|n\/a)$/i.test(sourceValue(row) || '');
  });
}

function historyRows(caseData, domain = null) {
  const history = caseData?.history || {};
  const rows = domain
    ? (Array.isArray(history[domain]) ? history[domain] : [])
    : Object.values(history).flatMap((items) => Array.isArray(items) ? items : []);
  return rows;
}

function historyValues(caseData, keys, domain = null) {
  const wanted = new Set(keys);
  return historyRows(caseData, domain)
    .filter((row) => wanted.has(row?.field_key || row?.key))
    .map((row) => cleanPhpString(row?.value))
    .filter((value) => value != null && value !== '' && !/^source field unavailable$/i.test(value));
}

function historyValue(caseData, keys, domain = null) {
  return historyValues(caseData, keys, domain)[0] ?? null;
}

function naturalList(items, conjunction = 'and') {
  const values = [...new Set(items.filter(Boolean))];
  if (values.length < 2) return values[0] || '';
  if (values.length === 2) return `${values[0]} ${conjunction} ${values[1]}`;
  return `${values.slice(0, -1).join(', ')} ${conjunction} ${values[values.length - 1]}`;
}

function countLabel(value) {
  return value === 1 ? 'one' : String(value);
}

function screeningGaLabel(value) {
  return String(value || '')
    .replace(/\b1 weeks\b/i, '1 week')
    .replace(/\b1 days\b/i, '1 day')
    .replace(/\s*,\s*/g, ' and ');
}

function screeningHistoryProse(caseData) {
  const medical = historyValue(caseData, [
    'does_the_participant_have_any_medical_history',
    'does_the_subject_have_any_medical_conditions_to_report',
  ], 'conditions');
  const surgery = historyValue(caseData, ['did_participant_have_any_surgery'], 'conditions');
  const allergy = historyValue(caseData, [
    'does_participant_have_any_ongoing_allergies',
    'does_the_subject_have_any_allergies_or_intolerances_to_report',
  ], 'conditions');
  const priorMeds = historyValue(caseData, [
    'did_the_participant_take_any_prior_or_concomitant_medications_including_supplements_in_the_past_30_days',
  ], 'conditions');

  const allNegative = [medical, surgery, allergy].every((value) => /^no$/i.test(value || ''));
  let prose = '';
  if (allNegative) {
    prose = 'Her medical-history assessment recorded no previous medical conditions, surgery or allergies';
  } else {
    const conditions = historyValues(caseData, ['medical_condition'], 'conditions')
      .filter((value) => !/^(other medical condition|none|no)$/i.test(value));
    prose = conditions.length
      ? `Her medical history included ${naturalList(conditions)}`
      : 'Her available medical history was reviewed';
  }
  if (/^no$/i.test(priorMeds || '')) prose += ' and no use of prior or concomitant medication during the preceding 30 days.';
  else if (/^yes$/i.test(priorMeds || '')) prose += '. Prior or concomitant medication use during the preceding 30 days was reported.';
  else prose += '.';
  return prose;
}

function screeningObstetricProse(caseData) {
  const risk = caseData?.risk_summary || {};
  const previousPregnancies = num(historyValue(caseData, ['if_yes_how_many_previous_pregnancies'], 'obstetric'));
  const gravidity = num(risk.gravidity ?? caseData?.gravidity) ?? (previousPregnancies != null ? previousPregnancies + 1 : null);
  const parity = num(risk.parity ?? caseData?.parity) ?? num(historyValue(caseData, ['number_of_live_births'], 'obstetric'));
  const miscarriages = num(risk.miscarriages) ?? num(historyValue(caseData, ['number_of_miscarriages'], 'obstetric')) ?? 0;
  const stillbirths = num(risk.stillbirths) ?? num(historyValue(caseData, ['number_of_still_births'], 'obstetric')) ?? 0;
  const cSections = num(risk.c_sections) ?? num(historyValue(caseData, ['number_of_cesarean_sections'], 'obstetric')) ?? 0;
  const vaginal = num(risk.vaginal_deliveries) ?? num(historyValue(caseData, ['number_of_vaginal_deliveries'], 'obstetric')) ?? 0;

  const parts = [];
  if (parity > 0) parts.push(`${countLabel(parity)} previous live ${plural(parity, 'birth')}`);
  if (miscarriages > 0) parts.push(`${countLabel(miscarriages)} ${plural(miscarriages, 'miscarriage')}`);
  if (stillbirths > 0) parts.push(`${countLabel(stillbirths)} previous ${plural(stillbirths, 'stillbirth')}`);
  if (vaginal > 0) parts.push(`${countLabel(vaginal)} prior vaginal ${plural(vaginal, 'delivery', 'deliveries')}`);
  if (cSections > 0) parts.push(`${countLabel(cSections)} prior caesarean ${plural(cSections, 'section')}`);

  let prose = '';
  if (gravidity === 1 && (parity ?? 0) === 0) prose = 'This was her first pregnancy.';
  else if (parts.length) prose = `Her obstetric history included ${naturalList(parts)}.`;

  if (cSections > 0) {
    const reasons = [
      ...historyValues(caseData, ['reason_for_cesarean_section'], 'obstetric'),
      ...historyValues(caseData, ['other_reason'], 'obstetric'),
    ].filter((value) => !/^(0|none|no)$/i.test(value));
    if (reasons.length) prose += ` The recorded caesarean indication included ${naturalList(reasons.map((r) => r.toLowerCase()))}.`;
  }

  const complicationFields = [
    ['does_participant_have_any_history_of_raised_blood_pressure_during_pregnancy', 'raised blood pressure'],
    ['does_the_participant_have_any_history_of_preeclampsia_in_previous_pregnancies', 'pre-eclampsia'],
    ['does_the_participant_have_any_history_of_severe_preeclampsia_in_previous_pregnancies', 'severe pre-eclampsia'],
    ['does_the_participant_have_any_history_of_eclampsia_in_previous_pregnancies', 'eclampsia'],
    ['does_the_participant_have_any_history_of_hellp_in_previous_pregnancies', 'HELLP syndrome'],
    ['does_the_participant_have_any_history_of_iugr_in_previous_pregnancies', 'fetal growth restriction'],
  ];
  const documented = complicationFields
    .map(([key, label]) => ({ label, value: historyValue(caseData, [key], 'obstetric') }))
    .filter((item) => item.value != null);
  const positives = documented.filter((item) => /^yes$/i.test(item.value)).map((item) => item.label);
  if (positives.length) prose += ` Previous pregnancy complications included ${naturalList(positives)}.`;
  else if (documented.length === complicationFields.length) {
    prose += ` No previous pregnancy complicated by ${naturalList(documented.map((item) => item.label))} was recorded.`;
  }

  if (/^yes$/i.test(historyValue(caseData, ['has_anyone_in_participant_family_ever_had_hypertension'], 'conditions') || '')) {
    prose += ' A family history of hypertension was documented.';
  }
  return prose.trim();
}

function screeningUltrasoundProse(visit) {
  const scanDate = usableEvidenceValue(visit, ['dating_anchor_date', 'us_date']);
  const edd = usableEvidenceValue(visit, ['edd']);
  const gaRows = evidenceRows(visit, ['dating_anchor_ga'])
    .filter((row) => /sonographic data|ultrasound|scan/i.test(String(row?.source?.page || '')))
    .map(sourceValue)
    .filter((value) => value != null && /^\d+(?:\.\d+)?$/.test(value));
  const gaWeeks = gaRows.length ? Number(gaRows[0]) : null;
  const gaDays = gaRows.length > 1 ? Number(gaRows[1]) : 0;

  const s = visit?.sonography || {};
  const efw = usableEvidenceValue(visit, ['efw', 'EFW']) || (s.efwRaw !== 'not documented' ? s.efwRaw : null);
  const presentation = usableEvidenceValue(visit, ['fetal_presentation']) || (s.presentation !== 'unknown' ? s.presentation : null);
  const fhr = usableEvidenceValue(visit, ['fetal_heart_rate', 'FETAL_HEART_RATE', 'fetal_hr']) || (s.fhr !== 'not documented' ? s.fhr : null);
  const movement = usableEvidenceValue(visit, ['us_viability']) || s.movement;
  const fluid = usableEvidenceValue(visit, ['afi', 'AFI']) || s.afiRaw;
  const placenta = usableEvidenceValue(visit, ['us_placenta']) || s.placenta;
  const cervical = usableEvidenceValue(visit, ['cervical_length', 'CERVICAL_LENGTH']) || s.cervicalLength;

  if (!scanDate && gaWeeks == null && !efw && !presentation && !fhr && !movement && !fluid && !placenta && !cervical) {
    return 'No obstetric ultrasound was documented.';
  }

  let prose = scanDate ? `The dating ultrasound was performed on ${formatVisitDate(scanDate)}` : 'The dating ultrasound date was not documented';
  if (gaWeeks != null) prose += ` at ${gaWeeks} weeks and ${gaDays} days`;
  if (edd) prose += `, with an expected delivery date of ${formatVisitDate(edd)}`;
  prose += '.';

  const measurements = [];
  if (efw) measurements.push(`an estimated fetal weight of ${formatWithUnit(efw, 'g')}`);
  if (presentation) measurements.push(`${presentation.toLowerCase()} presentation`);
  if (fhr) measurements.push(`a fetal heart rate of ${formatWithUnit(fhr, 'bpm')}`);
  if (measurements.length) prose += ` The scan recorded ${naturalList(measurements)}.`;

  const findings = [
    movement ? { label: 'fetal movement', value: movement } : null,
    fluid ? { label: 'amniotic-fluid volume', value: fluid } : null,
    placenta ? { label: 'placental position', value: placenta } : null,
  ].filter(Boolean);
  if (findings.length && findings.every((item) => /^normal$/i.test(String(item.value)))) {
    prose += ` ${naturalList(findings.map((item) => item.label)).replace(/^f/, 'F')} ${findings.length === 1 ? 'was' : 'were'} recorded as normal.`;
  } else if (findings.length) {
    prose += ` ${findings.map((item) => `${item.label} was recorded as ${String(item.value).toLowerCase()}`).join('; ')}.`;
  }
  const unavailable = [
    !efw && unavailableEvidence(visit, ['efw', 'EFW'], /estimated.*fetal weight/i) ? 'estimated fetal weight' : null,
    !presentation && unavailableEvidence(visit, ['fetal_presentation'], /ultrasound presentation/i) ? 'fetal presentation' : null,
    !movement && unavailableEvidence(visit, ['us_viability']) ? 'fetal movement' : null,
    !fluid && unavailableEvidence(visit, ['afi', 'AFI']) ? 'amniotic-fluid assessment' : null,
    !placenta && unavailableEvidence(visit, ['us_placenta']) ? 'placental position' : null,
  ].filter(Boolean);
  if (unavailable.length) prose += ` ${naturalList(unavailable).replace(/^e/, 'E')} ${unavailable.length === 1 ? 'was' : 'were'} not documented.`;
  if (cervical && !/^not documented$/i.test(cervical)) prose += ` Cervical length was ${formatWithUnit(cervical, 'cm')}.`;
  return prose;
}

function generateScreeningNarrative(visit, caseData) {
  const age = caseData?.age || caseData?.risk_summary?.age || historyValue(caseData, ['age'], 'baseline');
  const gravida = num(caseData?.risk_summary?.gravidity ?? caseData?.gravidity);
  const parity = num(caseData?.risk_summary?.parity ?? caseData?.parity);
  const gp = gravida != null && parity != null ? ` G${gravida}P${parity}` : '';
  const date = visit?.date ? ` on ${formatVisitDate(visit.date)}` : '';
  const ga = formatGa(visit?.gestationalLabel);
  let opening = `${age ? `A ${age}-year-old` : 'An adult'}${gp} participant presented for routine study screening${date}`;
  if (ga) opening += ` at ${screeningGaLabel(ga)} of gestation`;
  opening += `. ${screeningHistoryProse(caseData)}`;

  const obstetric = screeningObstetricProse(caseData);
  if (obstetric) opening += ` ${obstetric}`;

  const vitals = [];
  if (visit?.vitals?.bp) vitals.push(`Blood pressure was ${formatWithUnit(visit.vitals.bp, 'mmHg')}`);
  if (visit?.vitals?.recheck) vitals.push(`remained ${formatWithUnit(visit.vitals.recheck, 'mmHg')} on repeat measurement`);
  if (visit?.vitals?.hr) vitals.push(`heart rate was ${formatWithUnit(visit.vitals.hr, 'bpm')}`);
  const respiratory = usableEvidenceValue(visit, ['respiratory_rate']);
  if (respiratory) vitals.push(`respiratory rate was ${formatWithUnit(respiratory, 'breaths/min')}`);
  const oxygen = usableEvidenceValue(visit, ['o2_sat']);
  if (oxygen) vitals.push(`oxygen saturation was ${formatWithUnit(oxygen, '%', '')}`);
  const tempLocation = usableEvidenceValue(visit, ['temperature'], /location/i);
  if (visit?.vitals?.temp) vitals.push(`${tempLocation ? `${tempLocation.toLowerCase()} ` : ''}temperature was ${formatWithUnit(visit.vitals.temp, '°C', '')}`);
  if (visit?.vitals?.weight) vitals.push(`weight was ${formatWithUnit(visit.vitals.weight, 'kg')}`);
  let assessment = vitals.length ? `${naturalList(vitals)}.` : 'Vital signs were not documented.';

  const protein = usableEvidenceValue(visit, ['ua_protein', 'UA_PROTEIN', 'DIPSTICK_PROTEIN']);
  if (protein) assessment += ` Urine protein dipstick was ${protein.toLowerCase()}.`;

  return [
    opening,
    assessment,
    screeningUltrasoundProse(visit),
    'Laboratory results are presented in the table below.',
  ].join('\n\n');
}

function evidenceValue(visit, keys, fieldPattern = null) {
  for (const row of evidenceRows(visit, keys)) {
    const field = String(row?.source?.field || row?.source_field_label || '');
    if (fieldPattern && !fieldPattern.test(field)) continue;
    const value = sourceValue(row);
    if (value != null && value !== '') return value;
  }
  return null;
}

function literalEvidenceValue(visit, keys, fieldPattern = null) {
  for (const row of evidenceRows(visit, keys)) {
    const field = String(row?.source?.field || row?.source_field_label || '');
    if (fieldPattern && !fieldPattern.test(field)) continue;
    const raw = row?.raw_source_value ?? row?.parsed_text_value ?? row?.value ?? row?.coded_value ?? null;
    const value = cleanPhpString(raw);
    if (value != null && value !== '') return value;
  }
  return null;
}

function literalRowValue(row) {
  return cleanPhpString(row?.raw_source_value ?? row?.parsed_text_value ?? row?.value ?? row?.coded_value ?? null);
}

function numericEvidenceValue(visit, keys, fieldPattern = null) {
  const value = usableEvidenceValue(visit, keys, fieldPattern);
  if (value == null || !/^-?\d+(?:\.\d+)?$/.test(String(value).trim())) return null;
  return String(value).trim();
}

function sentenceList(items) {
  return naturalList(items).replace(/^./, (letter) => letter.toUpperCase());
}

function followUpStatusProse(visit) {
  const status = usableEvidenceValue(visit, ['health_status']);
  const description = usableEvidenceValue(visit, ['health_status_description'])
    || usableEvidenceValue(visit, ['health_status'], /description/i);
  if (status && description && status.toLowerCase() !== description.toLowerCase()) {
    return `Her health status was recorded as ${status.toLowerCase()}, with the description “${description.replace(/\s+/g, ' ').trim()}.”`;
  }
  if (description) return `Her health status was described as “${description.replace(/\s+/g, ' ').trim()}.”`;
  if (status) return `Her health status was recorded as ${status.toLowerCase()}.`;
  return '';
}

function symptomProse(visit) {
  const symptomFields = [
    ['headache', 'persistent headache'],
    ['visual_disturbance', 'visual disturbance'],
    ['pe_symptom_sudden_weight_gain', 'sudden weight gain'],
    ['epigastric_pain', 'epigastric pain'],
  ];
  const documented = symptomFields
    .map(([key, label]) => ({ label, value: evidenceValue(visit, [key]) }))
    .filter((item) => item.value != null);
  const present = documented.filter((item) => /^yes$/i.test(item.value)).map((item) => item.label);
  const absent = documented.filter((item) => /^no$/i.test(item.value)).map((item) => item.label);
  const sentences = [];
  if (present.length) sentences.push(`She reported ${naturalList(present)}.`);
  if (absent.length) sentences.push(`She reported no ${naturalList(absent, 'or')}.`);
  const pulmonary = evidenceValue(visit, ['pulmonary_edema'], /^pulmonary (?:oedema|edema)\??$/i);
  if (/^yes$/i.test(pulmonary || '')) sentences.push('Pulmonary oedema was recorded.');
  else if (/^no$/i.test(pulmonary || '')) sentences.push('Pulmonary oedema was not recorded.');
  return sentences.join(' ');
}

function bloodPressureProse(visit) {
  const readings = (Array.isArray(visit?.bp) ? visit.bp : [])
    .filter((row) => row?.sbp > 0 && row?.dbp > 0);
  let prose = '';
  if (readings.length) {
    prose = readings.length === 1
      ? `Blood pressure was ${readings[0].sbp}/${readings[0].dbp} mmHg.`
      : `Blood pressure was initially ${readings[0].sbp}/${readings[0].dbp} mmHg, with a second recorded measurement of ${readings[1].sbp}/${readings[1].dbp} mmHg`;
    if (readings.length > 1) {
      const interval = readings[0].observed_at && readings[1].observed_at
        ? Math.abs(new Date(readings[1].observed_at) - new Date(readings[0].observed_at)) / 60000
        : null;
      prose += interval > 0 ? ` ${Math.round(interval)} minutes later.` : '; the interval between measurements was unavailable.';
    }
  } else {
    prose = 'Blood pressure was not documented.';
  }

  const systolicCount = evidenceRows(visit, ['bp_systolic', 'SBP', 'SYSTOLIC_BP'])
    .map(sourceValue).filter((value) => num(value) > 0).length;
  const diastolicCount = evidenceRows(visit, ['bp_diastolic', 'DBP', 'DIASTOLIC_BP'])
    .map(sourceValue).filter((value) => num(value) > 0).length;
  if (systolicCount > diastolicCount) {
    const systolics = evidenceRows(visit, ['bp_systolic', 'SBP', 'SYSTOLIC_BP'])
      .map(sourceValue).filter((value) => num(value) > 0);
    const unpaired = systolics.slice(diastolicCount);
    if (unpaired.length) prose += ` An additional systolic measurement of ${unpaired[0]} mmHg was recorded without a corresponding diastolic measurement.`;
  }
  return prose;
}

function maternalVitalsProse(visit) {
  const parts = [];
  if (visit?.vitals?.hr) parts.push(`heart rate was ${formatWithUnit(visit.vitals.hr, 'bpm')}`);
  const respiratory = numericEvidenceValue(visit, ['respiratory_rate']);
  if (respiratory) parts.push(`respiratory rate was ${formatWithUnit(respiratory, 'breaths/min')}`);
  const oxygen = numericEvidenceValue(visit, ['o2_sat']);
  if (oxygen) parts.push(`oxygen saturation was ${formatWithUnit(oxygen, '%', '')}`);
  const tempLocation = usableEvidenceValue(visit, ['temperature'], /location/i);
  if (visit?.vitals?.temp) parts.push(`${tempLocation ? `${tempLocation.toLowerCase()} ` : ''}temperature was ${formatWithUnit(visit.vitals.temp, '°C', '')}`);
  if (visit?.vitals?.weight) parts.push(`weight was ${formatWithUnit(visit.vitals.weight, 'kg')}`);
  return parts.length ? `${sentenceList(parts)}.` : '';
}

function proteinuriaProse(visit) {
  const upcr = usableEvidenceValue(visit, ['upcr', 'UPCR']);
  const dipstick = evidenceValue(visit, ['ua_protein', 'UA_PROTEIN', 'DIPSTICK_PROTEIN'], /protein/i);
  const parts = [];
  if (dipstick) {
    if (/^(not done|not assessed|not available|n\/a)$/i.test(dipstick)) parts.push('Urine protein dipstick was not done');
    else parts.push(`Urine protein dipstick was ${dipstick.toLowerCase()}`);
  }
  if (upcr) parts.push(`UPCR was ${upcr}`);
  return parts.length ? `${sentenceList(parts)}.` : 'Proteinuria assessment was not documented.';
}

function medicationAndAdverseEventProse(visit) {
  const medicationChange = evidenceValue(visit, ['medication_changes'])
    || evidenceValue(visit, ['medication_name'], /updates?\/changes?|medication changes?/i);
  const newAe = evidenceValue(visit, ['new_adverse_events']);
  const changedAe = evidenceValue(visit, ['changed_adverse_events']);
  const sentences = [];

  if (/^no$/i.test(medicationChange || '')) sentences.push('No medication changes were reported.');
  else if (/^yes$/i.test(medicationChange || '')) {
    const meds = extractMedications(visit);
    sentences.push(meds.length
      ? `Medication changes included ${naturalList(meds)}.`
      : 'Medication changes were reported, but the medication details were unavailable in the supplied visit record.');
  }

  if (/^no$/i.test(newAe || '') && /^no$/i.test(changedAe || '')) {
    sentences.push('No new adverse events or changes to existing adverse events were reported.');
  } else {
    const missingDetails = [];
    if (/^yes$/i.test(newAe || '')) missingDetails.push('a new adverse event');
    if (/^yes$/i.test(changedAe || '')) missingDetails.push('a change to an existing adverse event');
    if (missingDetails.length) {
      sentences.push(`The source indicated ${naturalList(missingDetails)}, but no description was identified in the supplied visit record; source clarification is required.`);
    }
  }
  return sentences.join(' ');
}

function followUpUltrasoundProse(visit) {
  const ultrasoundKeys = ['us_date', 'efw', 'fetal_presentation', 'us_viability', 'fetal_heart_rate', 'afi', 'us_placenta', 'cervical_length'];
  const hasUltrasoundRecord = ultrasoundKeys.some((key) => evidenceRows(visit, [key]).length > 0);
  if (!hasUltrasoundRecord) return 'No obstetric ultrasound was documented for this visit.';

  const scanDate = usableEvidenceValue(visit, ['us_date']);
  let prose = scanDate
    ? `An obstetric ultrasound was performed on ${formatVisitDate(scanDate)}.`
    : `An obstetric ultrasound assessment was recorded for this visit${visit?.date ? ` on ${formatVisitDate(visit.date)}` : ''}.`;

  const fhr = numericEvidenceValue(visit, ['fetal_heart_rate', 'FETAL_HEART_RATE', 'fetal_hr']);
  const efw = numericEvidenceValue(visit, ['efw', 'EFW'], /fetal weight/i);
  const presentation = usableEvidenceValue(visit, ['fetal_presentation'], /description|provide/i);
  const measurements = [];
  if (fhr) measurements.push(`fetal heart rate was ${formatWithUnit(fhr, 'bpm')}`);
  if (efw) measurements.push(`estimated fetal weight was ${formatWithUnit(efw, 'g')}`);
  if (presentation) measurements.push(`fetal presentation was ${presentation.toLowerCase()}`);
  if (measurements.length) prose += ` ${sentenceList(measurements)}.`;

  const findings = [
    ['us_viability', 'fetal movement'],
    ['afi', 'amniotic-fluid volume'],
    ['us_placenta', 'placental position'],
  ].map(([key, label]) => ({ label, value: usableEvidenceValue(visit, [key]) })).filter((item) => item.value);
  if (findings.length && findings.every((item) => /^normal$/i.test(item.value))) {
    prose += ` ${sentenceList(findings.map((item) => item.label))} ${findings.length === 1 ? 'was' : 'were'} recorded as normal.`;
  } else if (findings.length) {
    prose += ` ${sentenceList(findings.map((item) => `${item.label} was recorded as ${item.value.toLowerCase()}`))}.`;
  }

  const efwStatus = evidenceValue(visit, ['efw', 'EFW'], /estimated.*fetal weight/i);
  if (!efw && efwStatus && !/^(no|not done|not assessed|not available|n\/a)$/i.test(efwStatus)) {
    prose += ` Estimated fetal weight was marked “${efwStatus},” but no numerical weight was supplied; estimated fetal weight cannot be determined.`;
  } else if (!efw && unavailableEvidence(visit, ['efw', 'EFW'])) {
    prose += ' Estimated fetal weight was not documented.';
  }

  const presentationStatus = evidenceValue(visit, ['fetal_presentation'], /ultrasound presentation/i);
  if (!presentation && /^yes$/i.test(presentationStatus || '')) {
    prose += ' Ultrasound presentation was marked as available, but the presentation description was unavailable.';
  } else if (!presentation && unavailableEvidence(visit, ['fetal_presentation'])) {
    prose += ' Fetal presentation was not documented.';
  }
  const cervical = numericEvidenceValue(visit, ['cervical_length', 'CERVICAL_LENGTH']);
  if (cervical) prose += ` Cervical length was ${formatWithUnit(cervical, 'cm')}.`;
  return prose;
}

function generateAntenatalFollowUpNarrative(visit, visitNum) {
  const date = visit?.date ? formatVisitDate(visit.date) : 'an undocumented date';
  const ga = formatGa(visit?.gestationalLabel);
  let opening = `On ${date}, ${ga ? `at ${screeningGaLabel(ga)} of gestation, ` : ''}the participant attended the scheduled Visit ${visitNum} antenatal follow-up.`;
  const status = followUpStatusProse(visit);
  if (status) opening += ` ${status}`;
  const symptoms = symptomProse(visit);
  if (symptoms) opening += ` ${symptoms}`;

  const assessment = [bloodPressureProse(visit), maternalVitalsProse(visit), proteinuriaProse(visit)]
    .filter(Boolean).join(' ');
  const changes = medicationAndAdverseEventProse(visit);

  return [
    opening,
    assessment,
    changes,
    followUpUltrasoundProse(visit),
    'Laboratory results and their source-recorded interpretations are presented in the table below.',
  ].filter(Boolean).join('\n\n');
}

function daysBetweenDates(first, second) {
  const start = new Date(first);
  const end = new Date(second);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null;
  return Math.round((end.getTime() - start.getTime()) / 86400000);
}

function deliveryDateFromCase(caseData) {
  const deliveryVisit = (caseData?.visits || []).find((row) => row?.visit_number === 5 || /^V0?5$/i.test(row?.name || ''));
  const sourceDeliveryDate = literalEvidenceValue(deliveryVisit, ['delivery_date'], /^date of delivery$/i);
  if (sourceDeliveryDate) return sourceDeliveryDate;
  const candidate = caseData?.delivery_date || caseData?.derivedDeliveryDate;
  if (candidate) {
    const parsed = new Date(candidate);
    if (!Number.isNaN(parsed.getTime()) && parsed.getFullYear() >= 2000) return candidate;
  }
  return null;
}

function infantAssessmentProse(visit, liveBirth = false, alreadyReported = []) {
  const sexRaw = usableEvidenceValue(visit, ['neonatal_gender']);
  const sex = /^f$/i.test(sexRaw || '') ? 'female' : /^m$/i.test(sexRaw || '') ? 'male' : sexRaw?.toLowerCase();
  const weight = numericEvidenceValue(visit, ['newborn_weight_g']);
  const length = numericEvidenceValue(visit, ['neonatal_length']);
  const head = numericEvidenceValue(visit, ['neonatal_hc']);
  const heartRate = numericEvidenceValue(visit, ['neonatal_heart_rate']);
  const apgar1 = numericEvidenceValue(visit, ['apgar_1m']);
  const apgar5 = numericEvidenceValue(visit, ['apgar_5m']);
  const apgar10 = numericEvidenceValue(visit, ['apgar_10m']);
  const hasCoreInfantData = [sex, weight, length, head, heartRate, apgar1, apgar5, apgar10]
    .some((value) => value != null);
  const respiratoryRate = (liveBirth || hasCoreInfantData)
    ? numericEvidenceValue(visit, ['neonatal_respiratory_exam', 'respiratory_rate'], /^respiration|respiratory rate$/i)
    : null;
  const hasInfantData = hasCoreInfantData || respiratoryRate != null;
  if (!hasInfantData) return 'No infant assessment was documented at this visit.';

  let prose = liveBirth
    ? `A liveborn ${sex ? `${sex} ` : ''}infant was recorded`
    : `The infant assessment recorded ${sex ? `a ${sex} infant` : 'an infant'}`;
  const anthropometry = [];
  if (weight) anthropometry.push(`a birth weight of ${formatWithUnit(Number(weight).toLocaleString('en-US'), 'g')}`);
  if (length) anthropometry.push(`length ${formatWithUnit(length, 'cm')}`);
  if (head) anthropometry.push(`head circumference ${formatWithUnit(head, 'cm')}`);
  if (anthropometry.length) prose += ` with ${naturalList(anthropometry)}`;
  prose += '.';

  const apgars = [apgar1, apgar5, apgar10].filter(Boolean);
  if (apgars.length === 3) prose += ` Apgar scores were ${apgar1}, ${apgar5} and ${apgar10} at 1, 5 and 10 minutes, respectively.`;
  else if (apgar1 && apgar5) prose += ` Apgar scores were ${apgar1} and ${apgar5} at 1 and 5 minutes, respectively.`;
  const infantVitals = [];
  if (heartRate) infantVitals.push(`the recorded neonatal heart rate was ${formatWithUnit(heartRate, 'bpm')}`);
  if (respiratoryRate) infantVitals.push(`respiratory rate was ${formatWithUnit(respiratoryRate, 'breaths/min')}`);
  if (infantVitals.length) prose += ` ${sentenceList(infantVitals)}.`;

  const negativeOutcomes = [
    ['neonatal_icu_admission', 'neonatal intensive-care admission'],
    ['neonatal_rds', 'respiratory distress syndrome'],
    ['neonatal_ivh', 'intraventricular haemorrhage'],
    ['neonatal_nec', 'necrotising enterocolitis'],
    ['congenital_anomalies', 'congenital anomaly'],
    ['birth_complications', 'birth complication'],
  ].map(([key, label]) => ({ label, value: evidenceValue(visit, [key]) }))
    .filter((item) => /^no$/i.test(item.value || ''))
    .map((item) => item.label);
  if (negativeOutcomes.length) prose += ` No ${naturalList(negativeOutcomes, 'or')} was recorded.`;

  const birthComplication = evidenceValue(visit, ['birth_complications'], /^birth complications?$/i);
  const birthComplicationDescription = literalEvidenceValue(visit, ['birth_complications'], /description/i)
    || literalEvidenceValue(visit, ['delivery_outcome'], /delivery complications? description/i);
  const reported = alreadyReported.map((value) => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim());
  const isAlreadyReported = (value) => {
    const normalized = String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
    return normalized && reported.some((item) => item === normalized || item.includes(normalized) || normalized.includes(item));
  };
  const positiveOutcomes = [
    ['neonatal_icu_admission', 'Neonatal intensive-care admission'],
    ['neonatal_rds', 'Respiratory distress syndrome'],
    ['neonatal_ivh', 'Intraventricular haemorrhage'],
    ['neonatal_nec', 'Necrotising enterocolitis'],
    ['congenital_anomalies', 'A congenital anomaly'],
  ].map(([key, label]) => ({ label, value: evidenceValue(visit, [key]) }))
    .filter((item) => /^yes$/i.test(item.value || '') && !isAlreadyReported(item.label))
    .map((item) => item.label);
  if (/^yes$/i.test(birthComplication || '') && !isAlreadyReported(birthComplicationDescription)) {
    prose += birthComplicationDescription
      ? ` A birth complication was recorded as ${birthComplicationDescription}.`
      : ' A birth complication was recorded, but its description was unavailable.';
  }
  if (positiveOutcomes.length) prose += ` ${sentenceList(positiveOutcomes)} ${positiveOutcomes.length === 1 ? 'was' : 'were'} recorded.`;
  return prose;
}

function generatePostpartumNarrative(visit, caseData) {
  const visitDate = visit?.date;
  const deliveryDate = deliveryDateFromCase(caseData);
  const postpartumDays = visitDate && deliveryDate ? daysBetweenDates(deliveryDate, visitDate) : null;
  let opening = visitDate ? `On ${formatVisitDate(visitDate)}` : 'On an undocumented date';
  if (postpartumDays != null && postpartumDays >= 0) opening += `, ${postpartumDays} days after the documented delivery on ${formatVisitDate(deliveryDate)}`;
  else opening += ', at the final postpartum follow-up';
  opening += ', the participant attended the final postpartum follow-up.';
  const status = followUpStatusProse(visit);
  if (status) opening += ` ${status.replace(/^Her health status/, 'Her final health status')}`;
  const symptoms = symptomProse(visit);
  if (symptoms) opening += ` ${symptoms}`;

  let maternal = [bloodPressureProse(visit), maternalVitalsProse(visit), proteinuriaProse(visit)]
    .filter(Boolean).join(' ');
  const hospitalization = evidenceValue(visit, ['maternal_hospitalization']);
  const icu = evidenceValue(visit, ['maternal_icu']);
  if (/^no$/i.test(hospitalization || '') && /^no$/i.test(icu || '')) {
    maternal += ' No maternal hospitalization or intensive-care admission was recorded.';
  }

  return [
    opening,
    maternal,
    medicationAndAdverseEventProse(visit),
    infantAssessmentProse(visit),
    'Laboratory results and their source-recorded interpretations are presented in the table below.',
  ].filter(Boolean).join('\n\n');
}

function deliveryGaFromSource(visit) {
  const values = evidenceRows(visit, ['ega_delivery', 'GA_AT_DELIVERY'])
    .filter((row) => /gestational age at delivery/i.test(String(row?.source?.field || row?.source_field_label || '')))
    .map((row) => num(literalRowValue(row)))
    .filter((value) => value != null);
  const weeks = values.find((value) => value >= 10) ?? null;
  const days = values.find((value) => value >= 0 && value < 7) ?? null;
  return weeks == null ? null : { weeks, days };
}

function gaDaysFromLabel(label) {
  const match = String(label || '').match(/(\d+)\s*weeks?(?:\s*(?:,|and)\s*(\d+)\s*days?)?/i);
  return match ? Number(match[1]) * 7 + Number(match[2] || 0) : null;
}

function approvedDeliveryGa(caseData, deliveryDate) {
  if (!deliveryDate) return null;
  const v1 = (caseData?.visits || []).find((row) => row?.visit_number === 1 || /^V0?1$/i.test(row?.name || ''));
  if (!v1?.date) return null;
  const baseDays = num(v1.ga_days ?? v1.gestational_age_days) ?? gaDaysFromLabel(v1.ga || v1.gestationalLabel);
  const elapsed = daysBetweenDates(v1.date, deliveryDate);
  if (baseDays == null || elapsed == null) return null;
  return baseDays + elapsed;
}

function gaParts(totalDays) {
  return totalDays == null ? null : { weeks: Math.floor(totalDays / 7), days: totalDays % 7 };
}

function gaPhrase(ga) {
  if (!ga || ga.weeks == null) return null;
  return ga.days == null
    ? `${ga.weeks} weeks (gestational days unavailable)`
    : `${ga.weeks} weeks and ${ga.days} ${plural(ga.days, 'day')}`;
}

function deliveryIndicationProse(value) {
  const indication = String(value || '').trim().toLowerCase();
  const previousCs = indication.match(/^(\d+)\s+previous\s+c(?:s|[- ]?section)s?$/i);
  if (previousCs) {
    const count = Number(previousCs[1]);
    const countWord = ({ 1: 'one', 2: 'two', 3: 'three' })[count] || String(count);
    return `${countWord} previous caesarean ${plural(count, 'section')}`;
  }
  return indication.replace(/c[- ]?section/g, 'caesarean section').replace(/\bcs\b/g, 'caesarean section');
}

function hasDeliveryRecord(visit) {
  const deliveryDate = literalEvidenceValue(visit, ['delivery_date'], /^date of delivery$/i);
  const outcome = literalEvidenceValue(visit, ['pregnancy_outcome']);
  return Boolean(deliveryDate || (outcome && !/^(ongoing|not delivered|pending|unknown)$/i.test(outcome)));
}

function maternalDeliveryOutcomeProse(visit) {
  const statements = [];
  const ebl = numericEvidenceValue(visit, ['ebl_ml', 'estimated_blood_loss']);
  if (ebl) statements.push(`Estimated maternal blood loss was ${Number(ebl).toLocaleString('en-US')} mL.`);

  const transfusion = evidenceValue(visit, ['blood_transfusion']);
  if (/^no$/i.test(transfusion || '')) statements.push('No blood transfusion was recorded.');
  else if (/^yes$/i.test(transfusion || '')) statements.push('A blood transfusion was recorded.');

  const infection = evidenceValue(visit, ['delivery_outcome'], /infection post-delivery/i);
  if (/^no$/i.test(infection || '')) statements.push('No postpartum infection was recorded.');
  else if (/^yes$/i.test(infection || '')) statements.push('A postpartum infection was recorded.');

  const postpartumStatus = literalEvidenceValue(visit, ['delivery_outcome'], /^postpartum health status$/i);
  if (postpartumStatus) statements.push(`Postpartum health status was recorded as ${postpartumStatus.toLowerCase()}.`);

  const stay = numericEvidenceValue(visit, ['delivery_outcome'], /how many days.*hospital/i);
  if (stay) statements.push(`The participant remained in hospital for ${stay} ${plural(Number(stay), 'day')}.`);
  const readmission = evidenceValue(visit, ['delivery_outcome'], /readmitted.*hospital/i);
  if (/^no$/i.test(readmission || '')) statements.push('She was not readmitted.');
  else if (/^yes$/i.test(readmission || '')) statements.push('Hospital readmission was recorded.');

  const maternalDeath = evidenceValue(visit, ['maternal_death']);
  if (/^yes$/i.test(maternalDeath || '')) statements.push('Maternal death was recorded.');
  const icu = evidenceValue(visit, ['maternal_icu']);
  if (/^yes$/i.test(icu || '')) statements.push('Maternal intensive-care admission was recorded.');

  const status = followUpStatusProse(visit);
  if (status) statements.push(status.replace(/^Her health status/, 'Her subsequent health status'));
  return statements.join(' ');
}

function generateDeliveryNarrative(visit, caseData) {
  if (!hasDeliveryRecord(visit)) return '';

  const deliveryDate = literalEvidenceValue(visit, ['delivery_date'], /^date of delivery$/i);
  const assessmentDate = literalEvidenceValue(visit, ['delivery_date'], /delivery outcome status assessment/i);
  const mode = literalEvidenceValue(visit, ['delivery_mode', 'type_of_delivery']);
  const indication = literalEvidenceValue(visit, ['indication', 'reason_for_cesarean_section']);
  const outcome = literalEvidenceValue(visit, ['pregnancy_outcome']);
  const stillbirth = /stillbirth|still birth|fetal death/i.test(outcome || '');

  const sourceGa = deliveryGaFromSource(visit);
  const derivedGa = gaParts(approvedDeliveryGa(caseData, deliveryDate));
  const primaryGa = derivedGa || sourceGa;

  let opening = /caesarean|cesarean/i.test(mode || '') ? 'Caesarean delivery' : /vaginal/i.test(mode || '') ? 'Vaginal delivery' : 'Delivery';
  opening += deliveryDate ? ` occurred on ${formatVisitDate(deliveryDate)}` : ' was recorded, but the actual delivery date was unavailable';
  if (primaryGa) {
    opening += ` at ${primaryGa.weeks} weeks`;
    if (primaryGa.days != null) opening += ` and ${primaryGa.days} ${plural(primaryGa.days, 'day')}`;
    opening += ' of gestation';
    if (primaryGa.days == null) opening += '; gestational days were unavailable';
  }
  opening += '.';
  if (assessmentDate && (!deliveryDate || formatVisitDate(assessmentDate) !== formatVisitDate(deliveryDate))) {
    opening += ` The delivery outcome assessment was completed on ${formatVisitDate(assessmentDate)}.`;
  }
  if (/caesarean|cesarean/i.test(mode || '') && indication) opening += ` The recorded indication was ${deliveryIndicationProse(indication)}.`;

  const complicationStatus = evidenceValue(visit, ['delivery_outcome'], /^any complications at delivery/i);
  const complicationDescription = literalEvidenceValue(visit, ['delivery_outcome'], /delivery complications? description/i);
  if (/^yes$/i.test(complicationStatus || '')) {
    opening += complicationDescription
      ? ` A delivery complication was recorded as ${complicationDescription.toLowerCase()}.`
      : ' A delivery complication was recorded, but its description was unavailable.';
  } else if (/^no$/i.test(complicationStatus || '') && !stillbirth) {
    opening += ' No complication at delivery was recorded.';
  }
  if (stillbirth) opening += ' The pregnancy outcome was recorded as stillbirth.';

  const paragraphs = [opening];
  const maternal = maternalDeliveryOutcomeProse(visit);
  if (maternal) paragraphs.push(maternal);

  if (stillbirth) {
    paragraphs.push('No neonatal anthropometric measurements, Apgar scores or neonatal vital signs were documented.');
  } else {
    paragraphs.push(infantAssessmentProse(visit, true, [complicationDescription]));
  }

  const discrepancies = [];
  if (sourceGa && derivedGa && (sourceGa.weeks !== derivedGa.weeks || (sourceGa.days != null && sourceGa.days !== derivedGa.days))) {
    discrepancies.push(`The delivery form recorded gestational age as ${gaPhrase(sourceGa)}, while the approved dating calculation gives ${gaPhrase(derivedGa)}.`);
  }
  const newbornGaValue = evidenceRows(visit, ['ega_delivery', 'GA_AT_DELIVERY'])
    .find((row) => /^gestational age$/i.test(String(row?.source?.field || row?.source_field_label || '')));
  const newbornGa = num(literalRowValue(newbornGaValue));
  if (newbornGa != null && primaryGa && newbornGa !== primaryGa.weeks) {
    discrepancies.push(`A separate Newborn Assessment field recorded gestational age as ${newbornGa} weeks, which conflicts with the delivery gestational age of ${gaPhrase(primaryGa)}.`);
  }
  if (discrepancies.length) paragraphs.push(`${discrepancies.join(' ')} This conflicting source value requires verification.`);

  return paragraphs.filter(Boolean).join('\n\n');
}


// ═══════════════════════════════════════════════════════════════════════════════
// 1. PER-VISIT NARRATIVE
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Generate a rich, registrar-style per-visit clinical narrative.
 *
 * @param {object} visit     - Normalised visit from normalizeVisitEvidence()
 * @param {number} visitNum  - 1-6
 * @param {object} caseData  - Full patient case object
 * @returns {string}         - Multi-paragraph clinical prose
 */
export function generateVisitNarrative(visit, visitNum, caseData) {
  if (!visit) return 'No visit data available.';

  // Delivery is deliberately handled before generic visit-performance and
  // empty-data fallbacks. An unrecorded delivery must render as a truly blank
  // V5 narrative rather than as a missed-visit or laboratory placeholder.
  if (visitNum === 5) return generateDeliveryNarrative(visit, caseData);

  // Non-performed visits
  if (visit.is_not_performed) {
    const reason = visit.not_performed_reason || 'visit not conducted';
    if (/delivered/i.test(reason)) {
      const delDate = caseData?.delivery_date || caseData?.visits?.find(v => v.visit_number === 5)?.date;
      return `Visit ${visitNum} was not performed. The source-recorded reason was “Delivered.” No clinical assessment is attributed to Visit ${visitNum}.${delDate ? ` Delivery is documented on ${formatVisitDate(delDate)} and is presented under Visit 5.` : ' Delivery information is presented under Visit 5.'}`;
    }
    return `Visit ${visitNum} was not performed. The source-recorded reason was “${reason}.” No clinical measurements, laboratory results or imaging are attributed to this visit.`;
  }

  const safeBp = Array.isArray(visit.bp) ? visit.bp : [];
  const hasBp = safeBp.length > 0;
  
  const safeLabs = Array.isArray(visit.labs) ? visit.labs : [];
  const hasLabs = safeLabs.filter(l => l?.value != null).length > 0;
  
  const hasVitals = Boolean(visit.vitals?.bp || visit.vitals?.hr || visit.vitals?.weight);
  
  const safeObs = Array.isArray(visit.observations) ? visit.observations : [];
  if (!hasBp && !hasLabs && !hasVitals && !visit.date && safeObs.length <= 1) {
    return `Visit ${visitNum} — no clinical data was collected or mapped for this scheduled assessment.`;
  }

  const paragraphs = [];
  const dateStr = visit.date ? formatVisitDate(visit.date) : 'date not documented';
  const gaStr = formatGa(visit.gestationalLabel);
  const symptoms = extractSymptoms(visit);
  const meds = extractMedications(visit);

  // Include global home medications from the case data alongside any visit-specific ones
  const safeMedications = Array.isArray(caseData?.medications) ? caseData.medications : [];
  const homeMeds = safeMedications.map(m => {
    let name = m;
    if (typeof m === 'object') name = m.description || m.name || m.medication || '';
    return cleanPhpString(name);
  }).filter(m => m && !/^(yes|no|true|false|none|not applicable|not documented|not done|n\/a|unspecified medication)$/i.test(m));
  
  const allMeds = [...new Set([...meds, ...homeMeds])];

  // ── Visit 1: Screening ──────────────────────────────────────────────────────
  if (visitNum === 1) {
    return generateScreeningNarrative(visit, caseData);
    // Demographics are already shown in PatientHistoryPanel, so the visit
    // narrative focuses on the clinical presentation at screening
    const age = caseData?.age || caseData?.risk_summary?.age || caseData?.history?.baseline?.find?.(f => f.field_key === 'age')?.value;
    const gravida = caseData?.risk_summary?.gravidity ?? caseData?.gravidity;
    const parity = caseData?.risk_summary?.parity ?? caseData?.parity ?? 0;
    const misc = caseData?.risk_summary?.miscarriages ?? caseData?.miscarriages ?? 0;
    const chips = Array.isArray(caseData?.risk_summary?.chips) ? caseData.risk_summary.chips : [];
    // Extract and format medical conditions
    const safeCond = Array.isArray(caseData?.medical_conditions) ? caseData.medical_conditions : [];
    const medCond = safeCond.map(c => {
      let name = c;
      let duration = '';
      if (typeof c === 'object') {
         name = c.name || c.condition || c.diagnosis || '';
         duration = c.onset_year || c.start_date || c.duration || '';
      }
      name = cleanPhpString(name);
      if (!name || /^(none|no|n\/a)$/i.test(name)) return null;
      return duration ? `${name} (since ${duration})` : name;
    }).filter(Boolean);

    const conditionMap = {
      'prior gestational htn': 'prior gestational hypertension',
      'pre-existing chronic htn': 'chronic hypertension',
    };
    const chipsConditions = chips
      .filter(c => !/nulliparous|age/i.test(c))
      .map(c => conditionMap[String(c).trim().toLowerCase()] || c);
    const allConditions = [...new Set([...chipsConditions, ...medCond])];

    // Let the shared demographic formatter render the medical-history clause
    // once; medication details are appended separately below.
    let opening = buildDemographicString(age, gravida, parity, misc, allConditions.length ? allConditions : null);
    if (gaStr) {
      opening = opening.replace('screening', `screening at an initial gestational age of ${gaStr}`);
    } else {
      if (!opening.endsWith('.')) opening += '.';
    }

    // Medications and Conditions
    if (allMeds.length) {
      if (allMeds.length) {
        opening += ` Current medications include ${allMeds.join(', ')}.`;
      }
    }

    paragraphs.push(opening);
  }

  if ([2, 3, 4].includes(visitNum)) {
    return generateAntenatalFollowUpNarrative(visit, visitNum);
  }

  if (visitNum === 6) {
    return generatePostpartumNarrative(visit, caseData);
  }

  // ── Visit 5: Delivery ───────────────────────────────────────────────────────
  if (visitNum === 5) {
    const delMode = firstEvidence(visit, ['delivery_mode', 'type_of_delivery']);
    const delIndication = firstEvidence(visit, ['indication', 'reason_for_cesarean_section']);
    const rawDelGa = firstEvidence(visit, ['ega_delivery', 'ga_at_delivery', 'ga_weeks']);
    const delGa = rawDelGa ? (String(rawDelGa).toLowerCase().includes('week') ? rawDelGa : `${rawDelGa} weeks`) : (gaStr || 'gestational age not documented');
    const ebl = firstEvidence(visit, ['ebl_ml', 'estimated_blood_loss']);
    const hospitalStay = firstEvidence(visit, ['hospital_stay', 'delivery_outcome']);
    const matStatus = firstEvidence(visit, ['health_status_description', 'health_status', 'maternal_outcome']);
    const babyOutcome = firstEvidence(visit, ['pregnancy_outcome', 'newborn_status']);
    const babySex = firstEvidence(visit, ['neonatal_gender', 'gender']);
    const babyWeight = firstEvidence(visit, ['newborn_weight_g', 'birth_weight']);
    const babyLength = firstEvidence(visit, ['neonatal_length', 'length']);
    const babyHc = firstEvidence(visit, ['neonatal_hc', 'head_circumference']);
    const babyHr = firstEvidence(visit, ['neonatal_heart_rate']);
    const babyResp = firstEvidence(visit, ['neonatal_respiratory_rate']);
    const apgar1 = firstEvidence(visit, ['apgar_1m', 'apgar_score_at_1_minute']);
    const apgar5 = firstEvidence(visit, ['apgar_5m', 'apgar_score_at_5_minutes']);
    const bComp = firstEvidence(visit, ['birth_complications', 'congenital_anomalies']);
    const nicu = firstEvidence(visit, ['neonatal_icu_admission', 'nicu_admission']);
    const feeding = firstEvidence(visit, ['feeding_type', 'feeding']);

    let delPara = `The participant was admitted for delivery at ${delGa}.`;
    if (delMode) {
      delPara = `The participant was admitted at ${delGa} for ${/elective|scheduled/i.test(delMode) ? 'an elective' : 'a'} ${delMode}`;
      if (delIndication) delPara += ` indicated by ${delIndication}`;
      delPara += '. ';
    } else {
      delPara += ' ';
    }
    
    // Add Vitals if present
    const vitParts = [];
    if (visit.vitals?.bp) vitParts.push(`blood pressure ${formatWithUnit(visit.vitals.bp, 'mmHg')}`);
    if (visit.vitals?.hr) vitParts.push(`heart rate ${formatWithUnit(visit.vitals.hr, 'bpm')}`);
    if (vitParts.length) {
      delPara += `Pre-delivery vitals included ${vitParts.join(' and ')}. `;
    }

    // Maternal Outcomes
    const matParts = [];
    if (matStatus) matParts.push(`postpartum status was ${matStatus}`);
    if (ebl) matParts.push(`estimated blood loss was ${formatWithUnit(ebl, 'mL')}`);
    if (hospitalStay && !isNaN(Number(hospitalStay))) matParts.push(`hospital stay duration was ${hospitalStay} day(s)`);
    if (matParts.length) {
      delPara += `Maternal ${matParts.join(', and ')}. `;
    }

    // Neonatal Outcomes
    if (babyWeight || babyOutcome || babySex) {
      let neo = `A ${babyOutcome || 'neonate'}`;
      if (babySex) neo += ` (${babySex})`;
      neo += ` was delivered`;
      
      const anthro = [];
      if (babyWeight) anthro.push(`birth weight ${formatWithUnit(babyWeight, 'g', '')}`);
      if (babyLength) anthro.push(`length ${formatWithUnit(babyLength, 'cm')}`);
      if (babyHc) anthro.push(`head circumference ${formatWithUnit(babyHc, 'cm')}`);
      if (anthro.length) neo += ` with a ${anthro.join(', ')}`;
      neo += `. `;

      if (apgar1 && apgar5) {
        neo += `Apgar scores were ${apgar1} and ${apgar5} at 1 and 5 minutes respectively. `;
      }
      
      const neoVitals = [];
      if (babyHr) neoVitals.push(`heart rate ${formatWithUnit(babyHr, 'bpm')}`);
      if (babyResp) neoVitals.push(`respirations ${formatWithUnit(babyResp, 'bpm')}`);
      if (neoVitals.length) neo += `Newborn vitals included ${neoVitals.join(' and ')}. `;

      if (bComp && !/^(no|none|false)$/i.test(bComp)) {
        neo += `Birth complications included ${bComp}. `;
      } else {
        neo += `No birth complications were noted. `;
      }
      
      if (nicu) {
        const admitted = /^(yes|true)$/i.test(String(nicu));
        neo += admitted ? `The neonate required NICU admission. ` : `The neonate did not require NICU admission. `;
      }
      if (feeding) neo += `Feeding method: ${feeding}.`;
      
      delPara += neo;
    }

    paragraphs.push(delPara.trim());

    return paragraphs.join('\n\n');
  }

  // ── Visit 6: Postpartum ─────────────────────────────────────────────────────
  else if (visitNum === 6) {
    let ppOpening = `Approximately four weeks postpartum, the participant returned for her final study follow-up.`;
    if (symptoms.length) {
      ppOpening += ` She reported ${symptoms.join(', ')}.`;
    } else {
      ppOpening += ` Her postnatal clinical recovery was unremarkable.`;
    }
    paragraphs.push(ppOpening);
  }

  // ── Visits 2-4: Antenatal follow-ups ────────────────────────────────────────
  else {
    let followUp = `The participant presented for a routine follow-up assessment`;
    if (gaStr) followUp += ` at ${gaStr} gestation`;
    followUp += '.';
    if (symptoms.length > 0) {
      followUp += ` She reported ${symptoms.join(', ')}.`;
    }
    if (allMeds.length) {
      followUp += ` Active pharmacological management included ${allMeds.join(', ')}.`;
    }
    paragraphs.push(followUp);
  }

  // ── Pack Physical, Urinalysis, Sonography into FDA Prose ────────────────────
  if (visitNum !== 5) {
    let physicalProse = '';
    
    // Extract specific physical examination system findings if they exist (pe_ prefix)
    const peFindings = [];
    if (Array.isArray(visit.observations)) {
      visit.observations.forEach(o => {
        if (o?.canonicalVariable && o.canonicalVariable.startsWith('pe_') && !o.canonicalVariable.startsWith('pe_symptom')) {
          const sys = o.canonicalVariable.replace('pe_', '').replace(/_/g, ' ');
          const val = String(o.value || '').trim();
          if (val && !/^(not done|unknown|unspecified|n\/a|none)$/i.test(val)) {
             peFindings.push(`${sys.charAt(0).toUpperCase() + sys.slice(1)} - ${val}`);
          }
        }
      });
    }

    let physStatus = firstEvidence(visit, ['health_status_description', 'health_status', 'maternal_outcome', 'physical_exam']);
    if (!physStatus && peFindings.length > 0) {
      physStatus = peFindings.some(f => /abnormal/i.test(f)) ? 'Abnormal' : 'Normal';
    }
    
    if (peFindings.length > 0) {
      const abnormalFindings = peFindings.filter(f => /abnormal|yes/i.test(f));
      if (abnormalFindings.length > 0) {
        physicalProse += `Physical assessment indicated abnormal findings (${abnormalFindings.join(', ')}). `;
      } else {
        physicalProse += `Physical assessment indicated that all systems were normal. `;
      }
    } else if (physStatus) {
      physicalProse += `Physical assessment indicated: ${physStatus}. `;
    }

    const vitParts = [];
    if (visit.vitals?.bp) vitParts.push(`blood pressure ${formatWithUnit(visit.vitals.bp, 'mmHg')}`);
    if (visit.vitals?.hr) vitParts.push(`heart rate ${formatWithUnit(visit.vitals.hr, 'bpm')}`);
    if (visit.vitals?.temp) vitParts.push(`temperature ${formatWithUnit(visit.vitals.temp, '°C', '')}`);
    if (visit.vitals?.weight) vitParts.push(`weight ${formatWithUnit(visit.vitals.weight, 'kg')}`);
    
    if (vitParts.length) {
      physicalProse += `On physical examination, ${vitParts.join(', ')}. `;
    }

    const protRows = Array.isArray(visit?.proteinuria) ? visit.proteinuria : [];
    if (protRows.length > 0) {
      const protParts = [];
      for (const p of protRows) {
        const val = String(p?.value ?? '').trim();
        if (/negative/i.test(val)) {
          if (!protParts.includes('negative for protein')) protParts.push('negative for protein');
        } else if (val) {
          const entry = `${val} protein`;
          if (!protParts.includes(entry)) protParts.push(entry);
        }
      }
      if (protParts.length) {
        physicalProse += `Dipstick urinalysis was ${protParts.join(' and ')}. `;
      }
    }

    if (visitNum < 5) {
      if (visit.sonography) {
        const s = visit.sonography;
        const ega = s.ega !== 'unknown' ? s.ega : (visit.gestationalLabel || 'unknown');
        const presentation = s.presentation !== 'unknown' ? s.presentation : null;
        const fhr = s.fhr !== 'not documented' ? s.fhr : null;
        const efw = s.efwRaw !== 'not documented' ? s.efwRaw : null;
        const afi = s.afiRaw !== null ? s.afiRaw : 'not documented';
        const cervical = s.cervicalLength !== 'not documented' ? s.cervicalLength : 'not documented';
        
        const documentedDetails = [];
        if (presentation) documentedDetails.push(`in ${presentation} presentation`);
        if (fhr) documentedDetails.push(`with a foetal heart rate of ${fhr}`);
        if (efw) documentedDetails.push(`an estimated foetal weight of ${efw}`);

        const missingDetails = [];
        if (!presentation) missingDetails.push('fetal presentation');
        if (!fhr) missingDetails.push('fetal heart rate');
        if (!efw) missingDetails.push('estimated fetal weight');

        let usStr = `Obstetric ultrasound at ${ega} gestation demonstrated a single viable foetus`;
        if (documentedDetails.length) {
          usStr += ` ${documentedDetails.length === 1
            ? documentedDetails[0]
            : `${documentedDetails.slice(0, -1).join(', ')}, and ${documentedDetails[documentedDetails.length - 1]}`}.`;
        } else {
          usStr += '.';
        }
        if (missingDetails.length) {
          const missingText = missingDetails.length === 1
            ? missingDetails[0]
            : `${missingDetails.slice(0, -1).join(', ')}, and ${missingDetails[missingDetails.length - 1]}`;
          usStr += ` ${missingText.charAt(0).toUpperCase() + missingText.slice(1)} ${missingDetails.length === 1 ? 'was' : 'were'} not documented.`;
        }
        const usFindings = [];
        if (s.afiRaw) {
          if (/normal/i.test(s.afiRaw)) {
            usFindings.push('normal amniotic fluid volume');
          } else if (/cm/i.test(s.afiRaw)) {
            usFindings.push(`an amniotic fluid index (AFI) of ${s.afiRaw}`);
          } else {
            usFindings.push(`amniotic fluid volume noted as ${s.afiRaw}`);
          }
        }
        if (s.cervicalLength && s.cervicalLength !== 'not documented') {
          usFindings.push(`a cervical length of ${s.cervicalLength}`);
        }
        if (usFindings.length) {
          usStr += ` Ultrasound findings included ${usFindings.join(' and ')}.`;
        }
        if (s.anomalies) usStr += ` ${s.anomalies}.`;
        physicalProse += usStr;
        
        if (s.notes && s.notes !== 'None documented.') {
          physicalProse += ` Sonographer notes: ${s.notes}.`;
        }
      } else {
        physicalProse += ` No obstetric ultrasound is documented.`;
      }
    }
    
    // Append this clinical block directly to the opening paragraph for a unified FDA prose
    if (physicalProse.trim()) {
       paragraphs[0] = paragraphs[0] + ' ' + physicalProse.trim();
    }
  }

  // ── Visit 6 infant status ───────────────────────────────────────────────────
  if (visitNum === 6) {
    const infantStatus = firstEvidence(visit, ['neonatal_outcome', 'newborn_disorder_status', 'infant_status']);
    if (infantStatus) {
      paragraphs[0] = paragraphs[0] + ` The infant's status was reported as ${infantStatus.toLowerCase()}.`;
    }
  }

  // ── Final Lab Statement ─────────────────────────────────────────────────────
  paragraphs.push('Lab results were recorded as presented below.');

  return paragraphs.join('\n\n');
}


// ═══════════════════════════════════════════════════════════════════════════════
// 2. OVERALL SUMMARY — FORM-ADJ-PROSE-v2.0
// ═══════════════════════════════════════════════════════════════════════════════

function numberedVisit(visits, number) {
  return visits.find((visit) => visit?.visit_number === number || new RegExp(`^V0?${number}$`, 'i').test(visit?.name || visit?.label || '')) || null;
}

function overallProteinValue(visit) {
  return usableEvidenceValue(visit, ['ua_protein', 'DIPSTICK_PROTEIN', 'UA_PROTEIN', 'PROTEINURIA']);
}

function overallDatingSentence(v1) {
  const scanDate = usableEvidenceValue(v1, ['dating_anchor_date', 'us_date']);
  const values = evidenceRows(v1, ['dating_anchor_ga'])
    .map((row) => num(literalRowValue(row)))
    .filter((value) => value != null);
  const weeks = values.find((value) => value >= 5) ?? null;
  const days = values.find((value) => value >= 0 && value < 7) ?? null;
  if (!scanDate) return '';
  let sentence = `Gestational dating was based on the ultrasound performed on ${formatVisitDate(scanDate)}`;
  if (weeks != null) sentence += ` at ${weeks} weeks${days != null ? ` and ${days} ${plural(days, 'day')}` : ''}`;
  return `${sentence}.`;
}

function overallHistorySentence(caseData) {
  const priorFields = [
    ['does_participant_have_any_history_of_raised_blood_pressure_during_pregnancy', 'raised blood pressure'],
    ['does_the_participant_have_any_history_of_preeclampsia_in_previous_pregnancies', 'pre-eclampsia'],
    ['does_the_participant_have_any_history_of_severe_preeclampsia_in_previous_pregnancies', 'severe pre-eclampsia'],
    ['does_the_participant_have_any_history_of_eclampsia_in_previous_pregnancies', 'eclampsia'],
    ['does_the_participant_have_any_history_of_hellp_in_previous_pregnancies', 'HELLP syndrome'],
    ['does_the_participant_have_any_history_of_iugr_in_previous_pregnancies', 'fetal growth restriction'],
  ].map(([key, label]) => ({ label, value: historyValue(caseData, [key], 'obstetric') }))
    .filter((item) => item.value != null);
  const positives = priorFields.filter((item) => /^yes$/i.test(item.value)).map((item) => item.label);
  if (positives.length) return `Her previous pregnancy history included ${naturalList(positives)}.`;
  if (priorFields.length) return 'No previous hypertensive pregnancy complication was recorded.';
  return '';
}

function overallBaselineParagraph(v1, caseData) {
  const age = caseData?.age || caseData?.risk_summary?.age || historyValue(caseData, ['age'], 'baseline');
  const gravida = num(caseData?.risk_summary?.gravidity ?? caseData?.gravidity);
  const parity = num(caseData?.risk_summary?.parity ?? caseData?.parity);
  const gp = gravida != null && parity != null ? ` G${gravida}P${parity}` : '';
  const date = v1?.date ? ` on ${formatVisitDate(v1.date)}` : '';
  const ga = formatGa(v1?.gestationalLabel);
  let prose = `${age ? `A ${age}-year-old` : 'An adult'}${gp} participant entered the study${date}`;
  if (ga) prose += ` at ${screeningGaLabel(ga)} of gestation`;
  prose += '.';
  const history = overallHistorySentence(caseData);
  if (history) prose += ` ${history}`;
  const dating = overallDatingSentence(v1);
  if (dating) prose += ` ${dating}`;
  const bp = pairBpReadings(v1?.bp || [])[0];
  const protein = overallProteinValue(v1);
  if (bp?.initial || protein) {
    const findings = [];
    if (bp?.initial) findings.push(`blood pressure was ${bpStr(bp.initial.sbp, bp.initial.dbp)}`);
    if (bp?.recheck) findings.push(`the repeat was ${bpStr(bp.recheck.sbp, bp.recheck.dbp)}`);
    if (protein) findings.push(`urine protein was ${protein.toLowerCase()}`);
    prose += ` At screening, ${naturalList(findings)}.`;
  }
  return prose;
}

function proteinTrajectory(visits) {
  const points = visits.map((visit) => ({ visit, value: overallProteinValue(visit) })).filter((item) => item.value);
  const values = points.map((item) => item.value.toLowerCase()).filter((value, index, all) => index === 0 || value !== all[index - 1]);
  if (!values.length) return '';
  if (values.length === 1) return `Urine protein was ${values[0]} when assessed.`;
  return `Urine protein changed from ${values[0]} to ${naturalList(values.slice(1))} across the available antenatal assessments.`;
}

function overallAntenatalParagraph(visits) {
  const followUps = visits.filter((visit) => [2, 3, 4].includes(visit.visit_number) && !visit.is_not_performed);
  if (!followUps.length) return 'No intervening antenatal follow-up assessment was performed.';
  const withBp = followUps.filter((visit) => Array.isArray(visit.bp) && visit.bp.length);
  const elevated = withBp.find((visit) => visit.bp.some((reading) => reading.sbp >= 140 || reading.dbp >= 90));
  let prose = '';
  if (elevated) {
    const pair = pairBpReadings(elevated.bp)[0];
    const ga = formatGa(elevated.gestationalLabel);
    prose = `At ${ga ? screeningGaLabel(ga) : `Visit ${elevated.visit_number}`}, blood pressure was ${bpStr(pair.initial.sbp, pair.initial.dbp)}`;
    if (pair.recheck) prose += ` and ${bpStr(pair.recheck.sbp, pair.recheck.dbp)} on repeat`;
    const protein = overallProteinValue(elevated);
    if (protein) prose += `, with urine protein ${protein.toLowerCase()}`;
    prose += '.';
    const symptoms = symptomProse(elevated);
    if (symptoms) prose += ` ${symptoms}`;
    const later = followUps.filter((visit) => visit.visit_number > elevated.visit_number && visit.bp?.length).at(-1);
    if (later) {
      const laterPair = pairBpReadings(later.bp)[0];
      const laterProtein = overallProteinValue(later);
      prose += ` At the last subsequent antenatal assessment, blood pressure was ${bpStr(laterPair.initial.sbp, laterPair.initial.dbp)}`;
      if (laterProtein) prose += ` and urine protein was ${laterProtein.toLowerCase()}`;
      prose += '.';
    }
  } else if (withBp.length) {
    prose = 'No antenatal blood pressure of 140/90 mmHg or higher was recorded.';
    const protein = proteinTrajectory([numberedVisit(visits, 1), ...followUps].filter(Boolean));
    if (protein) prose += ` ${protein}`;
  } else {
    prose = 'No antenatal blood-pressure measurement was documented after screening.';
  }

  const abnormalLabs = followUps.flatMap((visit) => (visit.labs || [])
    .filter((lab) => ['abnormal', 'severe', 'conflicting'].includes(lab.evidence_state))
    .map((lab) => ({ ...lab, visit })))
    .slice(0, 3);
  if (abnormalLabs.length) {
    const findings = abnormalLabs.map((lab) => `${lab.label} ${lab.raw ?? lab.value}${lab.unit ? ` ${lab.unit}` : ''} on ${formatVisitDate(lab.observed_at || lab.visit.date)}`);
    prose += ` Source-recorded laboratory findings requiring review included ${naturalList(findings)}.`;
  }
  return prose;
}

function overallDeliveryParagraph(v5, caseData) {
  if (!v5 || !hasDeliveryRecord(v5)) return 'Source field unavailable; the delivery outcome cannot be determined from the supplied record.';
  const deliveryDate = literalEvidenceValue(v5, ['delivery_date'], /^date of delivery$/i);
  const mode = literalEvidenceValue(v5, ['delivery_mode', 'type_of_delivery']);
  const outcome = literalEvidenceValue(v5, ['pregnancy_outcome']);
  const stillbirth = /stillbirth|still birth|fetal death/i.test(outcome || '');
  const sourceGa = deliveryGaFromSource(v5);
  const derivedGa = gaParts(approvedDeliveryGa(caseData, deliveryDate));
  const ga = derivedGa || sourceGa;
  let prose = `${/caesarean|cesarean/i.test(mode || '') ? 'Caesarean' : /vaginal/i.test(mode || '') ? 'Vaginal' : 'A'} delivery`;
  prose += deliveryDate ? ` occurred on ${formatVisitDate(deliveryDate)}` : ' was recorded without an actual delivery date';
  if (ga) prose += ` at ${gaPhrase(ga)}`;
  prose += '.';

  const complicationStatus = evidenceValue(v5, ['delivery_outcome'], /^any complications at delivery/i);
  const complication = literalEvidenceValue(v5, ['delivery_outcome'], /delivery complications? description/i);
  if (/^yes$/i.test(complicationStatus || '') && complication) prose += ` The recorded delivery complication was ${complication.toLowerCase()}.`;
  else if (/^no$/i.test(complicationStatus || '') && !stillbirth) prose += ' No delivery complication was recorded.';

  if (stillbirth) prose += ' The pregnancy outcome was stillbirth.';
  const ebl = numericEvidenceValue(v5, ['ebl_ml', 'estimated_blood_loss']);
  const transfusion = evidenceValue(v5, ['blood_transfusion']);
  const infection = evidenceValue(v5, ['delivery_outcome'], /infection post-delivery/i);
  const stay = numericEvidenceValue(v5, ['delivery_outcome'], /how many days.*hospital/i);
  const maternal = [];
  if (ebl) maternal.push(`estimated maternal blood loss was ${Number(ebl).toLocaleString('en-US')} mL`);
  if (/^no$/i.test(transfusion || '')) maternal.push('no transfusion was recorded');
  if (/^no$/i.test(infection || '')) maternal.push('no postpartum infection was recorded');
  if (stay) maternal.push(`the hospital stay was ${stay} ${plural(Number(stay), 'day')}`);
  if (maternal.length) prose += ` Maternal outcome records show ${naturalList(maternal)}.`;

  if (!stillbirth) {
    const sexRaw = usableEvidenceValue(v5, ['neonatal_gender']);
    const sex = /^f$/i.test(sexRaw || '') ? 'female' : /^m$/i.test(sexRaw || '') ? 'male' : sexRaw?.toLowerCase();
    const weight = numericEvidenceValue(v5, ['newborn_weight_g']);
    const apgar1 = numericEvidenceValue(v5, ['apgar_1m']);
    const apgar5 = numericEvidenceValue(v5, ['apgar_5m']);
    const apgar10 = numericEvidenceValue(v5, ['apgar_10m']);
    if (sex || weight || apgar1 || apgar5 || apgar10 || /live|normal baby/i.test(outcome || '')) {
      prose += ` A liveborn${sex ? ` ${sex}` : ''} infant was recorded`;
      if (weight) prose += ` with a birth weight of ${Number(weight).toLocaleString('en-US')} g`;
      prose += '.';
      const apgarScores = [
        apgar1 != null ? `${apgar1} at 1 minute` : null,
        apgar5 != null ? `${apgar5} at 5 minutes` : null,
        apgar10 != null ? `${apgar10} at 10 minutes` : null,
      ].filter(Boolean);
      if (apgarScores.length) prose += ` Apgar scores were ${naturalList(apgarScores)}.`;
    }
  }
  return prose;
}

function overallPostpartumParagraph(v6) {
  if (!v6 || v6.is_not_performed) return '';
  let prose = `At postpartum follow-up${v6.date ? ` on ${formatVisitDate(v6.date)}` : ''}`;
  const pair = pairBpReadings(v6.bp || [])[0];
  const protein = overallProteinValue(v6);
  const findings = [];
  if (pair?.initial) findings.push(`blood pressure was ${bpStr(pair.initial.sbp, pair.initial.dbp)}`);
  if (pair?.recheck) findings.push(`${bpStr(pair.recheck.sbp, pair.recheck.dbp)} on repeat`);
  if (protein) findings.push(`urine protein was ${protein.toLowerCase()}`);
  prose += findings.length ? `, ${naturalList(findings)}.` : ', no blood-pressure or proteinuria result was documented.';
  const status = followUpStatusProse(v6);
  if (status) prose += ` ${status}`;
  const hospitalization = evidenceValue(v6, ['maternal_hospitalization']);
  const icu = evidenceValue(v6, ['maternal_icu']);
  if (/^no$/i.test(hospitalization || '') && /^no$/i.test(icu || '')) prose += ' No maternal hospitalization or intensive-care admission was recorded.';
  return prose;
}

function overallUnresolvedIssues(visits, caseData) {
  const issues = [];
  const v1 = numberedVisit(visits, 1);
  const canonicalAge = num(caseData?.age ?? caseData?.risk_summary?.age);
  const sourceAges = evidenceRows(v1, ['age'])
    .map((row) => num(literalRowValue(row)))
    .filter((value, index, all) => value != null && all.indexOf(value) === index);
  const conflictingAges = sourceAges.filter((value) => canonicalAge != null && value !== canonicalAge);
  if (conflictingAges.length) {
    issues.push(`the canonical age of ${canonicalAge} years conflicts with source-recorded age ${naturalList(conflictingAges.map((value) => `${value} years`))}`);
  }
  for (const visit of visits.filter((row) => [2, 3, 4].includes(row.visit_number))) {
    const newAe = evidenceValue(visit, ['new_adverse_events']);
    const changedAe = evidenceValue(visit, ['changed_adverse_events']);
    const aeDescription = usableEvidenceValue(visit, ['adverse_event_description', 'new_adverse_event_description', 'changed_adverse_event_description']);
    if ((/^yes$/i.test(newAe || '') || /^yes$/i.test(changedAe || '')) && !aeDescription) {
      issues.push(`Visit ${visit.visit_number} indicates an adverse event or change without a description`);
    }
    const efw = numericEvidenceValue(visit, ['efw', 'EFW'], /fetal weight/i);
    const efwStatus = evidenceValue(visit, ['efw', 'EFW'], /estimated.*fetal weight/i);
    const presentation = usableEvidenceValue(visit, ['fetal_presentation'], /description|provide/i);
    const presentationStatus = evidenceValue(visit, ['fetal_presentation'], /ultrasound presentation/i);
    const missingUltrasound = [];
    if (!efw && efwStatus && !/^(no|not done|not assessed|not available|n\/a)$/i.test(efwStatus)) missingUltrasound.push('estimated fetal weight');
    if (!presentation && /^yes$/i.test(presentationStatus || '')) missingUltrasound.push('fetal presentation');
    if (missingUltrasound.length) issues.push(`Visit ${visit.visit_number} marks ${naturalList(missingUltrasound)} as assessed or available without supplying the result`);
  }

  const v5 = numberedVisit(visits, 5);
  if (v5 && hasDeliveryRecord(v5)) {
    const deliveryDate = literalEvidenceValue(v5, ['delivery_date'], /^date of delivery$/i);
    const sourceGa = deliveryGaFromSource(v5);
    const derivedGa = gaParts(approvedDeliveryGa(caseData, deliveryDate));
    if (sourceGa && derivedGa && (sourceGa.weeks !== derivedGa.weeks || (sourceGa.days != null && sourceGa.days !== derivedGa.days))) {
      issues.push(`the delivery form GA of ${gaPhrase(sourceGa)} conflicts with the approved dating calculation of ${gaPhrase(derivedGa)}`);
    }
    const newbornGaRow = evidenceRows(v5, ['ega_delivery', 'GA_AT_DELIVERY'])
      .find((row) => /^gestational age$/i.test(String(row?.source?.field || row?.source_field_label || '')));
    const newbornGa = num(literalRowValue(newbornGaRow));
    const primaryGa = derivedGa || sourceGa;
    if (newbornGa != null && primaryGa && newbornGa !== primaryGa.weeks) {
      issues.push(`the Newborn Assessment GA of ${newbornGa} weeks conflicts with the delivery GA of ${gaPhrase(primaryGa)}`);
    }
  }
  if (!issues.length) return '';
  return `Unresolved source ${issues.length === 1 ? 'issue' : 'issues'}: ${naturalList(issues)}.`;
}

/**
 * Generate a concise chronological synthesis for the top of the case view.
 * Repeated measurements remain in the longitudinal panels; this prose retains
 * only the pivotal clinical course, outcomes, and material source questions.
 */
export function generateOverallNarrative(visits, caseData) {
  if (!visits?.length) return 'No participant data available for synthesis.';
  const sortedVisits = [...visits].sort((a, b) => (a.visit_number || 0) - (b.visit_number || 0));
  const v1 = numberedVisit(sortedVisits, 1);
  const v5 = numberedVisit(sortedVisits, 5);
  const v6 = numberedVisit(sortedVisits, 6);
  const clinicalCourse = [
    v1 ? overallBaselineParagraph(v1, caseData) : 'Baseline information was not available.',
    overallAntenatalParagraph(sortedVisits),
    overallDeliveryParagraph(v5, caseData),
    overallPostpartumParagraph(v6),
  ].filter(Boolean).join('\n\n');
  const unresolved = overallUnresolvedIssues(sortedVisits, caseData);
  return unresolved ? `${clinicalCourse}\n\n${unresolved}` : clinicalCourse;
}
