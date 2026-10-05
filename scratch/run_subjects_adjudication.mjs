import { buildDemographicString, formatVisitDate } from '../src/services/visitEvidence.js';

// Replicate the exact narrative synthesis logic from VisitEvidenceSections.jsx
function synthesizeVisitNarrative(visit, visitNum, caseData) {
  const isSubject11 = !caseData?.id || String(caseData?.id || '').includes('0214') || String(caseData?.caseNo || '').includes('0214');
  
  const patientAge = caseData?.history?.age
    || caseData?.history?.demographics?.find(f => f.key === 'age')?.value
    || caseData?.age
    || null;

  const rawGravida = caseData?.risk_summary?.gravidity != null
    ? caseData.risk_summary.gravidity
    : (caseData?.gravidity != null ? caseData.gravidity : null);

  const rawParity = caseData?.risk_summary?.parity != null
    ? caseData.risk_summary.parity
    : (caseData?.parity != null ? caseData.parity : 0);

  const rawMisc = caseData?.risk_summary?.miscarriages != null
    ? caseData.risk_summary.miscarriages
    : (caseData?.miscarriages != null ? caseData.miscarriages : 0);

  const isNullip = caseData?.risk_summary?.chips?.some(c => /nulliparous/i.test(c))
    || (rawGravida === 0 && rawParity === 0 && rawMisc === 0)
    || (rawGravida == null && rawParity === 0 && rawMisc === 0);

  const gravidity = isNullip && (!rawGravida || rawGravida === 0) ? 1 : (rawGravida ?? 1);
  const parity = rawParity;
  const miscarriages = rawMisc;
  const comorbList = caseData?.risk_summary?.chips || [];

  const isPostpartum = visitNum === 6 || /eos|post|v06|visit 6/i.test(visit.name || visit.visit_code || '');
  const isDelivery = visitNum === 5 || /delivery|v05|visit 5/i.test(visit.name || visit.visit_code || '');
  const bp = visit.vitals?.bp;
  const bpRecheck = visit.vitals?.recheck;
  const ga = visit.gestationalLabel || (isPostpartum ? 'Postpartum (~4 weeks)' : isDelivery ? 'Term delivery window' : `Visit ${visitNum}`);

  // Baseline visit (Visit 1)
  if (visitNum === 1) {
    const demoOpening = buildDemographicString(patientAge, gravidity, parity, miscarriages, comorbList);
    const bpStr = bp ? `Blood pressure at presentation was ${bp}${bpRecheck ? ` (recheck: ${bpRecheck})` : ''}.` : 'Hemodynamic surveillance was recorded.';
    return `${demoOpening} ${bpStr} Baseline organ function and laboratory surveillance are detailed in the diagnostic panels below.`;
  }

  // Delivery encounter (Visit 5)
  if (isDelivery) {
    const delMode = visit.maternalDeliveryMode || visit.maternal?.find(m => /mode|delivery/i.test(m.value))?.value || 'delivery';
    const babyWt = visit.birthWeight || visit.neonatal?.find(n => /weight|birth_weight/i.test(String(n.id || n.value)))?.value;
    const babyStr = babyWt ? ` infant weighing ${babyWt}g` : ' infant';
    return `At ${ga}, the patient was admitted for an operative ${delMode}. She delivered a live${babyStr} without acute maternal complications documented, and recovered satisfactorily following delivery.`;
  }

  // Postpartum follow-up (Visit 6)
  if (isPostpartum) {
    return `Approximately four weeks postpartum, the patient returns for final postnatal follow-up. Her postnatal clinical recovery has been unremarkable. ${bp ? `Blood pressure was documented at ${bp}${bpRecheck ? ` (recheck: ${bpRecheck})` : ''}.` : 'Hemodynamics remain clinically stable.'} Routine urinalysis and laboratory indices remain preserved without evidence of late-onset preeclampsia.`;
  }

  // Antenatal follow-ups (Visits 2 - 4)
  const bpProse = bp
    ? `Blood pressure remained controlled at ${bp}${bpRecheck ? ` (recheck: ${bpRecheck})` : ''}.`
    : 'Hemodynamic indices remained clinically stable.';
  const protRow = (visit.proteinuria || [])[0];
  let protProse = 'Dipstick urinalysis remained negative for proteinuria and infection markers.';
  if (protRow && !/negative/i.test(String(protRow.value))) {
    protProse = `Urinalysis was notable for ${protRow.value} proteinuria.`;
  }

  return `At ${ga} gestation, the patient presented for scheduled clinical trial surveillance. She remained clinically stable without acute pre-eclamptic symptoms. ${bpProse} ${protProse} Maternal organ function and fetal wellbeing remain documented in the panels below.`;
}

// Replicate OverallSummary clinicalCourseText logic from VisitEvidenceSections.jsx
function synthesizeOverallSummary(visits, caseData) {
  const patientAge = caseData?.history?.age
    || caseData?.history?.demographics?.find(f => f.key === 'age')?.value
    || caseData?.age
    || null;

  const rawGravida = caseData?.risk_summary?.gravidity != null
    ? caseData.risk_summary.gravidity
    : (caseData?.gravidity != null ? caseData.gravidity : null);

  const rawParity = caseData?.risk_summary?.parity != null
    ? caseData.risk_summary.parity
    : (caseData?.parity != null ? caseData.parity : 0);

  const rawMisc = caseData?.risk_summary?.miscarriages != null
    ? caseData.risk_summary.miscarriages
    : (caseData?.miscarriages != null ? caseData.miscarriages : 0);

  const isNullip = caseData?.risk_summary?.chips?.some(c => /nulliparous/i.test(c))
    || (rawGravida === 0 && rawParity === 0 && rawMisc === 0)
    || (rawGravida == null && rawParity === 0 && rawMisc === 0);

  const gravidity = isNullip && (!rawGravida || rawGravida === 0) ? 1 : (rawGravida ?? 1);
  const parity = rawParity;
  const miscarriages = rawMisc;
  const comorbList = caseData?.risk_summary?.chips || [];

  const allBps = visits.flatMap(v => v.bp || []);
  const maxSbp = allBps.length > 0 ? Math.max(...allBps.map(b => b.sbp)) : null;
  const maxDbp = allBps.length > 0 ? Math.max(...allBps.map(b => b.dbp)) : null;
  const hasSevereHtn = (maxSbp && maxSbp >= 160) || (maxDbp && maxDbp >= 110);
  const hasElevatedHtn = (maxSbp && maxSbp >= 140) || (maxDbp && maxDbp >= 90);
  const hasProteinuria = visits.some(v => (v.proteinuria || []).some(p => !/negative/i.test(String(p.value))));

  const demoOpening = buildDemographicString(patientAge, gravidity, parity, miscarriages, comorbList);
  const htnStr = hasSevereHtn ? 'severe-range blood pressure elevation'
    : hasElevatedHtn ? 'mild-to-moderate hypertensive readings'
    : 'blood pressure control strictly within the normotensive range';
  const protStr = hasProteinuria ? 'with documented episodes of proteinuria' : 'without persistent proteinuria';

  return `${demoOpening} She completed study surveillance across ${visits.length} scheduled visits. Longitudinal hemodynamic evaluation demonstrated ${htnStr} (peak: ${maxSbp ? `${maxSbp}/${maxDbp} mmHg` : 'within documented limits'}), ${protStr}. Maternal systemic indices and fetal development were serially evaluated per protocol criteria.`;
}

// ── SUBJECT 1: ZWE001-0082 (MRN 7017, Age 25) ─────────────────────────────
const subject1 = {
  id: 'ZWE001-0082',
  caseNo: 'ADJ-ZWE001-0082',
  age: 25,
  risk_summary: {
    gravidity: 2,
    parity: 0,
    miscarriages: 1,
    chips: [], // No chronic conditions documented
  },
  visits: [
    {
      visit_number: 1,
      name: 'Screening | V01',
      date: '2026-03-04',
      gestationalLabel: '23 weeks, 4 days',
      vitals: { bp: '110/78 mmHg', recheck: '112/68 mmHg', hr: '88 bpm', temp: '36.3°C' },
      bp: [{ sbp: 110, dbp: 78 }, { sbp: 112, dbp: 68 }],
      proteinuria: [{ value: 'Negative' }],
      labs: [{ key: 'PLATELETS', raw: 279 }, { key: 'CREATININE', raw: 46.7 }]
    },
    {
      visit_number: 2,
      name: 'Visit 2',
      date: '2026-03-11',
      gestationalLabel: '24 weeks, 4 days',
      vitals: { bp: '114/56 mmHg', recheck: null, hr: '88 bpm', temp: '36.0°C' },
      bp: [{ sbp: 114, dbp: 56 }],
      proteinuria: [{ value: 'Trace' }],
      labs: [{ key: 'PLATELETS', raw: 289 }, { key: 'CREATININE', raw: 46.7 }]
    },
    {
      visit_number: 3,
      name: 'Visit 3',
      date: '2026-03-18',
      gestationalLabel: '25 weeks, 4 days',
      vitals: { bp: '110/61 mmHg', recheck: null, hr: '95 bpm', temp: '36.2°C' },
      bp: [{ sbp: 110, dbp: 61 }],
      proteinuria: [{ value: '2+' }],
      labs: [{ key: 'PLATELETS', raw: 264.2 }, { key: 'CREATININE', raw: 47.3 }]
    },
    {
      visit_number: 4,
      name: 'Visit 4',
      date: '2026-04-01',
      gestationalLabel: '27 weeks, 4 days',
      vitals: { bp: '107/55 mmHg', recheck: null, hr: '77 bpm', temp: '36.4°C' },
      bp: [{ sbp: 107, dbp: 55 }],
      proteinuria: [{ value: 'Negative' }],
      labs: [{ key: 'PLATELETS', raw: 264.0 }, { key: 'CREATININE', raw: 41.8 }]
    },
    {
      visit_number: 5,
      name: 'Visit 5 - Delivery',
      date: '2026-06-08',
      gestationalLabel: '37 weeks',
      maternalDeliveryMode: 'vaginal delivery',
      birthWeight: 2870,
      vitals: { bp: '112/70 mmHg' },
      bp: [{ sbp: 112, dbp: 70 }],
      proteinuria: [{ value: 'Negative' }]
    },
    {
      visit_number: 6,
      name: 'Visit 6 - Postnatal EOS',
      date: '2026-07-09',
      gestationalLabel: 'Postpartum (~4 weeks)',
      vitals: { bp: '96/62 mmHg', recheck: null, hr: '85 bpm', temp: '36.0°C' },
      bp: [{ sbp: 96, dbp: 62 }],
      proteinuria: [{ value: 'Negative' }]
    }
  ]
};

// ── SUBJECT 2: ZWE001-0214 (MRN 7167, Age 40) ─────────────────────────────
const subject2 = {
  id: 'ZWE001-0214',
  caseNo: 'ADJ-ZWE001-0214',
  age: 40,
  risk_summary: {
    gravidity: 4,
    parity: 2,
    miscarriages: 1,
    chips: ['Pre-existing chronic HTN', 'Pre-gestational diabetes'],
  },
  visits: [
    {
      visit_number: 1,
      name: 'Screening | V01',
      date: '2026-05-12',
      gestationalLabel: '30 weeks, 3 days',
      vitals: { bp: '114/78 mmHg', recheck: null, hr: '90 bpm', temp: '36.6°C' },
      bp: [{ sbp: 114, dbp: 78 }],
      proteinuria: [{ value: 'Negative' }],
      labs: [{ key: 'PLATELETS', raw: 251.5 }, { key: 'CREATININE', raw: 33.7 }]
    },
    {
      visit_number: 2,
      name: 'Visit 2',
      date: '2026-05-21',
      gestationalLabel: '31 weeks, 5 days',
      vitals: { bp: '128/85 mmHg', recheck: '127/86 mmHg', hr: '78 bpm', temp: '36.7°C' },
      bp: [{ sbp: 128, dbp: 85 }, { sbp: 127, dbp: 86 }],
      proteinuria: [{ value: 'Negative' }],
      labs: [{ key: 'PLATELETS', raw: 240.8 }, { key: 'CREATININE', raw: 44.24 }]
    },
    {
      visit_number: 3,
      name: 'Visit 3',
      date: '2026-05-27',
      gestationalLabel: '32 weeks, 4 days',
      vitals: { bp: '132/89 mmHg', recheck: '129/88 mmHg', hr: '82 bpm', temp: '36.6°C' },
      bp: [{ sbp: 132, dbp: 89 }, { sbp: 129, dbp: 88 }],
      proteinuria: [{ value: 'Trace' }],
      labs: [{ key: 'PLATELETS', raw: 245.0 }, { key: 'CREATININE', raw: 41.0 }]
    },
    {
      visit_number: 4,
      name: 'Visit 4',
      date: '2026-06-11',
      gestationalLabel: '34 weeks, 5 days',
      vitals: { bp: '130/84 mmHg', recheck: '128/82 mmHg', hr: '80 bpm', temp: '36.5°C' },
      bp: [{ sbp: 130, dbp: 84 }, { sbp: 128, dbp: 82 }],
      proteinuria: [{ value: 'Negative' }],
      labs: [{ key: 'PLATELETS', raw: 223.1 }, { key: 'CREATININE', raw: 45.1 }]
    },
    {
      visit_number: 5,
      name: 'Visit 5 - Delivery',
      date: '2026-06-29',
      gestationalLabel: '37 weeks, 3 days',
      maternalDeliveryMode: 'planned Cesarean section',
      birthWeight: 2550,
      vitals: { bp: '130/80 mmHg' },
      bp: [{ sbp: 130, dbp: 80 }],
      proteinuria: [{ value: 'Negative' }]
    },
    {
      visit_number: 6,
      name: 'Visit 6 - Postnatal EOS',
      date: '2026-07-28',
      gestationalLabel: 'Postpartum (~4 weeks)',
      vitals: { bp: '136/89 mmHg', recheck: '138/88 mmHg', hr: '88 bpm', temp: '36.2°C' },
      bp: [{ sbp: 136, dbp: 89 }, { sbp: 138, dbp: 88 }],
      proteinuria: [{ value: 'Negative' }]
    }
  ]
};

console.log('================================================================================');
console.log('OUTPUT FOR SUBJECT 1: ZWE001-0082 (Age 25, G2 P0 +1M, No chronic conditions)');
console.log('================================================================================\n');

subject1.visits.forEach((v, idx) => {
  const narrative = synthesizeVisitNarrative(v, idx + 1, subject1);
  console.log(`[VISIT ${idx + 1}]: ${v.name} (${v.date})`);
  console.log(narrative);
  console.log('--------------------------------------------------------------------------------');
});

console.log('\n[OVERALL ADJUDICATION SUMMARY & LONGITUDINAL CLINICAL COURSE]');
console.log(synthesizeOverallSummary(subject1.visits, subject1));
console.log('\n================================================================================\n');

console.log('================================================================================');
console.log('OUTPUT FOR SUBJECT 2: ZWE001-0214 (Age 40, G4 P2 +1M, Chronic HTN & DM)');
console.log('================================================================================\n');

subject2.visits.forEach((v, idx) => {
  const narrative = synthesizeVisitNarrative(v, idx + 1, subject2);
  console.log(`[VISIT ${idx + 1}]: ${v.name} (${v.date})`);
  console.log(narrative);
  console.log('--------------------------------------------------------------------------------');
});

console.log('\n[OVERALL ADJUDICATION SUMMARY & LONGITUDINAL CLINICAL COURSE]');
console.log(synthesizeOverallSummary(subject2.visits, subject2));
console.log('\n================================================================================\n');
