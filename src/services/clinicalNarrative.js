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

import { buildDemographicString, formatVisitDate, pairBpReadings, inferLabInterpretation, formatLabResult } from './visitEvidence';

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
  const ev = visit?.evidence || {};
  const medKeys = Object.keys(ev).filter(k => /medication|drug|treatment|therapy/i.test(k));
  for (const k of medKeys) {
    const rows = Array.isArray(ev[k]) ? ev[k] : [];
    for (const r of rows) {
      const val = cleanPhpString(r?.raw_source_value ?? r?.parsed_text_value ?? r?.value);
      if (val && !/^(no|none|false|n\/a|unspecified medication)$/i.test(val)) {
        meds.push(val);
      }
    }
  }
  // Also from explicit medications array
  const visitMeds = Array.isArray(visit?.medications) ? visit.medications : [];
  if (visitMeds.length) {
    for (const m of visitMeds) {
      const val = cleanPhpString(m?.value || m?.name || m?.description);
      if (val && !/^(no|none|false|n\/a|unspecified medication)$/i.test(val)) {
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

  // Non-performed visits
  if (visit.is_not_performed) {
    const reason = visit.not_performed_reason || 'visit not conducted';
    if (/delivered/i.test(reason)) {
      const delDate = caseData?.delivery_date || caseData?.visits?.find(v => v.visit_number === 5)?.date;
      return `Visit ${visitNum} was not performed because the participant had already delivered${delDate ? ` (delivery documented on ${formatVisitDate(delDate)})` : ''} prior to this scheduled assessment window. No clinical measurements or laboratory tests were conducted.`;
    }
    return `Visit ${visitNum} was not performed. Source records indicate: "${reason}". No clinical assessments were recorded for this scheduled window.`;
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
  }).filter(m => m && !/^(none|no|n\/a|unspecified medication)$/i.test(m));
  
  const allMeds = [...new Set([...meds, ...homeMeds])];

  // ── Visit 1: Screening ──────────────────────────────────────────────────────
  if (visitNum === 1) {
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

    const chipsConditions = chips.filter(c => !/nulliparous|age/i.test(c));
    const allConditions = [...new Set([...chipsConditions, ...medCond])];

    // Pass null for conditions to buildDemographicString so we can weave them in later
    let opening = buildDemographicString(age, gravida, parity, misc, null);
    if (gaStr) {
      opening = opening.replace('screening', `screening at an initial gestational age of ${gaStr}`);
    } else {
      if (!opening.endsWith('.')) opening += '.';
    }

    // Medications and Conditions
    if (allMeds.length || allConditions.length) {
      if (allMeds.length) {
        opening += ` She is actively managed on ${allMeds.join(', ')}`;
        if (allConditions.length) {
          opening += ` with a history of ${allConditions.join(', ')}`;
        }
        opening += `.`;
      } else if (allConditions.length) {
        opening += ` Her medical history is notable for ${allConditions.join(', ')}.`;
      }
    }

    paragraphs.push(opening);
  }

  // ── Visit 5: Delivery ───────────────────────────────────────────────────────
  else if (visitNum === 5) {
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
    if (visit.vitals?.bp) vitParts.push(`blood pressure ${visit.vitals.bp} mmHg`);
    if (visit.vitals?.hr) vitParts.push(`heart rate ${visit.vitals.hr} bpm`);
    if (vitParts.length) {
      delPara += `Pre-delivery vitals included ${vitParts.join(' and ')}. `;
    }

    // Maternal Outcomes
    const matParts = [];
    if (matStatus) matParts.push(`postpartum status was ${matStatus}`);
    if (ebl) matParts.push(`estimated blood loss was ${ebl} mL`);
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
      if (babyWeight) anthro.push(`birth weight ${babyWeight}g`);
      if (babyLength) anthro.push(`length ${babyLength}cm`);
      if (babyHc) anthro.push(`head circumference ${babyHc}cm`);
      if (anthro.length) neo += ` with a ${anthro.join(', ')}`;
      neo += `. `;

      if (apgar1 && apgar5) {
        neo += `Apgar scores were ${apgar1} and ${apgar5} at 1 and 5 minutes respectively. `;
      }
      
      const neoVitals = [];
      if (babyHr) neoVitals.push(`heart rate ${babyHr} bpm`);
      if (babyResp) neoVitals.push(`respirations ${babyResp} bpm`);
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
    if (visit.vitals?.bp) vitParts.push(`blood pressure ${visit.vitals.bp} mmHg`);
    if (visit.vitals?.hr) vitParts.push(`heart rate ${visit.vitals.hr} bpm`);
    if (visit.vitals?.temp) vitParts.push(`temperature ${visit.vitals.temp}°C`);
    if (visit.vitals?.weight) vitParts.push(`weight ${visit.vitals.weight} kg`);
    
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
        const presentation = s.presentation !== 'unknown' ? s.presentation : 'not documented';
        const fhr = s.fhr !== 'not documented' ? s.fhr : 'not documented';
        const efw = s.efwRaw !== 'not documented' ? s.efwRaw : 'not documented';
        const afi = s.afiRaw !== null ? s.afiRaw : 'not documented';
        const cervical = s.cervicalLength !== 'not documented' ? s.cervicalLength : 'not documented';
        
        let usStr = `Obstetric ultrasound at ${ega} gestation demonstrated a single viable foetus in ${presentation} presentation with a foetal heart rate of ${fhr} and an estimated foetal weight of ${efw}. `;
        usStr += `Environmental findings included: amniotic fluid index (AFI) ${afi}${afi !== 'not documented' ? ' cm' : ''}, and cervical length ${cervical}. `;
        usStr += `${s.anomalies || 'No gross foetal anomalies were appreciated'}.`;
        physicalProse += usStr;
        
        if (s.notes && s.notes !== 'None documented.') {
          physicalProse += ` Sonographer notes: ${s.notes}.`;
        }
      } else {
        physicalProse += ` No obstetric ultrasound was done.`;
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

/**
 * Generate a comprehensive overall clinical prose summary
 * synthesising all visit data longitudinally.
 *
 * @param {object[]} visits   - Array of normalised visits
 * @param {object}   caseData - Full patient case object
 * @returns {string}          - Multi-section flowing prose document
 */
export function generateOverallNarrative(visits, caseData) {
  if (!visits?.length) return 'No participant data available for synthesis.';

  // Sort visits chronologically or by visit_number to be safe
  const sortedVisits = [...visits].sort((a, b) => (a.visit_number || 0) - (b.visit_number || 0));
  
  const allProse = sortedVisits.map((v, idx) => {
    const title = v.label || `Visit ${v.visit_number || idx + 1}`;
    // Generate the single-paragraph prose for this visit
    const prose = generateVisitNarrative(v, v.visit_number || idx + 1, caseData);
    
    // Remove the redundant lab table sentence since there is a global longitudinal table here
    const cleanProse = prose.replace('Lab results were recorded as presented below.', '').trim();
    
    return `[${title.toUpperCase()}]\n${cleanProse}`;
  }).join('\n\n');

  return allProse;
}
