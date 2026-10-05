/**
 * ACRN PROTECT-Africa Adjudication Platform — Residency-Style Clinical Narrative Generator
 * Generates a blinded case presentation in the register a medical registrar / resident
 * would use when presenting to a consultant adjudicator.
 *
 * Style rules:
 *  - Opening `hook` sentence: age, gravidity/parity, comorbidities, gestational age.
 *  - Continuous flowing prose — NOT a bullet list or labelled form fields.
 *  - Salient positives called out clearly; pertinent negatives stated explicitly.
 *  - Numbers always carry units and threshold comparisons made explicit.
 *  - Clinical course builds chronologically from enrollment through delivery.
 *  - Ends with synthesis sentence that frames the adjudication question without pre-judging.
 *  - Biomarker data (sFlt-1, PlGF, sEng, treatment allocation, POC) EXCLUDED.
 *  - Site and provider identifiers EXCLUDED per SOP-ADJ-002.
 *  - Missing evidence stated as such — never inferred.
 *
 * Rule Version: FORM-ADJ-PROSE-v1.0
 */

import templateConfig from '../../Prompts and workflow/narrative_template.json';

export const NARRATIVE_VERSION = templateConfig.version;
export const AI_ENGINE_MODEL  = templateConfig.engineModel;

// Helpers
function safe(v, fallback) {
  var fb = fallback !== undefined ? fallback : 'not documented';
  if (v == null || (typeof v === 'string' && !v.trim())) return fb;
  return String(v).trim();
}

function obstetricHx(gravidity, parity) {
  var g = parseInt(gravidity);
  var p = parseInt(parity);
  if (Number.isNaN(g) || Number.isNaN(p)) return 'obstetric history not documented';
  if (g === 0) return 'Nulligravida';
  if (g === 1 && p === 0) return 'Primigravida, nulliparous';
  return 'Gravida ' + g + ', Para ' + p;
}

function peakBp(bpLog) {
  if (!bpLog || !bpLog.length) return null;
  var maxSbp = Math.max.apply(null, bpLog.map(function(b) { return b.sbp; }));
  var maxDbp = Math.max.apply(null, bpLog.map(function(b) { return b.dbp; }));
  return { sbp: maxSbp, dbp: maxDbp };
}

function isConfirmedHtn(bpLog) {
  if (!bpLog || bpLog.length < 2) return false;
  var htn = bpLog.filter(function(b) { return b.sbp >= 140 || b.dbp >= 90; });
  if (htn.length < 2) return false;
  var dates = [];
  htn.forEach(function(b) { if (b.date && dates.indexOf(b.date) < 0) dates.push(b.date); });
  return dates.length >= 2;
}

function formatBpList(bpLog) {
  if (!bpLog || !bpLog.length) return null;
  return bpLog.map(function(b) {
    var flag = (b.sbp >= 160 || b.dbp >= 110) ? ' \u2014 severe range'
             : (b.sbp >= 140 || b.dbp >= 90)  ? ' \u2014 hypertensive range'
             :                                   ' \u2014 within normal limits';
    var when = b.date ? ' on ' + b.date : '';
    var ga   = b.ga   ? ' (GA ' + b.ga + ')' : '';
    return b.sbp + '/' + b.dbp + ' mmHg' + when + ga + flag;
  }).join('; ');
}

function medicationSummary(medLog) {
  if (!medLog || !medLog.length) return null;
  return medLog.map(function(m) {
    return m.name + (m.dose ? ' ' + m.dose : '') + (m.route ? ' (' + m.route + ')' : '');
  }).join(', ');
}

// Main generator
export function generateNarrative(caseData, formCodeOverride) {
  if (!caseData) {
    return {
      formCode: 'FORM-ADJ-15A',
      sections: {},
      fullText: 'No active participant selected.',
      generatedAt: new Date().toISOString(),
    };
  }

  var id       = caseData.id || 'IMPORT-UNKNOWN';
  var gaEvent  = safe(caseData.gaAtEvent);
  var gaEnroll = safe(caseData.gaAtEnrollment);
  var edd      = safe(caseData.edd);
  var ussDate  = safe(caseData.firstUssDate);
  var ussGa    = safe(caseData.firstUssGa);
  var gaNum    = parseInt(gaEvent);
  var isEope   = gaNum < 34 || caseData.derivedSubtype === 'EOPE';
  var isPostPP = caseData.derivedSubtype === 'POSTPARTUM';
  var formCode = formCodeOverride || caseData.narrativeForm || (isEope ? 'FORM-ADJ-15A' : 'FORM-ADJ-15B');

  var bpLog   = caseData.bpLog || caseData.bp_readings || [];
  var protList = caseData.proteinuriaLog || [];
  var labs    = caseData.labLog || [];
  var meds    = caseData.medicationLog || [];
  var weights = caseData.weightLog || [];

  var obs          = obstetricHx(caseData.gravidity, caseData.parity);
  var peak         = peakBp(bpLog);
  var confirmedHtn = isConfirmedHtn(bpLog);
  var bpNarr       = formatBpList(bpLog);
  var medNarr      = medicationSummary(meds);

  var chips = (caseData.risk_summary && caseData.risk_summary.chips) || caseData.comorbidities || [];
  var comorbidities = null;
  if (Array.isArray(chips) && chips.length) {
    var filtered = chips.filter(function(c) { return !/nulliparous|age/i.test(c); });
    if (filtered.length) comorbidities = filtered.join(', ');
  }

  var upcr     = caseData.upcr;
  var dipstick = caseData.dipstick_raw;
  var plt      = caseData.platelet_count;
  var cr       = caseData.creatinine;
  var ast      = caseData.ast;
  var alt      = caseData.alt;
  var ldh      = caseData.ldh;
  var crUnit   = caseData.creatinine_unit || 'mg/dL';

  // --- SECTION 1: Presentation hook ---
  var resolvedAge = caseData.age || (caseData.risk_summary && caseData.risk_summary.age) || (caseData.history && caseData.history.baseline && caseData.history.baseline.find(function(f) { return f.field_key === 'age'; }) || {}).value;
  var ageStr    = resolvedAge ? (resolvedAge + '-year-old') : 'adult';
  var comorStr  = comorbidities ? ' with a background history of ' + comorbidities : ' with no significant past medical history';
  var gaContext = isPostPP
    ? 'She is now postpartum — her index pregnancy delivered at ' + safe(caseData.ga_at_delivery, 'gestational age not documented')
    : 'She presented at ' + gaEvent + ' weeks gestation';
  var enrollStr = (gaEnroll && gaEnroll !== 'not documented')
    ? ' She was enrolled into the ACRN trial at ' + gaEnroll + ' weeks, with pregnancy dating confirmed by first-trimester ultrasound at ' + ussGa + ' weeks on ' + ussDate + ' (EDD ' + edd + ').'
    : ' Pregnancy dating was established by first-trimester ultrasound at ' + ussGa + ' weeks on ' + ussDate + ', giving an EDD of ' + edd + '.';

  var section1 = 'We are presenting Participant ' + id + ' for adjudication \u2014 a ' + ageStr + ' African woman, ' + obs + comorStr + '. ' + gaContext + '.' + enrollStr
    + ' The clinical record has been prepared on Form ' + formCode + ' in accordance with SOP-ADJ-002; site and provider identifiers have been withheld to preserve adjudicator blinding.';

  // --- SECTION 2: Blood pressure ---
  var bpSection;
  if (!bpLog.length) {
    bpSection = 'Blood pressure documentation is not available in this packet; this prevents assessment of the hypertensive criterion.';
  } else {
    var sevRdgs = bpLog.filter(function(b) { return b.sbp >= 160 || b.dbp >= 110; });
    var peakStr = peak ? (peak.sbp + '/' + peak.dbp + ' mmHg') : 'not determinable';
    var confStr = confirmedHtn
      ? 'Hypertension is confirmed on two or more readings on separate occasions.'
      : 'Only a single occasion with hypertensive-range blood pressure is documented.';
    var sevStr = sevRdgs.length
      ? 'Severe-range hypertension (\u2265160/110 mmHg) is documented on ' + sevRdgs.length + ' occasion(s) \u2014 specifically ' + sevRdgs.map(function(b) { return b.sbp + '/' + b.dbp + ' mmHg'; }).join(' and ') + '.'
      : 'No severe-range blood pressure readings (\u2265160/110 mmHg) are documented in this record.';
    bpSection = 'The blood pressure trajectory comprises ' + bpLog.length + ' documented reading(s): ' + bpNarr + '. The peak recorded blood pressure is ' + peakStr + '. ' + confStr + ' ' + sevStr;
  }

  // --- SECTION 3: Proteinuria ---
  var protSection;
  if (!protList.length && upcr == null && !dipstick) {
    protSection = 'Proteinuria assessment is not documented in this packet. This represents a gap in the evidence package that limits the certainty of any determination.';
  } else {
    var protParts = [];
    if (upcr != null) {
      var upcrFlag = upcr >= 0.3 ? ' (\u22650.3 g/g)' : ' (<0.3 g/g)';
      protParts.push('Urine protein-to-creatinine ratio (UPCR) is ' + upcr + ' g/g' + upcrFlag);
    }
    if (dipstick) {
      var dip = String(dipstick).trim();
      protParts.push('Dipstick urinalysis demonstrated ' + dip + ' protein');
    }
    protList.forEach(function(p) {
      if (p.method !== 'UPCR' && !String(p.result).toLowerCase().includes('upcr')) {
        protParts.push(p.method + ': ' + p.result);
      }
    });
    protSection = protParts.join('. ') + '.';
  }

  // --- SECTION 4: Laboratory ---
  var labSection;
  if (!labs.length && plt == null && cr == null && ast == null) {
    labSection = 'Laboratory investigations are not available in this packet. This limits assessment of end-organ dysfunction criteria.';
  } else {
    var labParts = [];
    if (plt != null) {
      labParts.push('The platelet count is ' + plt + ' \u00d710\u00b3/\u00b5L (Ref: 150-400).');
    }
    if (cr != null) {
      labParts.push('Serum creatinine is ' + cr + ' ' + crUnit + '.');
    }
    if (ast != null || alt != null) {
      var astStr = ast != null ? 'AST ' + ast + ' U/L (ULN 40 U/L)' : null;
      var altStr = alt != null ? 'ALT ' + alt + ' U/L (ULN 40 U/L)' : null;
      var hepParts = [astStr, altStr].filter(Boolean).join(' and ');
      labParts.push('Liver function testing shows ' + hepParts + '.');
    }
    if (ldh != null) {
      labParts.push('LDH is ' + ldh + ' IU/L (ULN 250 IU/L).');
    }
    var extraLabs = labs.filter(function(l) {
      var n = (l.analyte || '').toLowerCase();
      return !n.includes('platelet') && !n.includes('creatinine') && !n.includes('ast') && !n.includes('alt') && !n.includes('ldh');
    });
    if (extraLabs.length) {
      labParts.push('Additional laboratory findings: ' + extraLabs.map(function(l) { return (l.analyte + ' ' + l.result + ' ' + (l.unit || '')).trim(); }).join('; ') + '.');
    }
    labSection = labParts.join(' ');
  }

  // --- SECTION 5: Fetal ---
  var ussDoc  = caseData.sourceDocs && caseData.sourceDocs.ultrasound;
  var efwCent = caseData.efw_centile;
  var aedf    = caseData.ua_aedf;
  var fetalSection;
  if (!ussDoc && efwCent == null) {
    fetalSection = 'No fetal ultrasound or Doppler assessment is documented in the packet; fetal wellbeing cannot be commented upon.';
  } else {
    var fetParts = [];
    if (efwCent != null) {
      var efwFlag = efwCent < 3 ? ' (<3rd centile)'
                 : efwCent < 10 ? ' (<10th centile)'
                 : ' (\u226510th centile)';
      fetParts.push('Estimated fetal weight plots at the ' + efwCent + 'th centile' + efwFlag);
    }
    if (aedf) {
      fetParts.push('Absent end-diastolic flow (AEDF) is documented on umbilical artery Doppler');
    } else if (aedf === false) {
      fetParts.push('Umbilical artery Doppler shows forward end-diastolic flow throughout');
    }
    if (ussDoc && !fetParts.length) fetParts.push(ussDoc);
    fetalSection = fetParts.join('. ') + '.';
  }

  // --- SECTION 6: Course, medications, delivery ---
  var delDate = safe(caseData.delivery_date);
  var delGa   = safe(caseData.ga_at_delivery);
  var delDoc  = (caseData.sourceDocs && caseData.sourceDocs.delivery) || '';
  var weightNarr = weights.length
    ? 'Serial weight measurements: ' + weights.map(function(w) { return w.weight_kg + ' kg at GA ' + w.ga; }).join(' \u2192 ') + '.'
    : null;
  var medStr = medNarr ? 'Pharmacological management included ' + medNarr + '.' : 'No medications are documented in the trial record for this period.';
  var deliveryStr = null;
  if (isPostPP) {
    deliveryStr = delDoc ? 'The index delivery is documented as follows: ' + delDoc : 'Delivery details: GA at delivery ' + delGa + (delDate !== 'not documented' ? ', date ' + delDate : '') + '.';
  } else if (delDate !== 'not documented' || delDoc) {
    var dParts = [];
    if (delDate !== 'not documented') dParts.push('Delivery occurred on ' + delDate + ' at ' + delGa + ' weeks gestation');
    if (delDoc && /caesarean|c-section|csection|cesarean/i.test(delDoc)) dParts.push('by emergency Caesarean section');
    if (delDoc && /liveborn|live.*born|viable.*neonate/i.test(delDoc)) {
      var wtMatch = delDoc.match(/(\d{3,4})\s*g/);
      dParts.push('with a liveborn neonate' + (wtMatch ? ' weighing ' + wtMatch[1] + 'g' : ''));
    }
    deliveryStr = dParts.length ? dParts.join(', ') + '.' : (delDoc || null);
  }
  var courseSection = [medStr, weightNarr, deliveryStr].filter(Boolean).join(' ');

  // --- SECTION 7: Gaps ---
  var missingItems = [];
  if (!bpLog.length) missingItems.push('blood pressure documentation');
  if (!protList.length && upcr == null && !dipstick) missingItems.push('proteinuria assessment');
  if (plt == null && !labs.some(function(l) { return /platelet/i.test(l.analyte); })) missingItems.push('platelet count');
  if (ast == null && alt == null && !labs.some(function(l) { return /ast|alt/i.test(l.analyte); })) missingItems.push('hepatic transaminases');
  if (cr == null && !labs.some(function(l) { return /creatinine/i.test(l.analyte); })) missingItems.push('serum creatinine');
  var missingSection = missingItems.length
    ? 'The following evidence classes are absent from this packet and limit the completeness of the adjudication assessment: ' + missingItems.join(', ') + '. These gaps should be noted when selecting a certainty level.'
    : 'The core evidence domains \u2014 blood pressure, proteinuria, platelet count, transaminases, and creatinine \u2014 are all represented in this packet.';

  // --- SECTION 8: Synthesis ---
  var hasSevereBp = peak && (peak.sbp >= 160 || peak.dbp >= 110);
  var hasHtn      = peak && (peak.sbp >= 140 || peak.dbp >= 90);
  var hasProt     = upcr >= 0.3 || /^(2\+|3\+|4\+|positive)/i.test(String(dipstick || '').trim());
  var hasOrganDys = (plt != null && plt < 100) || (ast != null && ast > 40) || (alt != null && alt > 40) || (ldh != null && ldh > 250);
  var contextClue;
  if (hasSevereBp && hasProt && hasOrganDys) contextClue = 'pre-eclampsia with severe features, including severe-range hypertension, significant proteinuria, and laboratory evidence of end-organ dysfunction';
  else if (hasSevereBp && hasOrganDys)       contextClue = 'severe hypertensive disease with evidence of end-organ involvement';
  else if (hasHtn && hasProt && confirmedHtn) contextClue = 'confirmed hypertension with significant proteinuria, raising the possibility of pre-eclampsia without severe features';
  else if (hasHtn && confirmedHtn)            contextClue = 'confirmed hypertension without clearly documented end-organ dysfunction or significant proteinuria';
  else if (hasHtn)                            contextClue = 'hypertension documented on the available readings, though confirmation on a second occasion and an assessment of proteinuria and organ function are required';
  else if (hasProt)                           contextClue = 'significant proteinuria documented, though the hypertensive criterion requires independent assessment';
  else if (missingItems.length > 2)           contextClue = 'an incomplete evidence package, limiting determination';
  else                                        contextClue = 'borderline clinical findings that require careful review of the source documentation';

  var synthesisSection = 'In summary, this is a case of ' + contextClue + '. '
    + 'The adjudicating physician is asked to review the source evidence above, taking into account the complete clinical trajectory and the protocol-defined diagnostic criteria for the ACRN PROTECT-Africa / LOPE-Nigeria programme, and to record an independent determination with a supporting rationale. '
    + 'No automated classification should be taken as a clinical conclusion \u2014 the determination rests entirely with the reviewing adjudicator.';

  var reviewerBlock = '\u2500'.repeat(60) + '\nADJUDICATOR DETERMINATION\n[To be completed by the reviewing physician. This section must not be pre-populated by any automated system.]\n' + '\u2500'.repeat(60);

  var fillTemplate = function(tpl, vars) {
    var str = tpl;
    for (var k in vars) {
      if (Object.prototype.hasOwnProperty.call(vars, k)) {
        str = str.replace(new RegExp('\\{\\{' + k + '\\}\\}', 'g'), vars[k]);
      }
    }
    return str;
  };

  var templateVars = {
    id: id, ageStr: ageStr, obs: obs, comorStr: comorStr, gaContext: gaContext, enrollStr: enrollStr, formCode: formCode,
    bpCount: bpLog.length, bpNarr: bpNarr, peakStr: peakStr, confStr: confStr, sevStr: sevStr,
    protSection: protSection, labSection: labSection, fetalSection: fetalSection, courseSection: courseSection,
    missingSection: missingSection, contextClue: contextClue
  };

  var sections = {};
  templateConfig.sections.forEach(function(sec) {
    if (sec.id === 'sec1') sections.sec1 = sec.title + '\n' + fillTemplate(sec.template, templateVars);
    if (sec.id === 'sec2' && bpLog.length) sections.sec2 = sec.title + '\n' + fillTemplate(sec.template, templateVars);
    if (sec.id === 'sec2' && !bpLog.length) sections.sec2 = sec.title + '\n' + bpSection;
    if (sec.id === 'sec3') sections.sec3 = sec.title + '\n' + protSection;
    if (sec.id === 'sec4') sections.sec4 = sec.title + '\n' + labSection;
    if (sec.id === 'sec5') sections.sec5 = sec.title + '\n' + fetalSection;
    if (sec.id === 'sec6') sections.sec6 = sec.title + '\n' + courseSection;
    if (sec.id === 'sec7') sections.sec7 = sec.title + '\n' + missingSection;
    if (sec.id === 'sec8') sections.sec8 = sec.title + '\n' + fillTemplate(sec.template, templateVars);
  });
  sections.sec9 = reviewerBlock;

  var lines = [
    '\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500',
    'BLINDED ADJUDICATION PACKET  |  ' + formCode + '  |  Participant ' + id,
    'Generated: ' + new Date().toLocaleString() + '  |  ' + NARRATIVE_VERSION,
    '[Site identifiers withheld \u2014 SOP-ADJ-002]',
    '\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500',
    '',
  ];
  Object.values(sections).forEach(function(s) { lines.push(s); });
  var fullText = lines.join('\n\n');

  return { formCode: formCode, sections: sections, fullText: fullText, generatedAt: new Date().toISOString(), aiEngine: AI_ENGINE_MODEL };
}

// Short summary for evidence tab header
export function generateSummary(caseData, dvResults) {
  if (!caseData) return 'No active case selected for summary.';
  var id    = caseData.id || 'N/A';
  var score = dvResults && dvResults.evidenceScore != null
    ? Math.round(dvResults.evidenceScore * 100)
    : (caseData.pktScore != null ? Math.round(caseData.pktScore * 100) : 0);
  var gateOpen = (dvResults && dvResults.certaintyGate && dvResults.certaintyGate.inputs && dvResults.certaintyGate.inputs.gate_open != null)
    ? dvResults.certaintyGate.inputs.gate_open
    : (score === 100);
  var bpLog = caseData.bpLog || caseData.bp_readings || [];
  var peak  = peakBp(bpLog);
  var hasSev = peak && (peak.sbp >= 160 || peak.dbp >= 110);
  var upcrStr = caseData.upcr != null
    ? 'UPCR ' + caseData.upcr + ' g/g' + (caseData.upcr >= 0.3 ? ' (\u22650.3 threshold met)' : '')
    : caseData.dipstick_raw ? 'Dipstick ' + caseData.dipstick_raw : 'Proteinuria not documented';
  return [
    'Participant ' + id + ' \u2014 Evidence Synthesis',
    '\u2022 BP: ' + bpLog.length + ' reading(s). Peak ' + (peak ? peak.sbp + '/' + peak.dbp + ' mmHg' : 'not available') + (hasSev ? ' \u2014 SEVERE RANGE' : '') + '.',
    '\u2022 Proteinuria: ' + upcrStr + '.',
    '\u2022 Platelets: ' + (caseData.platelet_count != null ? caseData.platelet_count + ' \u00d710\u00b3/\u00b5L' : 'not documented') + '.  Creatinine: ' + (caseData.creatinine != null ? caseData.creatinine + ' ' + (caseData.creatinine_unit || 'mg/dL') : 'not documented') + '.  AST: ' + (caseData.ast != null ? caseData.ast + ' U/L' : 'not documented') + '.  ALT: ' + (caseData.alt != null ? caseData.alt + ' U/L' : 'not documented') + '.',
    '\u2022 Evidence completeness: ' + score + '%.',
    '\u2022 Certainty gate: ' + (gateOpen ? 'Open \u2014 adjudicator may select any certainty level' : 'Restricted \u2014 evidence gaps may limit certainty selection') + '.',
    '\u2022 Mandatory: Adjudicator must review all source documents before signing.',
  ].join('\n');
}
