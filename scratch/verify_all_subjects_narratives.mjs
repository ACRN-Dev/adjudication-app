import fs from 'fs';
import assert from 'node:assert/strict';
import { normalizeVisitEvidence, formatVisitDate } from '../src/services/visitEvidence.js';

// Load VisitEvidenceSections.jsx to extract buildVisitNarrative
const vesCode = fs.readFileSync('src/components/VisitEvidenceSections.jsx', 'utf8');

// We can test the narrative generation directly
const pts = JSON.parse(fs.readFileSync('scratch/sample_participants.json', 'utf8'));

let totalVisitsChecked = 0;
let notPerformedCount = 0;
let performedCount = 0;

for (const p of pts) {
  console.log(`\n================ Participant ${p.id} ================`);
  const normalized = normalizeVisitEvidence(p);
  
  for (const v of normalized) {
    totalVisitsChecked++;
    const vNum = v.visit_number;
    
    // Check performance
    if (v.is_not_performed) {
      notPerformedCount++;
      assert.ok(v.not_performed_reason, `Visit ${vNum} marked not performed must have reason`);
      console.log(`  Visit ${vNum} [NOT PERFORMED]: ${v.not_performed_reason}`);
    } else {
      performedCount++;
      assert.ok(v.date, `Performed visit ${vNum} must have resolved date`);
      assert.notEqual(formatVisitDate(v.date), 'Date not documented', `Performed visit ${vNum} cannot have "Date not documented"`);
      console.log(`  Visit ${vNum} [PERFORMED]: Date = ${formatVisitDate(v.date)} | GA = ${v.gestationalLabel || 'N/A'}`);
    }
  }
}

console.log(`\nAll checks passed!`);
console.log(`Total visits checked: ${totalVisitsChecked}`);
console.log(`Performed visits: ${performedCount}`);
console.log(`Not performed visits: ${notPerformedCount}`);
