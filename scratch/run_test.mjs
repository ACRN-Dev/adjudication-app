import fs from 'fs';
import { normalizeVisitEvidence, formatVisitDate } from '../src/services/visitEvidence.js';

const pts = JSON.parse(fs.readFileSync('scratch/sample_participants.json', 'utf8'));
for (const p of pts) {
  console.log('\n--- Participant:', p.id, '---');
  const normalized = normalizeVisitEvidence(p);
  for (const v of normalized) {
    const rawReason = v.evidence?.visit_date?.[0]?.value || v.observations?.find(o => o.source_field_label?.includes('not performing'))?.raw_source_value;
    console.log(`Visit ${v.visit_number} (${v.label}): date=${v.date} (${formatVisitDate(v.date)}), ga=${v.gestationalLabel}, bp=${v.vitals?.bp || 'none'}, labs=${v.labs?.length}, obsCount=${v.observations?.length}, rawReason=${rawReason}`);
  }
}
