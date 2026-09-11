-- Fetal/neonatal outcome fields added to the canonical models (visit5_service) but never
-- given a matching migration, so init-prod's schema-drift check flags them on every deploy.
ALTER TABLE adjudication_visits ADD COLUMN IF NOT EXISTS final_fetal_assessments JSON;

ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS fetal_neonatal_assessments JSON;
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS gestational_age_at_delivery FLOAT;
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS pregnancy_outcome VARCHAR(100);
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS fetal_assessment_status VARCHAR(50);
ALTER TABLE adjudication_records ADD COLUMN IF NOT EXISTS fetal_neonatal_provenance JSON;

ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS final_fetal_assessments JSON;
ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS final_ga_at_delivery FLOAT;
ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS final_pregnancy_outcome VARCHAR(100);
ALTER TABLE committee_decisions ADD COLUMN IF NOT EXISTS fetal_neonatal_provenance JSON;
