import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { formatLabResult, inferLabInterpretation, normalizeVisitEvidence } from '../src/services/visitEvidence.js';
import { generateOverallNarrative, generateVisitNarrative, NARRATIVE_VERSION } from '../src/services/clinicalNarrative.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const sourcePath = path.join(here, 'latest_blinded_batch.json');
const outputPath = path.join(here, 'latest_blinded_presentations.json');
const payload = JSON.parse(fs.readFileSync(sourcePath, 'utf8'));

payload.narrative_version = NARRATIVE_VERSION;
payload.cases = payload.cases.map((caseData) => {
  const normalizedVisits = normalizeVisitEvidence(caseData);
  normalizedVisits.forEach((visit) => {
    visit.labs = (visit.labs || []).map((lab) => ({
      ...lab,
      display: formatLabResult(lab.key, lab.raw ?? lab.value, lab.unit),
      interpretation: inferLabInterpretation(lab.key, lab.value, lab.raw),
    }));
  });
  return {
    ...caseData,
    normalized_visits: normalizedVisits,
    visit_presentations: normalizedVisits.map((visit, index) => ({
      visit_number: visit.visit_number || index + 1,
      visit_code: visit.code || visit.name || `V${String(index + 1).padStart(2, '0')}`,
      presentation: generateVisitNarrative(visit, visit.visit_number || index + 1, caseData),
    })),
    overall_presentation: generateOverallNarrative(normalizedVisits, caseData),
  };
});

fs.writeFileSync(outputPath, JSON.stringify(payload, null, 2), 'utf8');
console.log(`Generated app-aligned presentations for ${payload.cases.length} cases at ${outputPath}`);
