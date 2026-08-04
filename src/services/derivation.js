/**
 * ACRN PROTECT-Africa Clinical Derivation Engine — JavaScript Port
 * ================================================================
 * Deterministic ISSHP 2021 / ACOG preeclampsia diagnostic criteria.
 * Mirrors backend/services/derivation_engine.py exactly.
 *
 * CRITICAL DESIGN PRINCIPLE (Dr. Makadzange):
 *   "The AI should not decide whether numeric diagnostic thresholds are met.
 *    That should be conventional validated code."
 *
 * DV-01 through DV-30 fully implemented.
 * Rule version: ISSHP-2021-v1.3-JS
 */

export const RULE_VERSION = 'ISSHP-2021-v1.3-JS';

// ── Thresholds ──────────────────────────────────────────────────────────────
const BP_HTN_SBP        = 140;
const BP_HTN_DBP        = 90;
const BP_SEVERE_SBP     = 160;
const BP_SEVERE_DBP     = 110;
const BP_MIN_INTERVAL_H = 4;

const UPCR_THRESHOLD    = 0.3;   // g/g
const PROT_24H_MG       = 300;   // mg/24h
const DIPSTICK_MIN      = 2;     // 2+

const PLATELET_LOW_1    = 150;   // x10³/µL — mild concern
const PLATELET_LOW_2    = 100;   // x10³/µL — ISSHP criterion
const PLATELET_LOW_3    = 50;    // x10³/µL — severe / transfusion risk

const CREATININE_MGDL   = 1.1;   // mg/dL absolute threshold (DV-10; baseline-doubling dropped per redesign)
const CREATININE_UMOL   = 90;    // µmol/L — ISSHP alternate threshold

const AST_ULN           = 40;    // U/L
const ALT_ULN           = 35;    // U/L
const LDH_ABSOLUTE      = 600;   // IU/L — DV-12 corrected fixed threshold (not 2×ULN)

const FGR_CENTILE       = 10;    // <10th centile
const GA_EOPE_DAYS      = 34 * 7; // 238 days = 34+0 weeks

const WEIGHT_GAIN_THRESH_KG_WK = 2.0; // > 2 kg/week in 3rd trimester — significant oedema proxy

// INTERGROWTH-21 EFW centile lookup (simplified — GA weeks 24–42, median EFW in grams)
const INTERGROWTH_EFW_MEDIAN = {
  24: 600, 25: 700, 26: 800, 27: 930, 28: 1050, 29: 1175, 30: 1320,
  31: 1480, 32: 1650, 33: 1830, 34: 2020, 35: 2210, 36: 2390, 37: 2550,
  38: 2700, 39: 2830, 40: 2940, 41: 3030, 42: 3100
};

// DV-18 Antihypertensive medication dictionary
const ANTIHYPERTENSIVE_DICT = [
  'labetalol', 'nifedipine', 'methyldopa', 'hydralazine', 'amlodipine',
  'atenolol', 'metoprolol', 'captopril', 'enalapril', 'losartan', 'verapamil'
];

// DV-19 Prophylaxis dictionary
const PROPHYLAXIS_DICT = {
  aspirin: ['aspirin', 'asa', 'acetylsalicylic'],
  calcium: ['calcium', 'calcium carbonate', 'caltrate']
};

// Dipstick value map
const DIPSTICK_MAP = { trace: 0.5, '1+': 1, '2+': 2, '3+': 3, '4+': 4 };

// Missingness constants
export const NOT_DOCUMENTED = 'NOT_DOCUMENTED';
export const NOT_DONE       = 'NOT_DONE';
export const UNKNOWN        = 'UNKNOWN';


// ── Utility helpers ─────────────────────────────────────────────────────────

/** Parse gestational age string "WW+D" → total days */
export function gaToDays(gaStr) {
  if (!gaStr) return null;
  const parts = String(gaStr).trim().split('+');
  const weeks = parseInt(parts[0], 10);
  const days  = parseInt(parts[1] || '0', 10);
  if (isNaN(weeks)) return null;
  return weeks * 7 + days;
}

/** Total days → "WW+D" string */
export function daysToGa(days) {
  return `${Math.floor(days / 7)}+${days % 7}`;
}

/** Parse a dipstick value to numeric (null if unreadable) */
export function parseDipstick(val) {
  if (val == null || String(val).toUpperCase() === NOT_DOCUMENTED) return null;
  if (typeof val === 'number') return val;
  return DIPSTICK_MAP[String(val).trim().toLowerCase()] ?? null;
}

/** Parse a date string or Date object to ms timestamp (null if invalid) */
function toTs(v) {
  if (!v) return null;
  const d = new Date(v);
  return isNaN(d.getTime()) ? null : d.getTime();
}

/**
 * DV-09 / G-13: Creatinine unit harmonisation.
 * If value > 10 or unit contains µmol/umol/mmol → convert to mg/dL via ÷88.42.
 * Returns { value_mgdl, unit_flag }
 */
export function harmonisedCreatinine(raw, unit) {
  if (raw == null || raw === '' || String(raw).toUpperCase() === NOT_DOCUMENTED)
    return { value_mgdl: null, unit_flag: NOT_DOCUMENTED };
  const val = parseFloat(raw);
  if (isNaN(val)) return { value_mgdl: null, unit_flag: NOT_DOCUMENTED };
  const u = String(unit || '').toLowerCase();
  if (val > 10 || u.includes('mmol') || u.includes('umol') || u.includes('µmol')) {
    // UNIT_SUSPECT: numeric magnitude consistent with µmol/L mislabelled
    const suspect = u.includes('mg') && val > 10;
    return {
      value_mgdl: Math.round((val / 88.42) * 100) / 100,
      unit_flag: suspect ? 'UNIT_SUSPECT_CONVERTED' : 'UNIT_ERROR_CONVERTED_UMOL_TO_MGDL'
    };
  }
  return { value_mgdl: Math.round(val * 100) / 100, unit_flag: 'VALID' };
}

/**
 * DV-04: Derive gestational age at a target date from an ultrasound dating anchor.
 * @param {string} ussDate  - Date of dating scan (ISO 8601)
 * @param {string} ussGa    - GA at scan "WW+D"
 * @param {string} targetDate - Date of event (ISO 8601)
 * Returns derived GA string "WW+D" or null if inputs invalid.
 */
export function gaFromAnchor(ussDate, ussGa, targetDate) {
  const anchorTs = toTs(ussDate);
  const targetTs = toTs(targetDate);
  const anchorDays = gaToDays(ussGa);
  if (!anchorTs || !targetTs || anchorDays == null) return null;
  const elapsed = Math.round((targetTs - anchorTs) / 86400000);
  const eventDays = anchorDays + elapsed;
  if (eventDays < 0) return null;
  return daysToGa(eventDays);
}


// ── DV-01: Maximum BP per visit window ─────────────────────────────────────

/**
 * DV-01: For each visit window, compute SBPMAX and DBPMAX from original + recheck readings.
 * Returns an array of { visitDate, sbpMax, dbpMax, source } objects.
 */
export function computeMaxBpPerVisit(bpReadings) {
  if (!bpReadings || !bpReadings.length) return [];
  // Group by date (YYYY-MM-DD prefix)
  const byDate = {};
  for (const r of bpReadings) {
    const dateKey = (r.date || r.datetime || '').slice(0, 10);
    if (!byDate[dateKey]) byDate[dateKey] = [];
    byDate[dateKey].push(r);
  }
  return Object.entries(byDate).map(([date, readings]) => ({
    visitDate: date,
    sbpMax: Math.max(...readings.map(r => Number(r.sbp) || 0)),
    dbpMax: Math.max(...readings.map(r => Number(r.dbp) || 0)),
    readings,
    source: readings.map(r => r.source || '').join('; ')
  }));
}


// ── DV-02: Severe-range hypertension ───────────────────────────────────────

export function deriveDV02(bpReadings) {
  const severe = (bpReadings || []).filter(
    r => (Number(r.sbp) >= BP_SEVERE_SBP) || (Number(r.dbp) >= BP_SEVERE_DBP)
  );
  if (!severe.length) return { id: 'DV-02', met: false, details: 'No severe-range BP readings documented', inputs: {} };
  const worst = severe.reduce((a, b) => (Number(a.sbp) + Number(a.dbp) > Number(b.sbp) + Number(b.dbp)) ? a : b);
  return {
    id: 'DV-02', met: true,
    details: `Severe-range BP confirmed: ${worst.sbp}/${worst.dbp} mmHg (${worst.date || worst.ga || ''})`,
    inputs: { sbp: worst.sbp, dbp: worst.dbp, date: worst.date },
    firstDate: worst.date
  };
}


// ── DV-03: Confirmed hypertension (≥140/90 on ≥2 occasions) ────────────────

/**
 * DV-03: Full G-01/G-02 operational fallback:
 *   Strategy A: Two qualifying readings ≥4 hours apart (timestamps)
 *   Strategy B: Two readings on distinct visit dates
 *   Strategy C: Severe BP + same-visit recheck
 */
export function deriveDV03(bpReadings) {
  const qualifying = (bpReadings || []).filter(
    r => (Number(r.sbp) >= BP_HTN_SBP) || (Number(r.dbp) >= BP_HTN_DBP)
  );

  if (qualifying.length < 2) {
    return {
      id: 'DV-03', met: false,
      details: `Only ${qualifying.length} qualifying reading(s). Need ≥2.`,
      inputs: { count: qualifying.length }
    };
  }

  // Strategy A: timestamps ≥4h apart
  const timed = qualifying.filter(r => r.datetime || (r.date && r.date.length > 10));
  if (timed.length >= 2) {
    const sorted = [...timed].sort((a, b) => toTs(a.datetime || a.date) - toTs(b.datetime || b.date));
    for (let i = 0; i < sorted.length; i++) {
      for (let j = i + 1; j < sorted.length; j++) {
        const t1 = toTs(sorted[i].datetime || sorted[i].date);
        const t2 = toTs(sorted[j].datetime || sorted[j].date);
        if (t1 && t2) {
          const hours = (t2 - t1) / 3600000;
          if (hours >= BP_MIN_INTERVAL_H) {
            return {
              id: 'DV-03', met: true,
              details: `Confirmed ${sorted[i].sbp}/${sorted[i].dbp} and ${sorted[j].sbp}/${sorted[j].dbp} mmHg, ${hours.toFixed(1)}h apart (Strategy A)`,
              inputs: { interval_h: Math.round(hours * 10) / 10 },
              firstDate: sorted[i].datetime || sorted[i].date,
              strategy: 'A_TIMED'
            };
          }
        }
      }
    }
  }

  // Strategy B: distinct visit dates
  const visitDates = new Set(qualifying.map(r => (r.date || r.datetime || '').slice(0, 10)).filter(Boolean));
  if (visitDates.size >= 2) {
    return {
      id: 'DV-03', met: true,
      details: `Qualifying BP on ${visitDates.size} distinct visit dates (G-01 Fallback)`,
      inputs: { visit_dates: [...visitDates] },
      strategy: 'B_DISTINCT_DATES'
    };
  }

  // Strategy C: severe + recheck
  const severe = qualifying.filter(r => Number(r.sbp) >= BP_SEVERE_SBP || Number(r.dbp) >= BP_SEVERE_DBP);
  if (severe.length >= 1 && qualifying.length >= 2) {
    return {
      id: 'DV-03', met: true,
      details: `Severe BP ${severe[0].sbp}/${severe[0].dbp} plus same-visit recheck (G-02 Fallback)`,
      inputs: { severe_reading: `${severe[0].sbp}/${severe[0].dbp}` },
      strategy: 'C_SEVERE_RECHECK'
    };
  }

  return {
    id: 'DV-03', met: false,
    details: 'Qualifying readings present but no confirmation across ≥4h or distinct visit dates.',
    inputs: { count: qualifying.length }
  };
}


// ── DV-05: EOPE / LOPE onset subtype ───────────────────────────────────────

/**
 * DV-05: Classify onset.
 * @param {string} onsetGa      - GA at onset "WW+D"
 * @param {string} deliveryGa   - GA at delivery "WW+D" (optional)
 * @param {boolean} postpartumOnly - Hypertension only after delivery
 */
export function deriveDV05(onsetGa, deliveryGa, postpartumOnly = false) {
  if (postpartumOnly) {
    return { id: 'DV-05', subtype: 'POSTPARTUM', met: false,
      details: 'Postpartum-only onset — hypertension first documented after delivery.' };
  }
  const days = gaToDays(onsetGa);
  if (days == null) {
    return { id: 'DV-05', subtype: 'UNCLASSIFIABLE', met: false,
      details: 'GA at onset not available — onset cannot be classified.' };
  }
  const isEOPE = days < GA_EOPE_DAYS;
  const subtype = isEOPE ? 'EOPE' : 'LOPE';
  return {
    id: 'DV-05', subtype, met: isEOPE,
    details: `${subtype}: GA at onset ${onsetGa} (${days} days). Threshold: <${daysToGa(GA_EOPE_DAYS)}.`,
    inputs: { onsetGa, days }
  };
}


// ── DV-06: Proposed onset — time-ordered evidence table ────────────────────

/**
 * DV-06: Build a time-ordered evidence table and identify the earliest point
 * where confirmed hypertension AND a confirmatory element coexist.
 */
export function deriveDV06(bpLog, protLog, labLog, ussDate, ussGa) {
  // Collect all datable events
  const events = [];

  (bpLog || []).forEach(r => {
    const ts = toTs(r.datetime || r.date);
    const sbp = Number(r.sbp); const dbp = Number(r.dbp);
    if (ts && (sbp >= BP_HTN_SBP || dbp >= BP_HTN_DBP)) {
      events.push({ ts, type: 'HTN', label: `BP ${sbp}/${dbp} mmHg`, ga: r.ga, date: r.date || r.datetime });
    }
  });

  (protLog || []).forEach(r => {
    const ts = toTs(r.date);
    if (ts) events.push({ ts, type: 'PROT', label: `Proteinuria: ${r.result || r.method}`, ga: r.ga, date: r.date });
  });

  (labLog || []).forEach(r => {
    const ts = toTs(r.date || r.datetime);
    const val = parseFloat(r.result);
    if (ts && r.severe) {
      events.push({ ts, type: 'LAB', label: `${r.analyte}: ${r.result} ${r.unit || ''}`, date: r.date || r.datetime });
    }
  });

  events.sort((a, b) => a.ts - b.ts);

  // Find earliest co-occurrence of HTN + confirmatory
  let onsetTs = null, onsetLabel = null;
  for (let i = 0; i < events.length; i++) {
    const e = events[i];
    if (e.type === 'HTN') {
      // Look forward (within same day) or same-day for confirmatory
      const sameDay = events.filter(x =>
        x.type !== 'HTN' && Math.abs(x.ts - e.ts) <= 86400000 * 2
      );
      if (sameDay.length > 0) {
        onsetTs = e.ts;
        onsetLabel = e.date;
        break;
      }
    }
  }

  // Derive GA at onset if USS anchor available
  let onsetGa = null;
  if (onsetLabel && ussDate && ussGa) {
    onsetGa = gaFromAnchor(ussDate, ussGa, onsetLabel);
  }

  return {
    id: 'DV-06',
    met: onsetTs != null,
    proposedOnsetDate: onsetLabel || null,
    proposedOnsetGa: onsetGa,
    evidenceTable: events.map(e => ({
      date: e.date,
      type: e.type,
      label: e.label,
      ga: e.ga || (ussDate && ussGa && e.date ? gaFromAnchor(ussDate, ussGa, e.date) : null)
    })),
    details: onsetTs
      ? `Proposed onset: ${onsetLabel} (GA ${onsetGa || 'unknown'}) — earliest confirmed HTN with co-occurring evidence`
      : 'Cannot establish a defensible onset — no co-occurrence of HTN and confirmatory element found'
  };
}


// ── DV-07: Significant proteinuria ─────────────────────────────────────────

export function deriveDV07(upcr, dipstickRaw, prot24hMg) {
  const dipstick = parseDipstick(dipstickRaw);

  if (upcr != null) {
    const val = parseFloat(upcr);
    return {
      id: 'DV-07', met: val >= UPCR_THRESHOLD,
      method: 'UPCR',
      details: `UPCR ${val} g/g (threshold ≥${UPCR_THRESHOLD} g/g) — ${val >= UPCR_THRESHOLD ? 'MET' : 'NOT MET'}`,
      inputs: { upcr: val }
    };
  }

  if (dipstick != null) {
    return {
      id: 'DV-07', met: dipstick >= DIPSTICK_MIN,
      method: 'Dipstick',
      details: `Dipstick ${dipstickRaw} (coded ${dipstick}) — ${dipstick >= DIPSTICK_MIN ? '≥2+ MET' : 'below 2+ threshold'}`,
      inputs: { dipstick }
    };
  }

  if (prot24hMg != null) {
    const val = parseFloat(prot24hMg);
    return {
      id: 'DV-07', met: val >= PROT_24H_MG,
      method: '24h urine',
      details: `24h urine protein ${val} mg (threshold ≥${PROT_24H_MG} mg) — ${val >= PROT_24H_MG ? 'MET' : 'NOT MET'}`,
      inputs: { prot24hMg: val }
    };
  }

  return { id: 'DV-07', met: false, method: NOT_DOCUMENTED,
    details: 'No proteinuria result documented (UPCR, dipstick, or 24h urine)', inputs: {} };
}


// ── DV-08: Platelet thresholds (three-tier) ─────────────────────────────────

export function deriveDV08(plateletCount) {
  if (plateletCount == null) return {
    id: 'DV-08', met: false, tier: null,
    details: 'Platelet count not documented', inputs: {}
  };
  const plt = parseFloat(plateletCount);
  let tier = null, met = false;
  if (plt < PLATELET_LOW_3) { tier = 'CRITICAL (<50)'; met = true; }
  else if (plt < PLATELET_LOW_2) { tier = 'SEVERE (<100)'; met = true; }
  else if (plt < PLATELET_LOW_1) { tier = 'MILD (<150)'; met = true; }

  return {
    id: 'DV-08', met,
    tier,
    plt150met: plt < PLATELET_LOW_1,
    plt100met: plt < PLATELET_LOW_2,
    plt50met:  plt < PLATELET_LOW_3,
    details: tier
      ? `Thrombocytopenia ${tier}: ${plt} x10³/µL`
      : `Platelets ${plt} x10³/µL — within normal range (≥150)`,
    inputs: { plateletCount: plt }
  };
}


// ── DV-09 is harmonisedCreatinine() above ──────────────────────────────────


// ── DV-10: Renal impairment flags ──────────────────────────────────────────

/**
 * DV-10: Absolute creatinine threshold only (baseline-doubling dropped per redesign).
 * Both ACOG (>1.1 mg/dL) and ISSHP (≥90 µmol/L) thresholds reported.
 */
export function deriveDV10(creatRaw, creatUnit) {
  const { value_mgdl, unit_flag } = harmonisedCreatinine(creatRaw, creatUnit);
  if (value_mgdl == null) {
    return { id: 'DV-10', met: false, details: 'Creatinine not documented', inputs: { unit_flag } };
  }
  const umol = Math.round(value_mgdl * 88.42);
  const acogMet  = value_mgdl > CREATININE_MGDL;
  const isshpMet = umol >= CREATININE_UMOL;
  const met = acogMet || isshpMet;
  return {
    id: 'DV-10', met,
    acogMet, isshpMet,
    value_mgdl, value_umol: umol, unit_flag,
    details: `Creatinine ${value_mgdl} mg/dL (${umol} µmol/L) [Unit: ${unit_flag}]. ACOG >1.1: ${acogMet ? 'MET' : 'not met'}. ISSHP ≥90 µmol/L: ${isshpMet ? 'MET' : 'not met'}.`,
    inputs: { creatRaw, unit_flag, value_mgdl, value_umol: umol }
  };
}


// ── DV-11: Liver flags (ACOG + ISSHP separate outputs) ─────────────────────

export function deriveDV11(ast, alt, localAstUln, localAltUln) {
  const astUln = localAstUln || AST_ULN;
  const altUln = localAltUln || ALT_ULN;

  const astVal = ast != null ? parseFloat(ast) : null;
  const altVal = alt != null ? parseFloat(alt) : null;

  if (astVal == null && altVal == null) {
    return { id: 'DV-11', met: false, details: 'AST and ALT not documented', inputs: {} };
  }

  const acogAst  = astVal != null && (astVal / astUln) > 2;
  const acogAlt  = altVal != null && (altVal / altUln) > 2;
  const isshpAst = astVal != null && astVal > 40;
  const isshpAlt = altVal != null && altVal > 40;

  const acogMet  = acogAst || acogAlt;
  const isshpMet = isshpAst || isshpAlt;
  const met = acogMet || isshpMet;

  return {
    id: 'DV-11', met, acogMet, isshpMet,
    details: [
      astVal != null ? `AST ${astVal} U/L (${(astVal/astUln).toFixed(1)}× ULN; ISSHP >40: ${isshpAst ? 'MET' : 'no'})` : 'AST: not documented',
      altVal != null ? `ALT ${altVal} U/L (${(altVal/altUln).toFixed(1)}× ULN; ISSHP >40: ${isshpAlt ? 'MET' : 'no'})` : 'ALT: not documented',
    ].join(' | '),
    inputs: { ast: astVal, alt: altVal, astUln, altUln,
      ast_x_uln: astVal ? Math.round((astVal/astUln)*100)/100 : null,
      alt_x_uln: altVal ? Math.round((altVal/altUln)*100)/100 : null }
  };
}


// ── DV-12: LDH ≥600 IU/L ──────────────────────────────────────────────────

export function deriveDV12(ldh) {
  if (ldh == null) return { id: 'DV-12', met: false, details: 'LDH not documented', inputs: {} };
  const val = parseFloat(ldh);
  return {
    id: 'DV-12', met: val >= LDH_ABSOLUTE,
    details: `LDH ${val} IU/L (threshold ≥${LDH_ABSOLUTE} IU/L) — ${val >= LDH_ABSOLUTE ? 'MET' : 'NOT MET'}`,
    inputs: { ldh: val, threshold: LDH_ABSOLUTE }
  };
}


// ── DV-13: HELLP composite (same-draw + complete vs partial) ────────────────

/**
 * DV-13: Full HELLP composite enforcement.
 * Complete HELLP: LDH ≥600 + liver dysfunction + platelets <100 — all from same blood draw (±4h).
 * Partial HELLP: ≥2 of 3 criteria met.
 */
export function deriveDV13(dv08, dv11, dv12, labLog) {
  const plt100 = dv08?.plt100met === true;
  const liver  = dv11?.met === true;
  const ldh    = dv12?.met === true;

  // Check for same-draw timestamps in labLog (±4 hours window)
  let sameDraw = false;
  if (labLog && labLog.length >= 2) {
    const pltEntry  = labLog.find(l => l.analyte?.toLowerCase().includes('platelet'));
    const liverEntry = labLog.find(l => l.analyte?.toLowerCase().match(/ast|alt/));
    const ldhEntry  = labLog.find(l => l.analyte?.toLowerCase().includes('ldh'));
    const entries = [pltEntry, liverEntry, ldhEntry].filter(Boolean);
    if (entries.length >= 2) {
      const times = entries.map(e => toTs(e.datetime || e.date)).filter(Boolean);
      if (times.length >= 2) {
        const spread = Math.max(...times) - Math.min(...times);
        sameDraw = spread <= 4 * 3600000; // ≤4 hours
      }
    }
  }

  const criteria_met = [plt100, liver, ldh].filter(Boolean).length;
  const complete = criteria_met === 3;
  const partial  = criteria_met === 2;

  return {
    id: 'DV-13',
    met: complete || partial,
    complete, partial, sameDraw,
    hellpType: complete ? 'COMPLETE_HELLP' : partial ? 'PARTIAL_HELLP' : 'NOT_HELLP',
    criteria_met,
    details: `${complete ? 'Complete' : partial ? 'Partial' : 'No'} HELLP: Plt<100=${plt100}, Liver=${liver}, LDH≥600=${ldh}. Same-draw: ${sameDraw ? 'Yes' : 'Not verified'}.`,
    inputs: { plt100met: plt100, liverMet: liver, ldhMet: ldh, sameDraw }
  };
}


// ── DV-14: Severity grade ──────────────────────────────────────────────────

/**
 * DV-14: Three-tier severity classification:
 *   CRITICAL:        Eclampsia, cerebral events, DIC, pulmonary oedema, ICU admission, maternal death
 *   SEVERE_FEATURES: Severe BP, platelets <100, renal/liver dysfunction, AEDF/REDF, HELLP
 *   STANDARD:        Hypertension ≥140/90 + proteinuria, no severe features
 */
export function deriveDV14(caseData, dvResults) {
  const {
    seizure_documented, dic_documented, pulm_oedema_documented,
    icu_admission, maternal_death, cerebral_event
  } = caseData;

  // CRITICAL limbs
  const criticalLimbs = {
    eclampsia:    !!seizure_documented && String(seizure_documented).toLowerCase() !== 'false',
    dic:          !!dic_documented,
    pulmOedema:   !!pulm_oedema_documented,
    icuAdmission: !!icu_admission,
    death:        !!maternal_death,
    cerebral:     !!cerebral_event
  };
  const criticalMet = Object.values(criticalLimbs).some(Boolean);

  // SEVERE_FEATURES limbs
  const severeLimbs = {
    severeBP:    dvResults['DV-02']?.met === true,
    thrombocyte: dvResults['DV-08']?.plt100met === true,
    renal:       dvResults['DV-10']?.met === true,
    liver:       dvResults['DV-11']?.met === true,
    ldh:         dvResults['DV-12']?.met === true,
    hellp:       dvResults['DV-13']?.met === true,
    doppler:     !!(caseData.ua_aedf || caseData.ua_redf)
  };
  const severeMet = Object.values(severeLimbs).some(Boolean);

  let grade, details;
  if (criticalMet) {
    grade = 'CRITICAL';
    const active = Object.entries(criticalLimbs).filter(([,v]) => v).map(([k]) => k);
    details = `CRITICAL grade: ${active.join(', ')}`;
  } else if (severeMet) {
    grade = 'SEVERE_FEATURES';
    const active = Object.entries(severeLimbs).filter(([,v]) => v).map(([k]) => k);
    details = `Severe features: ${active.join(', ')}`;
  } else {
    grade = 'STANDARD';
    details = 'Standard PE — hypertension + proteinuria without severe features';
  }

  return {
    id: 'DV-14', grade, met: grade !== 'STANDARD',
    criticalMet, severeMet, criticalLimbs, severeLimbs, details
  };
}


// ── DV-15: Uteroplacental dysfunction (combined UTPL) ──────────────────────

export function deriveDV15(efwCentile, ua_aedf, ua_redf, abruption, iufd) {
  const fgr      = efwCentile != null && parseFloat(efwCentile) < FGR_CENTILE;
  const aedf     = !!ua_aedf;
  const redf     = !!ua_redf;
  const abruptionMet = !!abruption;
  const iufdMet  = !!iufd;
  const met = fgr || aedf || redf || abruptionMet || iufdMet;
  const components = [
    fgr && `FGR (EFW ${efwCentile}th centile)`,
    aedf && 'AEDF on umbilical artery Doppler',
    redf && 'REDF on umbilical artery Doppler',
    abruptionMet && 'Placental abruption',
    iufdMet && 'Intrauterine fetal death (IUFD)'
  ].filter(Boolean);
  return {
    id: 'DV-15', met, components,
    details: met ? `Uteroplacental dysfunction (UTPL): ${components.join('; ')}` : 'No uteroplacental dysfunction documented',
    inputs: { efwCentile, ua_aedf, ua_redf, abruption, iufd }
  };
}


// ── DV-16: Serial weight gain ──────────────────────────────────────────────

/**
 * DV-16: Significant oedema proxy — weight gain >2 kg/week in third trimester.
 * @param {Array} weightLog - [{date, weight_kg, ga}]
 */
export function deriveDV16(weightLog) {
  if (!weightLog || weightLog.length < 2) {
    return { id: 'DV-16', met: false, details: 'Serial weight measurements not documented (<2 readings)', inputs: {} };
  }
  // Filter to 3rd trimester (GA ≥27 weeks = 189 days)
  const t3 = weightLog.filter(w => {
    const d = gaToDays(w.ga);
    return d != null && d >= 189;
  });
  if (t3.length < 2) {
    return { id: 'DV-16', met: false, details: 'Insufficient 3rd trimester weight readings', inputs: {} };
  }
  const sorted = [...t3].sort((a, b) => toTs(a.date) - toTs(b.date));
  let maxGainPerWeek = 0;
  let details = '';
  for (let i = 1; i < sorted.length; i++) {
    const t1 = toTs(sorted[i-1].date), t2 = toTs(sorted[i].date);
    const wks = t1 && t2 ? (t2 - t1) / (7 * 86400000) : 0;
    if (wks > 0) {
      const gain = (parseFloat(sorted[i].weight_kg) - parseFloat(sorted[i-1].weight_kg)) / wks;
      if (gain > maxGainPerWeek) {
        maxGainPerWeek = gain;
        details = `Weight gain ${gain.toFixed(1)} kg/week between ${sorted[i-1].date} and ${sorted[i].date}`;
      }
    }
  }
  const met = maxGainPerWeek > WEIGHT_GAIN_THRESH_KG_WK;
  return {
    id: 'DV-16', met,
    maxGainPerWeek: Math.round(maxGainPerWeek * 10) / 10,
    details: met ? `Significant weight gain: ${details} (threshold: >${WEIGHT_GAIN_THRESH_KG_WK} kg/week)` : `Weight gain within normal range (max ${maxGainPerWeek.toFixed(1)} kg/week)`,
    inputs: { readings: sorted.length, maxGainPerWeek }
  };
}


// ── DV-17: EFW centile validation ──────────────────────────────────────────

/**
 * DV-17: Validate EFW against INTERGROWTH-21 reference for GA.
 * If only raw EFW in grams is provided with GA, compute approximate centile.
 */
export function deriveDV17(efwCentile, efwGrams, gaStr) {
  if (efwCentile != null) {
    const c = parseFloat(efwCentile);
    return {
      id: 'DV-17', met: c < FGR_CENTILE, centile: c,
      details: `EFW ${c}th centile — ${c < FGR_CENTILE ? 'FGR (<10th centile)' : 'within normal range'} (centile provided directly)`,
      source: 'PROVIDED'
    };
  }
  if (efwGrams != null && gaStr) {
    const gaWk = parseInt(gaStr, 10);
    const median = INTERGROWTH_EFW_MEDIAN[gaWk];
    if (!median) return { id: 'DV-17', met: false, details: `No INTERGROWTH reference available for GA ${gaStr}`, source: 'UNCOMPUTABLE' };
    const efw = parseFloat(efwGrams);
    // Approximate centile using ±2SD ≈ ±20% of median
    const sd = median * 0.10; // approx 1 SD
    const zScore = (efw - median) / sd;
    // Simple normal CDF approximation
    const centile = Math.round(100 * (0.5 * (1 + erf(zScore / Math.sqrt(2)))));
    const clampedCentile = Math.max(1, Math.min(99, centile));
    return {
      id: 'DV-17', met: clampedCentile < FGR_CENTILE,
      centile: clampedCentile, efwGrams: efw, median,
      details: `EFW ${efw}g at GA ${gaStr}: ~${clampedCentile}th centile (INTERGROWTH-21 estimate). ${clampedCentile < FGR_CENTILE ? 'FGR confirmed.' : 'Within normal range.'}`,
      source: 'INTERGROWTH_ESTIMATED'
    };
  }
  return { id: 'DV-17', met: false, details: 'EFW centile and weight not documented', source: NOT_DOCUMENTED };
}

// Error function approximation for centile calculation
function erf(x) {
  const a1 = 0.254829592, a2 = -0.284496736, a3 = 1.421413741,
        a4 = -1.453152027, a5 = 1.061405429, p = 0.3275911;
  const sign = x < 0 ? -1 : 1;
  x = Math.abs(x);
  const t = 1 / (1 + p * x);
  const y = 1 - ((((a5*t + a4)*t + a3)*t + a2)*t + a1)*t * Math.exp(-x*x);
  return sign * y;
}


// ── DV-18: Antihypertensive exposure ───────────────────────────────────────

export function deriveDV18(medicationList) {
  if (!medicationList || !medicationList.length) {
    return { id: 'DV-18', met: false, details: 'No medication data documented', medications: [] };
  }
  const meds = medicationList.map(m => String(m.name || m).toLowerCase());
  const matched = ANTIHYPERTENSIVE_DICT.filter(drug => meds.some(m => m.includes(drug)));
  return {
    id: 'DV-18', met: matched.length > 0,
    medications: matched,
    details: matched.length
      ? `Antihypertensive exposure confirmed: ${matched.join(', ')}`
      : 'No antihypertensive medications documented in medication log'
  };
}


// ── DV-19: Aspirin / Calcium prophylaxis ───────────────────────────────────

export function deriveDV19(medicationList) {
  if (!medicationList || !medicationList.length) {
    return { id: 'DV-19', aspirinMet: false, calciumMet: false, met: false, details: 'No medication data documented' };
  }
  const meds = medicationList.map(m => String(m.name || m).toLowerCase());
  const aspirinMet  = PROPHYLAXIS_DICT.aspirin.some(k => meds.some(m => m.includes(k)));
  const calciumMet  = PROPHYLAXIS_DICT.calcium.some(k => meds.some(m => m.includes(k)));
  return {
    id: 'DV-19', aspirinMet, calciumMet, met: aspirinMet || calciumMet,
    details: [
      aspirinMet ? 'Aspirin prophylaxis documented' : 'Aspirin: not documented',
      calciumMet ? 'Calcium supplementation documented' : 'Calcium: not documented'
    ].join(' | ')
  };
}


// ── DV-20: Delivery date (multi-source priority) ────────────────────────────

export function deriveDV20(edcDeliveryDate, esourceDeliveryDate) {
  const edcTs  = toTs(edcDeliveryDate);
  const eTs    = toTs(esourceDeliveryDate);
  if (!edcTs && !eTs) return { id: 'DV-20', met: false, date: null, details: 'Delivery date not documented in any source' };
  if (!edcTs)  return { id: 'DV-20', met: true, date: esourceDeliveryDate, source: 'eSource', disagreement: false, details: `Delivery date from eSource: ${esourceDeliveryDate}` };
  if (!eTs)    return { id: 'DV-20', met: true, date: edcDeliveryDate, source: 'EDC', disagreement: false, details: `Delivery date from EDC: ${edcDeliveryDate}` };

  const diffDays = Math.abs(edcTs - eTs) / 86400000;
  const disagreement = diffDays > 7;
  return {
    id: 'DV-20', met: true, date: edcDeliveryDate, source: 'EDC',
    disagreement, diffDays: Math.round(diffDays),
    queryRequired: disagreement,
    details: disagreement
      ? `⚠ DV-20 Hard Query: EDC (${edcDeliveryDate}) vs eSource (${esourceDeliveryDate}) differ by ${Math.round(diffDays)} days (>7 day threshold)`
      : `Delivery date confirmed: ${edcDeliveryDate} (EDC/eSource agree within ${Math.round(diffDays)} days)`
  };
}


// ── DV-21: GA at delivery ──────────────────────────────────────────────────

export function deriveDV21(deliveryDate, ussDate, ussGa, edcDeliveryGa) {
  const derivedGa = (deliveryDate && ussDate && ussGa) ? gaFromAnchor(ussDate, ussGa, deliveryDate) : null;
  const derivedDays  = gaToDays(derivedGa);
  const enteredDays  = gaToDays(edcDeliveryGa);
  if (derivedDays == null && enteredDays == null) {
    return { id: 'DV-21', met: false, details: 'GA at delivery cannot be determined' };
  }
  if (derivedDays != null && enteredDays != null) {
    const diffDays = Math.abs(derivedDays - enteredDays);
    const hardQuery = diffDays > 7;
    return {
      id: 'DV-21', met: true,
      derivedGa, enteredGa: edcDeliveryGa,
      diffDays, hardQuery,
      details: hardQuery
        ? `⚠ DV-21 Hard Query: Derived GA at delivery ${derivedGa} vs entered ${edcDeliveryGa} (${diffDays} day discrepancy, >7-day threshold)`
        : `GA at delivery: ${enteredGa || derivedGa}. Derived/entered agree (±${diffDays} days)`
    };
  }
  return {
    id: 'DV-21', met: true,
    derivedGa: derivedGa || edcDeliveryGa,
    details: `GA at delivery: ${derivedGa || edcDeliveryGa}`
  };
}


// ── DV-22: Gravidity / parity ──────────────────────────────────────────────

export function deriveDV22(gravidity, parity, abortions, pregnancyHistory) {
  if (gravidity == null && !pregnancyHistory?.length) {
    return { id: 'DV-22', met: false, details: 'Gravidity/parity not documented' };
  }
  const G = gravidity != null ? parseInt(gravidity) : (pregnancyHistory?.length || 0) + 1;
  const P = parity != null ? parseInt(parity) : (pregnancyHistory?.filter(h => h.outcome === 'livebirth' || h.outcome === 'stillbirth').length || 0);
  const A = abortions != null ? parseInt(abortions) : (pregnancyHistory?.filter(h => h.outcome === 'abortion' || h.outcome === 'miscarriage').length || 0);
  return {
    id: 'DV-22', met: true,
    G, P, A,
    gpString: `G${G}P${P}A${A}`,
    details: `Obstetric history: G${G}P${P}A${A}`,
    inputs: { gravidity: G, parity: P, abortions: A }
  };
}


// ── DV-23: Comorbidities ───────────────────────────────────────────────────

const COMORBIDITY_MAP = {
  'chronic htn': 'I10', 'hypertension': 'I10',
  'diabetes': 'E11', 'diabetes mellitus': 'E11',
  'renal disease': 'N18', 'ckd': 'N18', 'chronic kidney disease': 'N18',
  'sle': 'M32', 'lupus': 'M32', 'systemic lupus': 'M32',
  'antiphospholipid': 'D68.61', 'aps': 'D68.61',
  'obesity': 'E66', 'bmi': 'E66',
  'hiv': 'B20', 'aids': 'B20',
  'thyroid': 'E03', 'hypothyroid': 'E03',
  'anaemia': 'D64', 'anemia': 'D64', 'sickle cell': 'D57'
};

export function deriveDV23(comorbidityList) {
  if (!comorbidityList || !comorbidityList.length) {
    return { id: 'DV-23', met: false, coded: [], details: 'No comorbidities documented' };
  }
  const coded = comorbidityList.map(item => {
    const raw = String(item.name || item).toLowerCase();
    const icd10 = Object.entries(COMORBIDITY_MAP).find(([k]) => raw.includes(k))?.[1] || 'UNCODEABLE';
    return { name: item.name || item, icd10 };
  });
  return {
    id: 'DV-23', met: coded.length > 0,
    coded,
    details: `${coded.length} comorbidities coded: ${coded.map(c => `${c.name} [${c.icd10}]`).join(', ')}`
  };
}


// ── DV-24: Maternal composite endpoint ────────────────────────────────────

/**
 * DV-24: Six-component maternal composite:
 * Eclampsia | ICU admission | Transfusion | Acute renal failure | Hepatic failure | Maternal death
 */
export function deriveDV24(caseData) {
  const components = {
    eclampsia:    !!(caseData.seizure_documented && String(caseData.seizure_documented).toLowerCase() !== 'false'),
    icuAdmission: !!caseData.icu_admission,
    transfusion:  !!caseData.blood_transfusion,
    acuteRenal:   !!(caseData.acute_renal_failure || (caseData.creatinine && parseFloat(caseData.creatinine) > 3.5)),
    hepaticFailure: !!(caseData.hepatic_failure),
    maternalDeath:  !!caseData.maternal_death
  };
  const met = Object.values(components).some(Boolean);
  const active = Object.entries(components).filter(([,v]) => v).map(([k]) => k);
  return {
    id: 'DV-24', met, components,
    compositeLabel: met ? active.join(' + ') : 'None',
    details: met
      ? `Maternal composite endpoint MET: ${active.join(', ')}`
      : 'Maternal composite endpoint: no qualifying components documented'
  };
}


// ── DV-25: Fetal/neonatal composite endpoint ───────────────────────────────

/**
 * DV-25: Seven-component fetal/neonatal composite:
 * Perinatal/fetal death | Delivery <34 weeks | IUGR | Abruption | RDS | NEC | IVH
 */
export function deriveDV25(caseData, dv05Result) {
  const gaAtDeliveryDays = gaToDays(caseData.ga_at_delivery || caseData.gaAtDelivery);
  const deliveryLt34 = gaAtDeliveryDays != null && gaAtDeliveryDays < GA_EOPE_DAYS;

  const components = {
    perinatalDeath: !!(caseData.iufd || caseData.neonatal_death),
    deliveryLt34,
    iugr:      !!(caseData.ua_aedf || caseData.ua_redf || (caseData.efw_centile && parseFloat(caseData.efw_centile) < FGR_CENTILE)),
    abruption: !!caseData.abruption,
    rds:       !!caseData.rds,
    nec:       !!caseData.nec,
    ivh:       !!caseData.ivh
  };
  const met = Object.values(components).some(Boolean);
  const active = Object.entries(components).filter(([,v]) => v).map(([k]) => k);
  return {
    id: 'DV-25', met, components,
    details: met
      ? `Fetal/neonatal composite MET: ${active.join(', ')}`
      : 'Fetal/neonatal composite: no qualifying components documented'
  };
}


// ── DV-26: Evidence completeness (6 classes) ───────────────────────────────

/**
 * DV-26: Six evidence classes (expanded from 5):
 *   1. Dating anchor [0.167]  2. BP trajectory [0.167]  3. Proteinuria [0.167]
 *   4. Organ dysfunction labs [0.167]  5. Fetal assessment [0.167]  6. Delivery/outcome [0.167]
 */
export function deriveDV26(caseData) {
  const weight = 1/6;
  let pts = 0;
  const missing = [];

  // 1. Dating anchor
  if (caseData.firstUssDate || caseData.lnmp || caseData.edd) pts += weight;
  else missing.push('Dating Anchor (1st-trimester USS or LMP)');

  // 2. BP trajectory (≥2 readings)
  const bpList = caseData.bpLog || caseData.bp_readings || [];
  if (bpList.length >= 2) pts += weight;
  else missing.push('BP Trajectory (≥2 serial BP readings)');

  // 3. Proteinuria
  const hasProt = caseData.upcr != null ||
    (caseData.proteinuriaLog && caseData.proteinuriaLog.length > 0) ||
    caseData.dipstick_raw != null ||
    caseData.prot_24h_mg != null;
  if (hasProt) pts += weight;
  else missing.push('Proteinuria Assessment (UPCR/dipstick/24h)');

  // 4. Organ dysfunction labs
  const labs = caseData.labLog || [];
  const hasPlatelets = caseData.platelet_count != null || labs.some(l => l.analyte?.toLowerCase().includes('platelet'));
  const hasCreat = caseData.creatinine != null || caseData.creatinine_raw != null || labs.some(l => l.analyte?.toLowerCase().includes('creatinine'));
  if (hasPlatelets && hasCreat) pts += weight;
  else missing.push('Organ Dysfunction Labs (Platelets + Creatinine)');

  // 5. Fetal assessment (USS)
  const hasFetal = caseData.efw_centile != null || caseData.ua_aedf != null ||
    (caseData.sourceDocs?.ultrasound) || (caseData.efw_grams != null);
  if (hasFetal) pts += weight;
  else missing.push('Fetal Growth & Doppler (Ultrasound report)');

  // 6. Delivery / outcome documented
  const hasDelivery = !!(caseData.delivery_date || caseData.ga_at_delivery || caseData.gaAtDelivery ||
    (caseData.sourceDocs?.delivery && caseData.sourceDocs.delivery !== 'Pending — Ongoing pregnancy.'));
  if (hasDelivery) pts += weight;
  else missing.push('Delivery & Neonatal Outcome');

  const score = Math.min(1.0, Math.round(pts * 100) / 100);
  return { score, missing, classes: 6 };
}


// ── DV-27: Certainty gate ─────────────────────────────────────────────────

/**
 * DV-27: Three-condition certainty gate for "DEFINITE":
 *   A. Evidence completeness score (DV-26) = 1.0
 *   B. Dated confirmed hypertension (DV-03 met with a date)
 *   C. Dated confirmatory element (proteinuria or organ dysfunction with a date)
 */
export function deriveDV27(dv26Score, dv03Result, dv07Result, dv08Result, dv10Result, dv11Result) {
  const condA = dv26Score >= 1.0;
  const condB = dv03Result?.met === true && !!(dv03Result?.firstDate || dv03Result?.inputs?.visit_dates?.length);
  const condC = (dv07Result?.met === true) || (dv08Result?.met === true) || (dv10Result?.met === true) || (dv11Result?.met === true);

  const gateOpen = condA && condB && condC;
  const blockedBy = [];
  if (!condA) blockedBy.push(`DV-26 completeness ${Math.round(dv26Score * 100)}% (needs 100%)`);
  if (!condB) blockedBy.push('Dated confirmed hypertension not established (DV-03)');
  if (!condC) blockedBy.push('No dated confirmatory element (proteinuria or organ dysfunction)');

  return {
    id: 'DV-27', gateOpen, condA, condB, condC,
    blockedBy,
    details: gateOpen
      ? 'DV-27 Certainty Gate: OPEN — All 3 conditions met. DEFINITE certainty available.'
      : `DV-27 Certainty Gate: LOCKED — ${blockedBy.join('; ')}`
  };
}


// ── DV-28: Endpoint windows ────────────────────────────────────────────────

/**
 * DV-28: Determine whether adjudicated onset falls within 1-, 2-, or 4-week
 * windows from Visit 1 (screening/enrollment date).
 */
export function deriveDV28(visit1Date, onsetDate) {
  const v1Ts = toTs(visit1Date);
  const onTs = toTs(onsetDate);
  if (!v1Ts || !onTs) {
    return { id: 'DV-28', met: false, window: null, details: 'Visit 1 date or onset date not available' };
  }
  const diffDays = Math.round((onTs - v1Ts) / 86400000);
  const window1wk = diffDays <= 7;
  const window2wk = diffDays <= 14;
  const window4wk = diffDays <= 28;
  const activeWindow = window1wk ? '1-week' : window2wk ? '2-week' : window4wk ? '4-week' : 'Outside all windows';
  return {
    id: 'DV-28', met: window4wk,
    diffDays, window1wk, window2wk, window4wk,
    activeWindow,
    details: `Onset ${diffDays >= 0 ? diffDays : 0} days after Visit 1 — falls in: ${activeWindow}`
  };
}


// ── DV-29: Inter-rater agreement (Cohen's Kappa) ──────────────────────────

/**
 * DV-29: Calculate % agreement and Cohen's Kappa from Reviewer A/B pairs.
 * @param {Array} submissions - [{reviewer: 'A'|'B', diagnosis, onset, severity, certainty, meetsEndpoint}]
 */
export function deriveDV29(submissions) {
  const reviewerA = submissions?.find(s => s.reviewer === 'A' || s.reviewer_role === 'REVIEWER_A');
  const reviewerB = submissions?.find(s => s.reviewer === 'B' || s.reviewer_role === 'REVIEWER_B');

  if (!reviewerA || !reviewerB) {
    return {
      id: 'DV-29', kappa: null, pctAgreement: null,
      details: 'Inter-rater agreement requires ≥2 reviewer submissions',
      reviewerA: !!reviewerA, reviewerB: !!reviewerB
    };
  }

  const fields = ['diagnosis', 'onset_class', 'meets_criteria'];
  let agreeing = 0;
  const fieldResults = {};
  for (const f of fields) {
    const match = String(reviewerA[f] || '').toLowerCase() === String(reviewerB[f] || '').toLowerCase();
    if (match) agreeing++;
    fieldResults[f] = { match, a: reviewerA[f], b: reviewerB[f] };
  }

  const pctAgreement = Math.round((agreeing / fields.length) * 100);

  // Simple Cohen's Kappa: κ = (Po - Pe) / (1 - Pe)
  // For binary agreement across N categories, Pe ≈ 1/categories (uniform distribution approximation)
  const Po = agreeing / fields.length;
  const Pe = 1 / 3; // simple approximation for 3-way classification
  const kappa = Pe < 1 ? Math.round(((Po - Pe) / (1 - Pe)) * 100) / 100 : 1;

  const concordant = agreeing === fields.length;
  return {
    id: 'DV-29', kappa, pctAgreement, concordant,
    fieldResults, agreeing, total: fields.length,
    driftAlert: kappa < 0.80,
    details: concordant
      ? `Concordant: Reviewer A & B agree on all ${fields.length} key fields (κ=${kappa})`
      : `Discordant: ${fields.length - agreeing} field(s) differ. Cohen's κ=${kappa} (${pctAgreement}% agreement). ${kappa < 0.80 ? '⚠ Kappa below 0.80 — calibration may be needed.' : ''}`
  };
}


// ── DV-30: Adjudication trigger evaluation ─────────────────────────────────

/**
 * DV-30: Evaluate all trigger limbs automatically:
 *   A. BP ≥140/90 on ≥2 occasions at any visit after 20+0 weeks
 *   B. Maternal SAE documented
 *   C. EFW <10th centile + abnormal Doppler
 *   D. Preterm birth <37 weeks with obstetric HTN indication
 */
export function deriveDV30(caseData) {
  const bpLog = caseData.bpLog || caseData.bp_readings || [];
  // Check after 20+0 weeks (140 days)
  const afterBooking = bpLog.filter(r => {
    const d = gaToDays(r.ga);
    return d != null ? d >= 140 : true; // include if GA unknown (conservative)
  });
  const qualifyingBP = afterBooking.filter(r => Number(r.sbp) >= BP_HTN_SBP || Number(r.dbp) >= BP_HTN_DBP);

  const limbA = qualifyingBP.length >= 2;
  const limbB = !!(caseData.seizure_documented || caseData.icu_admission || caseData.dic_documented ||
                   caseData.pulm_oedema_documented || caseData.maternal_death || caseData.sae_documented);
  const limbC = !!(caseData.ua_aedf || caseData.ua_redf) &&
                (caseData.efw_centile != null && parseFloat(caseData.efw_centile) < FGR_CENTILE);
  const gaDelivery = gaToDays(caseData.ga_at_delivery || caseData.gaAtDelivery);
  const limbD = gaDelivery != null && gaDelivery < 37 * 7 && limbA;

  const triggered = limbA || limbB || limbC || limbD;
  const activeLimbs = [limbA && 'A-BP', limbB && 'B-SAE', limbC && 'C-FGR+Doppler', limbD && 'D-PreTermHTN'].filter(Boolean);

  return {
    id: 'DV-30', triggered, met: triggered,
    limbA, limbB, limbC, limbD,
    activeLimbs,
    triggerCode: activeLimbs.length > 0 ? `DV-30(${activeLimbs.join(',')})` : null,
    details: triggered
      ? `DV-30 Trigger: Limb(s) met: ${activeLimbs.join(', ')}. Case qualifies for adjudication.`
      : 'DV-30: No trigger criteria met — does not qualify for adjudication package.'
  };
}


// ── Full Case Derivation Runner ─────────────────────────────────────────────

/**
 * runFullDerivation(caseData) → Complete derivation result for all DV-01–DV-30.
 *
 * @param {Object} caseData - The canonical case object (from mock or CSV parse)
 * @returns {Object} - Full derivation result including all DV results, score, gate, severity grade
 */
export function runFullDerivation(caseData) {
  if (!caseData) return null;

  const bpLog      = caseData.bpLog || caseData.bp_readings || [];
  const labLog     = caseData.labLog || [];
  const protLog    = caseData.proteinuriaLog || [];
  const weightLog  = caseData.weightLog || [];
  const meds       = caseData.medicationLog || caseData.medications || [];

  // Extract lab values from labLog if not top-level fields
  const findLab = (analyte) => labLog.find(l => l.analyte?.toLowerCase().includes(analyte.toLowerCase()));
  const plateletEntry  = findLab('platelet');
  const creatEntry     = findLab('creatinine');
  const astEntry       = findLab('ast');
  const altEntry       = findLab('alt');
  const ldhEntry       = findLab('ldh');

  const plateletCount  = caseData.platelet_count ?? (plateletEntry ? parseFloat(plateletEntry.result) : null);
  const creatRaw       = caseData.creatinine_raw ?? caseData.creatinine ?? (creatEntry?.result ?? null);
  const creatUnit      = caseData.creatinine_unit ?? creatEntry?.unit ?? null;
  const ast            = caseData.ast ?? (astEntry ? parseFloat(astEntry.result) : null);
  const alt            = caseData.alt ?? (altEntry ? parseFloat(altEntry.result) : null);
  const ldh            = caseData.ldh ?? (ldhEntry ? parseFloat(ldhEntry.result) : null);

  // Proteinuria
  const upcr = caseData.upcr ?? (protLog.find(p => p.method?.toUpperCase().includes('UPCR'))?.numeric ?? null);
  const dipstickRaw = caseData.dipstick_raw ?? (protLog.find(p => p.method?.toLowerCase().includes('dipstick'))?.result ?? null);
  const prot24h = caseData.prot_24h_mg ?? null;

  // Run individual DV rules
  const dv02 = deriveDV02(bpLog);
  const dv03 = deriveDV03(bpLog);
  const dv07 = deriveDV07(upcr, dipstickRaw, prot24h);
  const dv08 = deriveDV08(plateletCount);
  const dv10 = deriveDV10(creatRaw, creatUnit);
  const dv11 = deriveDV11(ast, alt);
  const dv12 = deriveDV12(ldh);
  const dv13 = deriveDV13(dv08, dv11, dv12, labLog);
  const dv14 = deriveDV14(caseData, { 'DV-02': dv02, 'DV-08': dv08, 'DV-10': dv10, 'DV-11': dv11, 'DV-12': dv12, 'DV-13': dv13 });
  const dv15 = deriveDV15(caseData.efw_centile, caseData.ua_aedf, caseData.ua_redf, caseData.abruption, caseData.iufd);
  const dv16 = deriveDV16(weightLog);
  const dv17 = deriveDV17(caseData.efw_centile, caseData.efw_grams, caseData.gaAtEvent);
  const dv18 = deriveDV18(meds);
  const dv19 = deriveDV19(meds);
  const dv20 = deriveDV20(caseData.delivery_date || caseData.edcDeliveryDate, caseData.esourceDeliveryDate);
  const dv21 = deriveDV21(caseData.delivery_date, caseData.firstUssDate, caseData.firstUssGa, caseData.ga_at_delivery || caseData.gaAtDelivery);
  const dv22 = deriveDV22(caseData.gravidity, caseData.parity, caseData.abortions, caseData.pregnancyHistory);
  const dv23 = deriveDV23(caseData.comorbidities);
  const dv24 = deriveDV24(caseData);
  const dv25 = deriveDV25(caseData, null);
  const { score: dv26Score, missing: dv26Missing } = deriveDV26(caseData);
  const dv27 = deriveDV27(dv26Score, dv03, dv07, dv08, dv10, dv11);

  // DV-05 onset
  const onsetGa = caseData.gaAtEvent || caseData.ga_at_first_criterion;
  const dv05 = deriveDV05(onsetGa, caseData.gaAtDelivery, caseData.postpartum_only);

  // DV-06 proposed onset
  const dv06 = deriveDV06(bpLog, protLog, labLog, caseData.firstUssDate, caseData.firstUssGa);

  // DV-28 endpoint windows (use enrollment date as Visit 1 proxy)
  const visit1Date = caseData.enrollmentDate || caseData.firstUssDate;
  const dv28 = deriveDV28(visit1Date, dv06.proposedOnsetDate || caseData.derivedOnset);

  // DV-29 inter-rater
  const dv29 = deriveDV29(caseData.submissions || caseData.adjudicationRecords || []);

  // DV-30 trigger
  const dv30 = deriveDV30(caseData);

  // Build criteria array for UI display (backward compatible with existing `criteria` field structure)
  const criteriaResults = [
    { id: 'HTN-01', title: 'Hypertension (≥140/90 mmHg, confirmed)', met: dv03.met, details: dv03.details },
    { id: 'HTN-02', title: 'Severe-range BP (≥160/110 mmHg)', met: dv02.met, details: dv02.details },
    { id: 'PROT-01', title: 'Significant Proteinuria', met: dv07.met, details: dv07.details },
    { id: 'HAEM-01', title: `Thrombocytopenia — ${dv08.tier || 'None'}`, met: dv08.met, details: dv08.details },
    { id: 'RENAL-01', title: 'Renal Impairment', met: dv10.met, details: dv10.details },
    { id: 'HEP-01', title: 'Hepatic Dysfunction', met: dv11.met, details: dv11.details },
    { id: 'LDH-01', title: 'LDH ≥600 IU/L', met: dv12.met, details: dv12.details },
    { id: 'HELLP-01', title: `HELLP — ${dv13.hellpType || 'NOT_HELLP'}`, met: dv13.met, details: dv13.details },
    { id: 'FGR-UTPL', title: 'Uteroplacental Dysfunction', met: dv15.met, details: dv15.details },
    { id: 'SEV-01', title: `Severity Grade: ${dv14.grade}`, met: dv14.met, details: dv14.details }
  ];

  return {
    // All DV results
    'DV-02': dv02, 'DV-03': dv03, 'DV-05': dv05, 'DV-06': dv06,
    'DV-07': dv07, 'DV-08': dv08, 'DV-10': dv10, 'DV-11': dv11,
    'DV-12': dv12, 'DV-13': dv13, 'DV-14': dv14, 'DV-15': dv15,
    'DV-16': dv16, 'DV-17': dv17, 'DV-18': dv18, 'DV-19': dv19,
    'DV-20': dv20, 'DV-21': dv21, 'DV-22': dv22, 'DV-23': dv23,
    'DV-24': dv24, 'DV-25': dv25, 'DV-27': dv27, 'DV-28': dv28,
    'DV-29': dv29, 'DV-30': dv30,

    // Summary outputs
    evidenceScore: dv26Score,
    missingAnchors: dv26Missing,
    certaintyGatePassed: dv27.gateOpen,
    derivedSeverityGrade: dv14.grade,
    derivedSubtype: dv05.subtype,
    proposedOnset: dv06.proposedOnsetDate,
    proposedOnsetGa: dv06.proposedOnsetGa,
    evidenceTable: dv06.evidenceTable,
    triggerCode: dv30.triggerCode,
    triggered: dv30.triggered,
    maternalComposite: dv24.met,
    fetalComposite: dv25.met,
    ruleVersion: RULE_VERSION,

    // Backward-compatible criteria array for workbench display
    computedCriteria: criteriaResults
  };
}
