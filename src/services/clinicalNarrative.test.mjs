import assert from 'node:assert/strict';
import { generateOverallNarrative, generateVisitNarrative } from './clinicalNarrative.js';
import { normalizeVisitEvidence } from './visitEvidence.js';

const row = (raw_source_value, field, numeric_value = null) => ({
  value: numeric_value ?? raw_source_value,
  numeric_value,
  raw_source_value,
  parsed_text_value: raw_source_value,
  source: { page: 'Sonographic Data', field },
});

const caseData = {
  age: 32,
  risk_summary: {
    age: 32,
    gravidity: 2,
    parity: 1,
    miscarriages: 0,
    stillbirths: 0,
    vaginal_deliveries: 0,
    c_sections: 1,
  },
  history: {
    conditions: [
      { field_key: 'does_the_participant_have_any_medical_history', value: 'No' },
      { field_key: 'did_participant_have_any_surgery', value: 'No' },
      { field_key: 'does_participant_have_any_ongoing_allergies', value: 'No' },
      { field_key: 'did_the_participant_take_any_prior_or_concomitant_medications_including_supplements_in_the_past_30_days', value: 'No' },
      { field_key: 'has_anyone_in_participant_family_ever_had_hypertension', value: 'Yes' },
    ],
    obstetric: [
      { field_key: 'if_yes_how_many_previous_pregnancies', value: '1' },
      { field_key: 'number_of_live_births', value: '1' },
      { field_key: 'number_of_cesarean_sections', value: '1' },
      { field_key: 'reason_for_cesarean_section', value: 'Maternal health issues' },
      { field_key: 'other_reason', value: 'cephalopelvic disproportion' },
      { field_key: 'does_participant_have_any_history_of_raised_blood_pressure_during_pregnancy', value: 'No' },
      { field_key: 'does_the_participant_have_any_history_of_preeclampsia_in_previous_pregnancies', value: 'No' },
      { field_key: 'does_the_participant_have_any_history_of_severe_preeclampsia_in_previous_pregnancies', value: 'No' },
      { field_key: 'does_the_participant_have_any_history_of_eclampsia_in_previous_pregnancies', value: 'No' },
      { field_key: 'does_the_participant_have_any_history_of_hellp_in_previous_pregnancies', value: 'No' },
      { field_key: 'does_the_participant_have_any_history_of_iugr_in_previous_pregnancies', value: 'No' },
    ],
  },
  visits: [{
    id: 'v01',
    name: 'V01',
    visit_number: 1,
    date: '2026-02-10T00:00:00',
    ga: '27 weeks, 0 days',
    evidence: {
      bp_systolic: [row('131', 'Systolic blood pressure', 131)],
      bp_diastolic: [row('75', 'Diastolic blood pressure', 75)],
      bp_systolic_recheck: [row('131', 'Systolic blood pressure recheck', 131)],
      bp_diastolic_recheck: [row('75', 'Diastolic blood pressure recheck', 75)],
      heart_rate: [row('69', 'Heart Rate', 69)],
      respiratory_rate: [row('16', 'Respiratory rate', 16)],
      o2_sat: [row('98', 'Oxygen saturation', 98)],
      temperature: [row('36.3', 'Body temperature', 36.3), row('Temporal', 'Temperature location')],
      weight: [row('60', 'Weight', 60)],
      ua_protein: [row('Negative', 'Urine protein results')],
      dating_anchor_date: [row('#1 - s:20:"11/18/2025 00:00:00 ";', 'First sonographic examination date', 1)],
      edd: [row('#1 - s:19:"5/12/2026 00:00:00 ";', 'Expected date of delivery', 1)],
      dating_anchor_ga: [
        row('#1 - s:2:"15";', 'Gestational age on scan', 1),
        row('#1 - s:1:"0";', 'Gestational age on scan', 1),
      ],
      efw: [row('# - Yes', 'Estimated US Fetal Weight'), row('#1 - s:3:"110";', 'Fetal Weight', 1)],
      fetal_presentation: [row('# - Yes', 'Ultrasound Presentation'), row('#1 - s:6:"breech";', 'Provide Ultrasound Presentation description', 1)],
      us_viability: [row('#1 - s:6:"Normal";', 'Fetal movement', 1)],
      fetal_heart_rate: [row('#1 - s:3:"161";', 'Fetal heart rate', 1)],
      afi: [row('#1 - s:6:"Normal";', 'Amniotic fluid volume', 1)],
      us_placenta: [row('#1 - s:6:"Normal";', 'Placenta position', 1)],
      cervical_length: [row('#1 - s:3:"3.3";', 'Cervical length', 1)],
    },
  }],
};

const visit = normalizeVisitEvidence(caseData)[0];
const narrative = generateVisitNarrative(visit, 1, caseData);

assert.match(narrative, /32-year-old G2P1 participant/);
assert.match(narrative, /weight was 60 kg/);
assert.match(narrative, /dating ultrasound was performed on .*Nov.*2025 at 15 weeks and 0 days/i);
assert.match(narrative, /estimated fetal weight of 110 g/);
assert.match(narrative, /breech presentation/);
assert.match(narrative, /fetal heart rate of 161 bpm/);
assert.match(narrative, /Fetal movement, amniotic-fluid volume and placental position were recorded as normal/i);
assert.match(narrative, /Cervical length was 3.3 cm/);
assert.doesNotMatch(narrative, /\b1 bpm/);
assert.doesNotMatch(narrative, /Hematology recorded|Biochemistry recorded|units.*unavailable/i);
assert.match(narrative, /Laboratory results are presented in the table below\.$/);

const unavailableCase = structuredClone(caseData);
unavailableCase.visits[0].evidence.efw = [row('# - No', 'Estimated US Fetal Weight')];
unavailableCase.visits[0].evidence.fetal_presentation = [row('# - No', 'Ultrasound Presentation')];
unavailableCase.visits[0].evidence.us_placenta = [row('#1 - s:8:"Not done";', 'Placenta position', 1)];
const unavailableVisit = normalizeVisitEvidence(unavailableCase)[0];
const unavailableNarrative = generateVisitNarrative(unavailableVisit, 1, unavailableCase);
assert.match(unavailableNarrative, /Estimated fetal weight, fetal presentation and placental position were not documented\./);
assert.doesNotMatch(unavailableNarrative, /negative (estimated fetal weight|fetal presentation|placental position)/i);

const overall = generateOverallNarrative([visit], caseData);
assert.doesNotMatch(overall, /Laboratory results are presented in the table below/);
assert.match(overall, /Source field unavailable; the delivery outcome cannot be determined from the supplied record/);
assert.match(overall, /\n\n/);

const clinicalRow = (raw_source_value, field, numeric_value = null, page = 'Clinical Assessment') => ({
  value: numeric_value ?? raw_source_value,
  numeric_value,
  raw_source_value,
  parsed_text_value: raw_source_value,
  source: { page, field },
});

const followUpCase = {
  id: 'FOLLOW-UP-001',
  delivery_date: '2026-05-02T00:00:00',
  visits: [
    {
      id: 'v02', name: 'V02', visit_number: 2, date: '2026-02-16T00:00:00', ga: '26 weeks, 4 days',
      evidence: {
        bp_systolic: [clinicalRow('116', 'Systolic blood pressure', 116)],
        bp_diastolic: [clinicalRow('63', 'Diastolic blood pressure', 63)],
        heart_rate: [clinicalRow('75', 'Heart rate', 75)],
        respiratory_rate: [clinicalRow('16', 'Respiratory rate', 16)],
        o2_sat: [clinicalRow('98', 'Oxygen saturation', 98)],
        temperature: [clinicalRow('36.1', 'Body temperature', 36.1), clinicalRow('Temporal', 'Temperature location')],
        weight: [clinicalRow('72', 'Weight', 72)],
        ua_protein: [clinicalRow('1+', 'Urine protein results', 1)],
        headache: [clinicalRow('No', 'Persistent headache?')],
        visual_disturbance: [clinicalRow('No', 'Visual disturbances?')],
        pe_symptom_sudden_weight_gain: [clinicalRow('No', 'Sudden weight gain?')],
        epigastric_pain: [clinicalRow('No', 'Epigastric pain?')],
        pulmonary_edema: [clinicalRow('No', 'Pulmonary edema')],
        medication_changes: [clinicalRow('No', 'Medication Changes')],
        new_adverse_events: [clinicalRow('No', 'New adverse events')],
        changed_adverse_events: [clinicalRow('No', 'Changed adverse events')],
      },
    },
    {
      id: 'v03', name: 'V03', visit_number: 3, date: '2026-02-23T13:40:00', ga: '27 weeks, 4 days',
      evidence: {
        bp_systolic: [clinicalRow('142', 'Systolic blood pressure', 142), clinicalRow('140', 'Systolic blood pressure', 140)],
        bp_diastolic: [clinicalRow('87', 'Diastolic blood pressure', 87), clinicalRow('85', 'Diastolic blood pressure', 85)],
        ua_protein: [clinicalRow('2+', 'Urine protein results', 2)],
        new_adverse_events: [clinicalRow('Yes', 'New adverse events')],
        changed_adverse_events: [clinicalRow('Yes', 'Changed adverse events')],
        us_date: [clinicalRow('#1 - s:19:"2/23/2026 00:00:00 ";', 'Scan date', 1, 'Sonographic Data')],
        efw: [clinicalRow('#1 - s:8:"Assessed";', 'Estimated US Fetal Weight', 1, 'Sonographic Data')],
        fetal_presentation: [clinicalRow('# - Yes', 'Ultrasound Presentation', null, 'Sonographic Data')],
        us_viability: [clinicalRow('#1 - s:6:"Normal";', 'Fetal movement', 1, 'Sonographic Data')],
        fetal_heart_rate: [clinicalRow('#1 - s:3:"148";', 'Fetal heart rate', 1, 'Sonographic Data')],
        afi: [clinicalRow('#1 - s:6:"Normal";', 'Amniotic fluid volume', 1, 'Sonographic Data')],
        us_placenta: [clinicalRow('#1 - s:6:"Normal";', 'Placenta position', 1, 'Sonographic Data')],
      },
    },
    {
      id: 'v04', name: 'V04', visit_number: 4, date: '2026-03-09T00:00:00', ga: '29 weeks, 4 days',
      evidence: {
        bp_systolic: [clinicalRow('115', 'Systolic blood pressure', 115), clinicalRow('112', 'Systolic blood pressure', 112)],
        bp_diastolic: [clinicalRow('73', 'Diastolic blood pressure', 73)],
        ua_protein: [clinicalRow('1+', 'Urine protein results', 1)],
      },
    },
    {
      id: 'v06', name: 'V06', visit_number: 6, date: '2026-06-01T11:13:00',
      evidence: {
        bp_systolic: [clinicalRow('150', 'Systolic blood pressure', 150), clinicalRow('144', 'Systolic blood pressure', 144)],
        bp_diastolic: [clinicalRow('90', 'Diastolic blood pressure', 90), clinicalRow('88', 'Diastolic blood pressure', 88)],
        health_status: [clinicalRow('Unchanged', 'Final Health Status'), clinicalRow('PATIENT IS CLINICALLY STABLE', 'Final Health Status Description')],
        ua_protein: [clinicalRow('Negative', 'Urine protein results')],
        neonatal_gender: [clinicalRow('F', 'Gender')],
        newborn_weight_g: [clinicalRow('2560', 'Birth Weight', 2560)],
        neonatal_length: [clinicalRow('49', 'Length', 49)],
        neonatal_hc: [clinicalRow('34', 'Head circumference', 34)],
        neonatal_heart_rate: [clinicalRow('140', 'Heart rate', 140)],
        neonatal_respiratory_exam: [clinicalRow('43', 'Respiration', 43)],
        apgar_1m: [clinicalRow('9', 'Apgar Score at 1 Minute', 9)],
        apgar_5m: [clinicalRow('9', 'Apgar Score at 5 Minutes', 9)],
        apgar_10m: [clinicalRow('9', 'Apgar Score at 10 Minutes', 9)],
      },
    },
    {
      id: 'v04-missed', name: 'V04', visit_number: 4,
      evidence: { visit_date: [clinicalRow('Missed visit', 'Reason for not performing visit')] },
    },
  ],
};

const followUps = normalizeVisitEvidence(followUpCase);
const v2Narrative = generateVisitNarrative(followUps[0], 2, followUpCase);
assert.match(v2Narrative, /On Feb 16, 2026, at 26 weeks and 4 days/);
assert.match(v2Narrative, /Urine protein dipstick was 1\+\./);
assert.match(v2Narrative, /No obstetric ultrasound was documented for this visit\./);
assert.doesNotMatch(v2Narrative, /single viable|1 protein/i);

const v3Narrative = generateVisitNarrative(followUps[1], 3, followUpCase);
assert.match(v3Narrative, /142\/87 mmHg.*140\/85 mmHg/);
assert.match(v3Narrative, /Urine protein dipstick was 2\+\./);
assert.match(v3Narrative, /fetal heart rate was 148 bpm/i);
assert.match(v3Narrative, /marked “Assessed,” but no numerical weight was supplied/);
assert.match(v3Narrative, /presentation description was unavailable/);
assert.doesNotMatch(v3Narrative, /single viable|estimated fetal weight was Assessed/i);

const v4Narrative = generateVisitNarrative(followUps[2], 4, followUpCase);
assert.match(v4Narrative, /additional systolic measurement of 112 mmHg.*without a corresponding diastolic/);

const v6Narrative = generateVisitNarrative(followUps[3], 6, followUpCase);
assert.match(v6Narrative, /30 days after the documented delivery/);
assert.match(v6Narrative, /150\/90 mmHg.*144\/88 mmHg/);
assert.match(v6Narrative, /clinically stable/i);
assert.match(v6Narrative, /female infant.*2,560 g/);
assert.doesNotMatch(v6Narrative, /recovery was unremarkable|obstetric ultrasound|viable fetus/i);

const missedNarrative = generateVisitNarrative(followUps[4], 4, followUpCase);
assert.match(missedNarrative, /source-recorded reason was “Missed visit.”/);
assert.match(missedNarrative, /No clinical measurements, laboratory results or imaging are attributed/);
assert.doesNotMatch(
  generateOverallNarrative(followUps.slice(0, 4), followUpCase),
  /source-recorded interpretations are presented in the table below/,
);

const emptyDeliveryCase = {
  id: 'NO-DELIVERY-001',
  visits: [{ id: 'v05', name: 'V05', visit_number: 5, evidence: {} }],
};
const emptyDeliveryVisit = normalizeVisitEvidence(emptyDeliveryCase)[0];
assert.equal(generateVisitNarrative(emptyDeliveryVisit, 5, emptyDeliveryCase), '');
assert.match(generateOverallNarrative([emptyDeliveryVisit], emptyDeliveryCase), /Source field unavailable; the delivery outcome cannot be determined from the supplied record/);
assert.doesNotMatch(generateOverallNarrative([emptyDeliveryVisit], emptyDeliveryCase), /\[V05\]/);

const deliveryRow = (rawValue, field, numericValue = null, page = 'Delivery Outcome') =>
  clinicalRow(rawValue, field, numericValue, page);

const stillbirthCase = {
  id: 'STILLBIRTH-001',
  visits: [
    { id: 'v01', name: 'V01', visit_number: 1, date: '2026-02-10T00:00:00', ga_days: 189, evidence: {} },
    {
      id: 'v05', name: 'V05', visit_number: 5, date: '2026-02-23T00:00:00',
      evidence: {
        delivery_date: [
          deliveryRow('2/19/2026 00:00:00', 'Date of Delivery'),
          deliveryRow('2/23/2026 00:00:00', 'Delivery Outcome Status Assessment Date'),
        ],
        delivery_mode: [deliveryRow('Vaginal', 'Type of Delivery')],
        ega_delivery: [
          deliveryRow('28', 'Gestational Age at Delivery', 28),
          deliveryRow('2', 'Gestational Age at Delivery', 2),
          deliveryRow('27', 'Gestational Age', 27, 'Newborn Assessment Form'),
        ],
        pregnancy_outcome: [deliveryRow('Stillbirth', 'Pregnancy Outcome')],
        delivery_outcome: [
          deliveryRow('Yes', 'Any Complications at Delivery?'),
          deliveryRow('Stillbirth delivery', 'Delivery Complications Description'),
          deliveryRow('No', 'Infection Post-Delivery'),
          deliveryRow('Normal', 'Postpartum Health Status'),
          deliveryRow('3', 'How many days did participant stay in hospital?', 3),
          deliveryRow('No', 'Was participant readmitted to hospital?'),
        ],
        ebl_ml: [deliveryRow('450', 'Estimated Blood Loss', 450)],
        blood_transfusion: [deliveryRow('No', 'Blood Transfusion')],
        health_status: [deliveryRow('Unchanged', 'Health Status')],
        health_status_description: [deliveryRow('Clinically stable', 'Health Status Description')],
      },
    },
  ],
};
const stillbirthVisit = normalizeVisitEvidence(stillbirthCase).find((item) => item.visit_number === 5);
const stillbirthNarrative = generateVisitNarrative(stillbirthVisit, 5, stillbirthCase);
assert.match(stillbirthNarrative, /Vaginal delivery occurred on Feb 19, 2026 at 28 weeks and 2 days of gestation\./);
assert.match(stillbirthNarrative, /outcome assessment was completed on Feb 23, 2026/);
assert.match(stillbirthNarrative, /pregnancy outcome was recorded as stillbirth/);
assert.match(stillbirthNarrative, /blood loss was 450 mL/);
assert.match(stillbirthNarrative, /No blood transfusion.*No postpartum infection.*hospital for 3 days.*not readmitted/s);
assert.match(stillbirthNarrative, /No neonatal anthropometric measurements, Apgar scores or neonatal vital signs were documented/);
assert.match(stillbirthNarrative, /Newborn Assessment field recorded gestational age as 27 weeks.*conflicts.*28 weeks and 2 days/s);
assert.doesNotMatch(stillbirthNarrative, /No complication at delivery|Lab results|Laboratory results/i);

const liveBirthCase = {
  id: 'LIVE-BIRTH-001',
  visits: [
    { id: 'v01', name: 'V01', visit_number: 1, date: '2026-02-09T00:00:00', ga_days: 179, evidence: {} },
    {
      id: 'v05', name: 'V05', visit_number: 5, date: '2026-05-04T00:00:00',
      evidence: {
        delivery_date: [
          deliveryRow('5/2/2026 00:00:00', 'Date of Delivery'),
          deliveryRow('5/4/2026 00:00:00', 'Delivery Outcome Status Assessment Date'),
        ],
        delivery_mode: [deliveryRow('Vaginal', 'Type of Delivery')],
        ega_delivery: [deliveryRow('37', 'Gestational Age at Delivery', 37), deliveryRow('2', 'Gestational Age at Delivery', 2)],
        pregnancy_outcome: [deliveryRow('Live birth', 'Pregnancy Outcome')],
        delivery_outcome: [
          deliveryRow('No', 'Any Complications at Delivery?'),
          deliveryRow('No', 'Infection Post-Delivery'),
          deliveryRow('Normal', 'Postpartum Health Status'),
          deliveryRow('2', 'How many days did participant stay in hospital?', 2),
          deliveryRow('No', 'Was participant readmitted to hospital?'),
        ],
        ebl_ml: [deliveryRow('200', 'Estimated Blood Loss', 200)],
        blood_transfusion: [deliveryRow('No', 'Blood Transfusion')],
        health_status: [deliveryRow('Improved', 'Health Status')],
        health_status_description: [deliveryRow('Clinically stable', 'Health Status Description')],
        neonatal_gender: [deliveryRow('F', 'Gender', null, 'Newborn Assessment Form')],
        newborn_weight_g: [deliveryRow('2560', 'Birth Weight', 2560, 'Newborn Assessment Form')],
        neonatal_length: [deliveryRow('49', 'Length', 49, 'Newborn Assessment Form')],
        neonatal_hc: [deliveryRow('34', 'Head Circumference', 34, 'Newborn Assessment Form')],
        apgar_1m: [deliveryRow('9', 'Apgar Score at 1 Minute', 9, 'Newborn Assessment Form')],
        apgar_5m: [deliveryRow('9', 'Apgar Score at 5 Minutes', 9, 'Newborn Assessment Form')],
        apgar_10m: [deliveryRow('9', 'Apgar Score at 10 Minutes', 9, 'Newborn Assessment Form')],
        neonatal_heart_rate: [deliveryRow('140', 'Heart Rate', 140, 'Newborn Assessment Form')],
        neonatal_respiratory_exam: [deliveryRow('43', 'Respiration', 43, 'Newborn Assessment Form')],
        birth_complications: [deliveryRow('No', 'Birth Complications', null, 'Newborn Assessment Form')],
        congenital_anomalies: [deliveryRow('No', 'Congenital Anomalies', null, 'Newborn Assessment Form')],
        neonatal_icu_admission: [deliveryRow('No', 'NICU Admission', null, 'Newborn Assessment Form')],
        neonatal_rds: [deliveryRow('No', 'Respiratory Distress Syndrome', null, 'Newborn Assessment Form')],
        neonatal_ivh: [deliveryRow('No', 'Intraventricular Haemorrhage', null, 'Newborn Assessment Form')],
      },
    },
  ],
};
const liveBirthVisit = normalizeVisitEvidence(liveBirthCase).find((item) => item.visit_number === 5);
const liveBirthNarrative = generateVisitNarrative(liveBirthVisit, 5, liveBirthCase);
assert.match(liveBirthNarrative, /Vaginal delivery occurred on May 02, 2026 at 37 weeks and 2 days of gestation\./);
assert.match(liveBirthNarrative, /No complication at delivery was recorded/);
assert.match(liveBirthNarrative, /liveborn female infant.*2,560 g.*length 49 cm.*head circumference 34 cm/s);
assert.match(liveBirthNarrative, /Apgar scores were 9, 9 and 9.*heart rate was 140 bpm.*respiratory rate was 43 breaths\/min/s);
assert.match(liveBirthNarrative, /No neonatal intensive-care admission, respiratory distress syndrome, intraventricular haemorrhage, congenital anomaly or birth complication was recorded/);
assert.doesNotMatch(liveBirthNarrative, /Lab results|Laboratory results|for a Vaginal|Normal baby/i);

const maternalRespirationOnlyCase = {
  delivery_date: '2026-02-19T00:00:00',
  visits: [{
    id: 'v06-maternal-only', name: 'V06', visit_number: 6, date: '2026-03-23T00:00:00',
    evidence: { respiratory_rate: [clinicalRow('14', 'Respiratory Rate', 14)] },
  }],
};
const maternalRespirationOnlyVisit = normalizeVisitEvidence(maternalRespirationOnlyCase)[0];
const maternalRespirationOnlyNarrative = generateVisitNarrative(maternalRespirationOnlyVisit, 6, maternalRespirationOnlyCase);
assert.match(maternalRespirationOnlyNarrative, /No infant assessment was documented at this visit/);
assert.doesNotMatch(maternalRespirationOnlyNarrative, /infant.*respiratory rate was 14/i);

console.log(narrative);
console.log('clinical narrative V1-V6 tests passed');
