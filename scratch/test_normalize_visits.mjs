import sqlite3 from 'sqlite3';
import { normalizeVisitEvidence, formatVisitDate } from './src/services/visitEvidence.js';

const db = new sqlite3.Database('backend/acrn_demo.db');

db.all("SELECT id, blinded_subject_id FROM longitudinal_participants", (err, pts) => {
  if (err) {
    console.error(err);
    process.exit(1);
  }
  console.log(`Found ${pts.length} participants.`);
  
  // Pick first 2 participants
  for (const p of pts.slice(0, 2)) {
    console.log(`\n================ Participant ${p.blinded_subject_id} ================`);
    db.all(`
      SELECT id, scheduled_visit_code, visit_sequence, visit_datetime, gestational_age_days, form_title 
      FROM visit_instances 
      WHERE participant_id = ? AND scheduled_visit_code IN ('V01','V02','V03','V04','V05','V06')
      ORDER BY visit_sequence
    `, [p.id], (err, visits) => {
      if (err) { console.error(err); return; }
      
      const vPromises = visits.map(v => new Promise((resolve) => {
        db.all("SELECT canonical_variable, raw_source_value, observation_datetime, source_field_label FROM canonical_observations WHERE visit_id = ?", [v.id], (err, obs) => {
          const evidence = {};
          (obs || []).forEach(o => {
            if (!evidence[o.canonical_variable]) evidence[o.canonical_variable] = [];
            evidence[o.canonical_variable].push({
              value: o.raw_source_value,
              raw_source_value: o.raw_source_value,
              observed_at: o.observation_datetime,
              source_field_label: o.source_field_label
            });
          });
          resolve({
            id: v.id,
            visit_number: v.visit_sequence,
            scheduled_visit_code: v.scheduled_visit_code,
            name: v.scheduled_visit_code,
            date: v.visit_datetime,
            gestational_age_days: v.gestational_age_days,
            evidence,
            observations: obs || []
          });
        });
      }));

      Promise.all(vPromises).then(loadedVisits => {
        const normalized = normalizeVisitEvidence({ id: p.blinded_subject_id, visits: loadedVisits });
        normalized.forEach(v => {
          console.log(`Visit ${v.visit_number} (${v.label}): date=${v.date} (${formatVisitDate(v.date)}), ga=${v.gestationalLabel}, bpCount=${v.bp.length}, labCount=${v.labs.length}`);
        });
      });
    });
  }
});
