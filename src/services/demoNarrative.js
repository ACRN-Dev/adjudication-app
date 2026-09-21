/**
 * ACRN PROTECT-Africa Adjudication Platform — Local & AI Narrative Generator
 * Generates 13-section blinded clinical narrative (FORM-ADJ-15A / FORM-ADJ-15B)
 * Rule Version: FORM-ADJ-LOCAL-v2.1
 */

export const NARRATIVE_VERSION = 'FORM-ADJ-LOCAL-v2.1';
export const AI_ENGINE_MODEL = 'ACRN-PROTECT-AI-v2.4 (Blinded Clinical LLM)';

const REVIEWER_PLACEHOLDER = `
---
SECTION 13 — REVIEWER / OAC DETERMINATION
[To be completed by the adjudicating physician during Step 3 review.
This section must not be pre-populated by any automated system.]
---`;

function _safe(v, fallback = '[Not documented — not assessable]') {
  if (v == null || (typeof v === 'string' && !v.trim())) {
    return fallback;
  }
  return String(v);
}

export function generateNarrative(caseData, formCodeOverride = null) {
  if (!caseData) {
    return {
      formCode: 'FORM-ADJ-15A',
      sections: {},
      fullText: 'No active participant selected.',
      generatedAt: new Date().toISOString(),
    };
  }

  const id = caseData.id || 'IMPORT-0099';
  const gaEvent = _safe(caseData.gaAtEvent);
  const gaEnroll = _safe(caseData.gaAtEnrollment);
  const edd = _safe(caseData.edd);
  const ussDate = _safe(caseData.firstUssDate);
  const ussGa = _safe(caseData.firstUssGa);
  const lnmp = _safe(caseData.lnmp);
  const trigger = _safe(caseData.trigger);

  const isEope = (parseInt(gaEvent) < 34) || (caseData.derivedSubtype === 'EOPE') || (caseData.derivedSubtype === 'POSTPARTUM');
  const formCode = formCodeOverride || caseData.narrativeForm || (isEope ? 'FORM-ADJ-15A' : 'FORM-ADJ-15B');

  const bpList = caseData.bpLog || caseData.bp_readings || [];
  const bpSummary = bpList.length > 0
    ? bpList.map(b => `${b.sbp}/${b.dbp} mmHg (${b.date ? b.date + ' ' : ''}GA ${b.ga || 'N/A'})`).join('; ')
    : '[Not documented — not assessable]';

  const maxSbp = bpList.length > 0 ? Math.max(...bpList.map(b => b.sbp)) : null;
  const maxDbp = bpList.length > 0 ? Math.max(...bpList.map(b => b.dbp)) : null;
  const severeBpDoc = (maxSbp >= 160 || maxDbp >= 110) ? 'Yes (≥160/110 mmHg severe-range criterion met)' : 'No severe-range BP documented';

  const protList = caseData.proteinuriaLog || [];
  const protSummary = protList.length > 0
    ? protList.map(p => `${p.method}: ${p.result}`).join('; ')
    : '[Not documented — not assessable]';

  const upcrVal = caseData.upcr != null ? `${caseData.upcr} g/g` : '[Not documented — not assessable]';
  const dipVal = caseData.dipstick_raw ? String(caseData.dipstick_raw) : '[Not documented — not assessable]';

  const labs = caseData.labLog || [];
  const findLab = (name) => {
    const l = labs.find(item => item.analyte && item.analyte.toLowerCase().includes(name.toLowerCase()));
    return l ? `${l.result} ${l.unit || ''}`.trim() : null;
  };

  const plt = caseData.platelet_count != null ? `${caseData.platelet_count} ×10³/µL` : (findLab('platelet') || '[Not documented — not assessable]');
  const cr = caseData.creatinine != null ? `${caseData.creatinine} ${caseData.creatinine_unit || 'mg/dL'}` : (findLab('creatinine') || '[Not documented — not assessable]');
  const ast = caseData.ast != null ? `${caseData.ast} U/L` : (findLab('ast') || '[Not documented — not assessable]');
  const alt = caseData.alt != null ? `${caseData.alt} U/L` : (findLab('alt') || '[Not documented — not assessable]');
  const ldh = caseData.ldh != null ? `${caseData.ldh} IU/L` : (findLab('ldh') || '[Not documented — not assessable]');

  const ussDoc = _safe(caseData.sourceDocs?.ultrasound);
  const delDoc = _safe(caseData.sourceDocs?.delivery);
  const delDate = _safe(caseData.delivery_date);
  const delGa = _safe(caseData.ga_at_delivery);

  const sections = {
    sec1: `SECTION 1 — PATIENT DEMOGRAPHICS & OBSTETRIC HISTORY
Participant ID: ${id}
Form: ${formCode} (Blinded Clinical Narrative)
Site / Provider: [Blinded per SOP-ADJ-002]
Gravidity: ${_safe(caseData.gravidity)} | Parity: ${_safe(caseData.parity)}
Dating Anchor: 1st-Trimester Ultrasound
First USS Date: ${ussDate}
GA at First USS: ${ussGa}
LMP Date: ${lnmp}
Estimated Delivery Date (EDD): ${edd}`,

    sec2: `SECTION 2 — CLINICAL CONTEXT
Triggering Event: ${trigger}
  Protocol Scope: PROTECT-Africa / LOPE-Nigeria
  The adjudicator must determine the diagnosis from the source evidence below; automated classifications are not presented as clinical conclusions.`,

    sec3: `SECTION 3 — CLINICAL COURSE (VISIT-BY-VISIT SUMMARY)
Blood Pressure Trajectory:
${bpSummary}
Peak BP Measurement: ${maxSbp != null ? maxSbp + '/' + maxDbp + ' mmHg' : '[Not documented — not assessable]'}
Severe Range BP (≥160/110): ${severeBpDoc}

Proteinuria & Renal Function:
UPCR Quantitation: ${upcrVal}
Dipstick Result: ${dipVal}
Assessment Summary: ${protSummary}

Haematology and Biochemistry:
Platelet Count: ${plt}
Creatinine: ${cr}
Transaminases: AST ${ast} | ALT ${alt}
LDH: ${ldh}
[Biomarker data strictly withheld per SOP-ADJ-002.]

Maternal Clinical Course:
Medication Log: ${caseData.medicationLog && caseData.medicationLog.length > 0 ? caseData.medicationLog.map(m => m.name + ' (' + m.dose + ')').join(', ') : '[Not documented — not assessable]'}
Weight Log: ${caseData.weightLog && caseData.weightLog.length > 0 ? caseData.weightLog.map(w => w.weight_kg + 'kg at GA ' + w.ga).join(' → ') : '[Not documented — not assessable]'}

Fetal Assessment (Growth and Doppler):
Ultrasound & Doppler Findings: ${ussDoc}
EFW Centile: ${caseData.efw_centile != null ? caseData.efw_centile + 'th centile' : '[Not documented — not assessable]'}
Umbilical Artery AEDF: ${caseData.ua_aedf ? 'Yes (AEDF documented)' : 'No / Not documented'}`,

    sec4: `SECTION 4 — DELIVERY SUMMARY & OUTCOMES
Delivery Date: ${delDate}
GA at Delivery: ${delGa}
Delivery Record: ${delDoc}
Maternal SAEs / Complications: ${delDoc.includes('Caesarean') ? 'Emergency Caesarean section indicated.' : '[Not documented — not assessable]'}
Neonatal Outcome: ${delDoc.includes('Liveborn') ? 'Liveborn neonate documented.' : '[Not documented — not assessable]'}`,

    sec5: `SECTION 5 — ADJUDICATION QUESTION
Evidence Completeness Score: ${caseData.pktScore != null ? Math.round(caseData.pktScore * 100) + '%' : '[Pending derivation]'}
${REVIEWER_PLACEHOLDER}`,
  };

  const fullText = Object.values(sections).join('\n\n');

  return {
    formCode,
    sections,
    fullText,
    generatedAt: new Date().toISOString(),
    aiEngine: AI_ENGINE_MODEL,
  };
}

export function generateSummary(caseData, dvResults) {
  if (!caseData) return 'No active case selected for summary.';

  const id = caseData.id || 'N/A';
  const score = dvResults?.evidenceScore != null ? Math.round(dvResults.evidenceScore * 100) : (caseData.pktScore != null ? Math.round(caseData.pktScore * 100) : 0);
  const gateOpen = dvResults?.certaintyGate?.inputs?.gate_open ?? (score === 100);

  const bpList = caseData.bpLog || caseData.bp_readings || [];
  const maxSbp = bpList.length > 0 ? Math.max(...bpList.map(b => b.sbp)) : null;
  const maxDbp = bpList.length > 0 ? Math.max(...bpList.map(b => b.dbp)) : null;

  return `CLINICAL EVIDENCE SYNTHESIS — Participant ${id}:
• BP Evidence: ${bpList.length} reading(s) documented. Peak BP: ${maxSbp != null ? maxSbp + '/' + maxDbp + ' mmHg' : 'Not documented'}.
• Proteinuria: ${caseData.upcr != null ? 'UPCR ' + caseData.upcr + ' g/g' : (caseData.dipstick_raw ? 'Dipstick ' + caseData.dipstick_raw : 'Not documented')}.
• Organ Dysfunction: Platelets ${caseData.platelet_count || 'N/A'}, Creatinine ${caseData.creatinine || 'N/A'}, AST ${caseData.ast || 'N/A'}, ALT ${caseData.alt || 'N/A'}.
• Evidence Completeness: ${score}% (6 evidence classes evaluated).
• Certainty restriction: ${gateOpen ? 'No automated restriction is displayed; verify the source evidence before selecting certainty.' : 'The available evidence may limit the certainty of the final determination.'}
• Mandatory Notice: Adjudicator must verify all raw source documents before placing signature.`;
}
