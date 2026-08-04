/**
 * ACRN PROTECT-Africa Adjudication Engine — Browser JavaScript Port
 * Rule Version: PROTECT-DV-2026.08-JS
 * 
 * Provides fast, offline-capable derivation in the browser.
 */

export const DV_ENGINE_VERSION = 'PROTECT-DV-2026.08-JS';

function dvResult(id, met, notAssessable, label, details, inputs = {}) {
  return {
    id,
    met,
    notAssessable,
    label,
    details,
    inputs,
    version: DV_ENGINE_VERSION
  };
}

export function ga_to_days(gaStr) {
  if (!gaStr || typeof gaStr !== 'string') return null;
  const m = gaStr.trim().match(/^(\d{1,2})(?:[\+\.](\d))?$/);
  if (!m) return null;
  const w = parseInt(m[1], 10);
  const d = m[2] ? parseInt(m[2], 10) : 0;
  if (d > 6) return null;
  return w * 7 + d;
}

export function parse_dipstick(val) {
  if (val == null) return null;
  const s = String(val).toLowerCase();
  if (s.includes('4+') || s.includes('++++')) return 4.0;
  if (s.includes('3+') || s.includes('+++')) return 3.0;
  if (s.includes('2+') || s.includes('++')) return 2.0;
  if (s.includes('1+') || s.includes('+')) return 1.0;
  if (s.includes('trace')) return 0.5;
  if (s.includes('neg') || s.includes('0')) return 0.0;
  const f = parseFloat(val);
  return isNaN(f) ? null : f;
}

export function evaluateDV02(bpLog = []) {
  if (!bpLog || bpLog.length === 0) {
    return dvResult('DV-02', false, true, 'NOT_ASSESSABLE', 'A confirmatory dated/timed BP or eligible severe-range recheck not documented');
  }
  const severe = bpLog.filter(b => (b.sbp >= 160 || b.dbp >= 110));
  if (severe.length > 0) {
    const maxS = Math.max(...severe.map(b => b.sbp));
    const maxD = Math.max(...severe.map(b => b.dbp));
    return dvResult('DV-02', true, false, 'SEVERE_HTN_MET', `Severe range BP documented (${maxS}/${maxD} mmHg).`, { maxS, maxD });
  }
  return dvResult('DV-02', false, false, 'NOT_MET', 'No severe-range BP (>=160/110) documented.');
}

export function evaluateDV03(bpLog = []) {
  if (!bpLog || bpLog.length < 2) {
    return dvResult('DV-03', false, true, 'NOT_ASSESSABLE', 'A confirmatory dated/timed BP or eligible severe-range recheck not documented');
  }
  const qual = bpLog.filter(b => (b.sbp >= 140 || b.dbp >= 90));
  if (qual.length < 2) {
    return dvResult('DV-03', false, false, 'NOT_MET', 'Fewer than 2 qualifying BP readings (>=140/90) documented.');
  }
  const dates = new Set(qual.map(b => b.date).filter(Boolean));
  const hasSevere = qual.some(b => b.sbp >= 160 || b.dbp >= 110);

  if (dates.size >= 2 || hasSevere) {
    return dvResult('DV-03', true, false, 'CONFIRMED_HTN_MET', `Confirmed HTN met across ${dates.size} distinct dates (Severe: ${hasSevere}).`, { datesCount: dates.size, hasSevere });
  }
  return dvResult('DV-03', false, false, 'NOT_MET', 'Multiple BPs on single date without severe recheck.');
}

export function evaluateDV07(caseData = {}) {
  const upcr = caseData.upcr != null ? parseFloat(caseData.upcr) : null;
  const dip = parse_dipstick(caseData.dipstick_raw || (caseData.proteinuriaLog?.[0]?.result));
  const protLog = caseData.proteinuriaLog || [];

  if (upcr == null && dip == null && protLog.length === 0) {
    return dvResult('DV-07', false, true, 'NOT_ASSESSABLE', 'A dated UPCR, 24-hour protein or dipstick result not documented');
  }

  const metUpcr = upcr != null && upcr >= 0.3;
  const metDip = dip != null && dip >= 2.0;

  if (metUpcr || metDip) {
    return dvResult('DV-07', true, false, 'PROTEINURIA_MET', `Significant proteinuria met (UPCR: ${upcr}, Dipstick: ${caseData.dipstick_raw || dip}).`, { upcr, dip });
  }
  return dvResult('DV-07', false, false, 'NOT_MET', 'Proteinuria thresholds (<0.3 UPCR, <2+ dipstick) not met.');
}

export function evaluateDV08(caseData = {}) {
  const plt = caseData.platelet_count != null ? parseFloat(caseData.platelet_count) : null;
  if (plt == null) {
    return dvResult('DV-08', false, true, 'NOT_ASSESSABLE', 'Dated platelet count with AST/ALT evidence not documented');
  }

  if (plt < 50) return dvResult('DV-08', true, false, 'CRITICAL_THROMBOCYTOPENIA', `Critical platelets ${plt} x10³/µL (<50).`, { tier: '<50' });
  if (plt < 100) return dvResult('DV-08', true, false, 'SEVERE_THROMBOCYTOPENIA', `Severe platelets ${plt} x10³/µL (<100).`, { tier: '<100' });
  if (plt < 150) return dvResult('DV-08', true, false, 'MILD_THROMBOCYTOPENIA', `Mild platelets ${plt} x10³/µL (<150).`, { tier: '<150' });

  return dvResult('DV-08', false, false, 'NORMAL_PLATELETS', `Normal platelets ${plt} x10³/µL.`, { tier: 'normal' });
}

export function evaluateDV10(caseData = {}) {
  const cr = caseData.creatinine != null ? parseFloat(caseData.creatinine) : null;
  if (cr == null) {
    return dvResult('DV-10', false, true, 'NOT_ASSESSABLE', 'Dated platelet count with AST/ALT evidence not documented');
  }
  const umol = Math.round(cr * 88.4);
  const met = cr > 1.1 || umol >= 90;
  if (met) {
    return dvResult('DV-10', true, false, 'RENAL_IMPAIRMENT_MET', `Elevated creatinine ${cr} mg/dL (${umol} µmol/L).`, { cr, umol });
  }
  return dvResult('DV-10', false, false, 'NOT_MET', `Normal creatinine ${cr} mg/dL (${umol} µmol/L).`);
}

export function evaluateDV11(caseData = {}) {
  const ast = caseData.ast != null ? parseFloat(caseData.ast) : null;
  const alt = caseData.alt != null ? parseFloat(caseData.alt) : null;
  if (ast == null && alt == null) {
    return dvResult('DV-11', false, true, 'NOT_ASSESSABLE', 'Dated platelet count with AST/ALT evidence not documented');
  }
  const met = (ast && ast > 40) || (alt && alt > 35);
  if (met) {
    return dvResult('DV-11', true, false, 'HEPATIC_DYSFUNCTION_MET', `Elevated transaminases (AST: ${ast}, ALT: ${alt}).`, { ast, alt });
  }
  return dvResult('DV-11', false, false, 'NOT_MET', `Normal transaminases (AST: ${ast}, ALT: ${alt}).`);
}

export function evaluateDV12(caseData = {}) {
  const ldh = caseData.ldh != null ? parseFloat(caseData.ldh) : null;
  if (ldh == null) {
    return dvResult('DV-12', false, true, 'NOT_ASSESSABLE', 'Dated platelet count with AST/ALT evidence not documented');
  }
  if (ldh >= 600) {
    return dvResult('DV-12', true, false, 'LDH_ELEVATED', `Elevated LDH ${ldh} IU/L (>=600).`, { ldh });
  }
  return dvResult('DV-12', false, false, 'NOT_MET', `Normal LDH ${ldh} IU/L.`);
}

export function evaluateDV14(caseData = {}, dvMap = {}) {
  const dv02 = dvMap['DV-02'];
  const dv08 = dvMap['DV-08'];
  const dv10 = dvMap['DV-10'];
  const dv11 = dvMap['DV-11'];
  const dv12 = dvMap['DV-12'];

  const severe = (dv02 && dv02.met) ||
    (dv08 && dv08.met && dv08.inputs.tier !== 'normal') ||
    (dv10 && dv10.met) ||
    (dv11 && dv11.met) ||
    (dv12 && dv12.met);

  if (severe) {
    return dvResult('DV-14', true, false, 'With severe features', 'Pre-eclampsia with severe features confirmed.', { severity: 'SEVERE_FEATURES' });
  }

  const dv03 = dvMap['DV-03'];
  const dv07 = dvMap['DV-07'];
  if (dv03 && dv03.met && dv07 && dv07.met) {
    return dvResult('DV-14', true, false, 'Without severe features', 'Pre-eclampsia without severe features.', { severity: 'STANDARD' });
  }

  return dvResult('DV-14', false, true, 'Severity requires review', 'Incomplete evidence for automated severity determination.', { severity: 'NOT_ASSESSABLE' });
}

export function evaluateDV26(caseData = {}) {
  const missing = [];
  let pts = 0;

  if (caseData.firstUssDate || caseData.lnmp || caseData.edd) pts += 1;
  else missing.push('Pregnancy dating evidence (dating method, anchor date and GA) not documented');

  const bpList = caseData.bpLog || caseData.bp_readings || [];
  if (bpList.length >= 2) pts += 1;
  else missing.push('A confirmatory dated/timed BP or eligible severe-range recheck not documented');

  if (caseData.upcr != null || caseData.dipstick_raw != null || (caseData.proteinuriaLog && caseData.proteinuriaLog.length > 0)) pts += 1;
  else missing.push('A dated UPCR, 24-hour protein or dipstick result not documented');

  const hasPlt = caseData.platelet_count != null || (caseData.labLog && caseData.labLog.some(l => l.analyte && l.analyte.toLowerCase().includes('platelet')));
  const hasAst = caseData.ast != null || caseData.alt != null || (caseData.labLog && caseData.labLog.some(l => l.analyte && (l.analyte.includes('AST') || l.analyte.includes('ALT'))));
  if (hasPlt && hasAst) pts += 1;
  else missing.push('Dated platelet count with AST/ALT evidence not documented');

  if (caseData.efw_centile != null || caseData.ua_aedf || caseData.ua_redf || (caseData.sourceDocs && caseData.sourceDocs.ultrasound)) pts += 1;
  else missing.push('Dated fetal growth/centile and Doppler assessment not documented');

  if (caseData.delivery_date || caseData.ga_at_delivery || (caseData.sourceDocs && caseData.sourceDocs.delivery)) pts += 1;
  else missing.push('Delivery record and gestational age at delivery not documented');

  const score = Math.round((pts / 6.0) * 100) / 100;
  return dvResult('DV-26', score === 1.0, false, score === 1.0 ? 'COMPLETE' : 'INCOMPLETE', `Evidence completeness: ${Math.round(score * 100)}%.`, { score, missing, packet_complete: score === 1.0 });
}

export function evaluateDV27(dv26Score, dv03, dv07, dv08, dv10, dv11) {
  const blocked_by = [];
  if (dv26Score < 1.0) blocked_by.push(`Incomplete evidence packet (DV-26 completeness ${Math.round(dv26Score * 100)}% < 100%)`);
  if (!dv03 || !dv03.met) blocked_by.push('Hypertension not confirmed (DV-03)');
  if (!((dv07 && dv07.met) || (dv08 && dv08.met) || (dv10 && dv10.met) || (dv11 && dv11.met))) {
    blocked_by.push('Neither proteinuria nor organ dysfunction confirmed');
  }

  const gate_open = blocked_by.length === 0;
  let max_certainty = 'Possible';
  if (gate_open) max_certainty = 'Definite';
  else if (dv26Score >= 0.5 && dv03 && dv03.met) max_certainty = 'Probable';

  return dvResult('DV-27', gate_open, false, gate_open ? 'GATE_OPEN' : 'GATE_RESTRICTED', `Certainty Gate: max allowed = '${max_certainty}'.`, { gate_open, max_certainty, blocked_by });
}

export function evaluateDV30(caseData, dvMap) {
  const reasons = [];
  if (dvMap['DV-02']?.met) reasons.push('Severe BP (>=160/110)');
  if (dvMap['DV-03']?.met) reasons.push('Confirmed HTN');
  if (dvMap['DV-07']?.met) reasons.push('Significant Proteinuria');
  if (dvMap['DV-14']?.met && dvMap['DV-14']?.label === 'With severe features') reasons.push('Severe Features');

  const triggered = reasons.length > 0;
  return dvResult('DV-30', triggered, false, triggered ? 'TRIGGERED' : 'NON_CASE', triggered ? `Triggered: ${reasons.join(', ')}` : 'Non-case / Borderline', { triggered, reasons });
}

export function runDvEngine(caseData) {
  const dvMap = {};
  const bpLog = caseData.bpLog || caseData.bp_readings || [];

  dvMap['DV-02'] = evaluateDV02(bpLog);
  dvMap['DV-03'] = evaluateDV03(bpLog);
  dvMap['DV-07'] = evaluateDV07(caseData);
  dvMap['DV-08'] = evaluateDV08(caseData);
  dvMap['DV-10'] = evaluateDV10(caseData);
  dvMap['DV-11'] = evaluateDV11(caseData);
  dvMap['DV-12'] = evaluateDV12(caseData);
  dvMap['DV-14'] = evaluateDV14(caseData, dvMap);

  const dv26 = evaluateDV26(caseData);
  dvMap['DV-26'] = dv26;

  const dv27 = evaluateDV27(dv26.inputs.score, dvMap['DV-03'], dvMap['DV-07'], dvMap['DV-08'], dvMap['DV-10'], dvMap['DV-11']);
  dvMap['DV-27'] = dv27;

  const dv30 = evaluateDV30(caseData, dvMap);
  dvMap['DV-30'] = dv30;

  return {
    version: DV_ENGINE_VERSION,
    dvMap,
    evidenceScore: dv26.inputs.score,
    missingAnchors: dv26.inputs.missing,
    certaintyGate: dv27,
    trigger: dv30,
  };
}
