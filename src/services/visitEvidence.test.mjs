import assert from 'node:assert/strict';
import {
  buildLongitudinalRows,
  formatInterval,
  isVisitComplete,
  minutesBetween,
  normalizeVisitEvidence,
  pairBpReadings,
} from './visitEvidence.js';

const caseData = {
  id: 'SYNTHETIC-001',
  derivedSubtype: 'EOPE',
  derivedSeverity: 'SEVERE_FEATURES',
  visits: [
    { id: 'v01', name: 'V01', date: '2026-03-01T08:00:00Z', ga: '12+4', evidence: {} },
    {
      id: 'v04',
      name: 'V04',
      date: '2026-04-21T08:00:00Z',
      ga: '31+2',
      evidence: {
        SBP: [
          { value: '162', observed_at: '2026-04-21T08:14:00Z', source: { form: 'Vitals' }, severe: true },
          { value: '168', observed_at: '2026-04-21T12:40:00Z', source: { form: 'Vitals' }, severe: true },
        ],
        DBP: [
          { value: '112', observed_at: '2026-04-21T08:14:00Z', source: { form: 'Vitals' }, severe: true },
          { value: '114', observed_at: '2026-04-21T12:40:00Z', source: { form: 'Vitals' }, severe: true },
        ],
        PLATELETS: [{ value: '92', unit: 'x10^3/uL', observed_at: '2026-04-21T14:05:00Z', severe: true }],
        CREATININE: [{ value: '1.31', unit: 'mg/dL', observed_at: '2026-04-21T14:05:00Z', abnormal: true }],
        ALT: [
          { value: '62', unit: 'U/L', observed_at: '2026-04-21T13:05:00Z', abnormal: true },
          { value: '78', unit: 'U/L', observed_at: '2026-04-21T14:05:00Z', abnormal: true },
        ],
        UPCR: [{ value: '1.84', unit: 'g/g', observed_at: '2026-04-21T14:10:00Z', abnormal: true }],
        SFLT1_PLGF_RATIO: [{ value: '99', evidence_state: 'AVAILABLE' }],
      },
    },
    {
      id: 'v02',
      name: 'V02',
      date: '2026-03-31T09:43:00Z',
      evidence: {
        SBP: [
          { value: '120', observed_at: '2026-03-31T09:43:00Z', source: { form: 'Visit 2', field: 'Systolic blood pressure' } },
          { value: 'Yes', observed_at: '2026-03-31T09:48:00Z', source: { form: 'Visit 2', field: 'Elevated systolic blood pressure?' } },
        ],
        DBP: [{ value: '62', observed_at: '2026-03-31T09:43:00Z', source: { form: 'Visit 2', field: 'Diastolic blood pressure' } }],
        SBP_RECHECK: [{ value: '120', observed_at: '2026-03-31T09:48:00Z', source: { form: 'Visit 2', field: 'Systolic blood pressure recheck' } }],
        DBP_RECHECK: [{ value: '62', observed_at: '2026-03-31T09:48:00Z', source: { form: 'Visit 2', field: 'Diastolic blood pressure recheck' } }],
      },
    },
    {
      id: 'v05',
      name: 'V05',
      date: '2026-04-28T08:00:00Z',
      evidence: {
        UPCR: [{ value: 'Pending', evidence_state: 'PENDING' }],
        AST: [{ value: 'Conflict between source and LIMS', evidence_state: 'CONFLICTING' }],
      },
      resolution_status: 'CONCORDANT',
    },
  ],
};

const visits = normalizeVisitEvidence(caseData);
assert.equal(visits.length, 4);
assert.equal(visits[1].bp.length, 2, 'keeps multiple BP observations from the same visit');
assert.equal(visits[1].labs.some((row) => /SFLT|PLGF/i.test(row.key)), false, 'blinded biomarkers are withheld');
assert.equal(minutesBetween('2026-04-21T08:14:00Z', '2026-04-21T12:40:00Z'), 266);
assert.equal(formatInterval(266), '4 h 26 min');
assert.equal(pairBpReadings(visits[1].bp)[0].confirmed, true);
assert.equal(visits[2].bp.length, 2, 'V2 has one initial and one recheck reading, not flag rows');
assert.equal(pairBpReadings(visits[2].bp).length, 1, 'V2 initial and recheck render as one BP card');
assert.equal(visits[0].interpretation.missing.includes('Blood pressure'), true);
assert.equal(visits[3].proteinuria[0].evidence_state, 'pending');
assert.equal(visits[3].labs[0].evidence_state, 'conflicting');
assert.equal(isVisitComplete(visits[3]), true);
assert.equal(isVisitComplete({ signed: true, status: 'SIGNED' }), false, 'one reviewer signature does not unlock overall final adjudication');

const legacy = normalizeVisitEvidence({
  id: 'LEGACY-001',
  gaAtEvent: '33+0',
  bpLog: [{ date: '2026-07-28 10:15', sbp: 164, dbp: 108, severe: true }],
  labLog: [{ analyte: 'Platelet Count', result: '88', unit: 'x10^3/uL', severe: true }],
  proteinuriaLog: [{ method: 'Dipstick', result: '2+', date: '2026-07-28' }],
});
assert.equal(legacy[0].name, 'Unassigned dated evidence');
assert.equal(legacy[0].bp.length, 1);

const rows = buildLongitudinalRows(visits);
assert.ok(rows.find((row) => row.key === 'creatinine').cells[1].value.includes('1.31'));
assert.ok(rows.find((row) => row.key === 'alt').cells[1].value.includes('78'));

console.log('visitEvidence service tests passed');
