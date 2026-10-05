with open('src/services/visitEvidence.js', 'r', encoding='utf-8') as f:
    content = f.read()

target = """export function normalizeVisitEvidence(caseData = {}) {
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
    return {
      ...visit,
      id: visit.id || `${caseData.id || 'case'}-${visitLabel(visit, index)}`,
      label: visitLabel(visit, index),
      date: visit.date || visit.visit_date,
      gestationalLabel: (() => {
        const isPost = visit.visit_number === 6 || /eos|post|v06|visit 6/i.test(visit.name || visit.visit_code || '');
        if (isPost) return 'Postpartum (~4 weeks)';
        if (visit.ga && !/unclassifiable|null|undefined/i.test(String(visit.ga))) return String(visit.ga);
        if (visit.gestational_age && !/unclassifiable|null|undefined/i.test(String(visit.gestational_age))) return String(visit.gestational_age);
        if (visit.ga_days && visit.ga_days >= 45) {
          return `${Math.floor(visit.ga_days / 7)} weeks, ${visit.ga_days % 7} days`;
        }
        if (caseData.gaAtEvent && !/unclassifiable|null|undefined/i.test(String(caseData.gaAtEvent))) {
          return String(caseData.gaAtEvent);
        }
        return 'Antenatal';
      })(),"""

replacement = """export function resolveVisitDate(visit, index, caseData, bp = [], labs = [], proteinuria = [], otherResults = []) {
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
  const hasDate = Boolean(visit?.date || visit?.visit_date || visit?.visit_datetime);
  const hasClinicalData = hasBp || hasLabs || hasVitals || (visit?.proteinuria || []).length > 0;

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
    const perf = detectVisitPerformance({ ...visit, bp, labs, vitals, proteinuria });
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
      })(),"""

content_nl = content.replace('\r\n', '\n')
target_nl = target.replace('\r\n', '\n')
replacement_nl = replacement.replace('\r\n', '\n')

if target_nl in content_nl:
    updated = content_nl.replace(target_nl, replacement_nl, 1)
    with open('src/services/visitEvidence.js', 'w', encoding='utf-8') as f:
        f.write(updated)
    print('SUCCESSFULLY UPDATED visitEvidence.js')
else:
    print('TARGET NOT FOUND')
