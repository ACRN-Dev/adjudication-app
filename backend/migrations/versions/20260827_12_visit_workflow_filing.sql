-- Migration: 20260827_12_visit_workflow_filing
-- Forward: visit resolution/filing state, and deferred filing on signed case artifacts.
--
-- Guarded throughout: init_prod.py creates the model tables via create_all() before it
-- replays these files, so on a production database adjudication_visits already carries
-- these columns and a bare ADD COLUMN would abort the deploy.

BEGIN;

ALTER TABLE adjudication_visits ADD COLUMN IF NOT EXISTS status VARCHAR(40) NOT NULL DEFAULT 'IN_REVIEW';
ALTER TABLE adjudication_visits ADD COLUMN IF NOT EXISTS resolution_type VARCHAR(40);
ALTER TABLE adjudication_visits ADD COLUMN IF NOT EXISTS final_record_id UUID REFERENCES adjudication_records(id);
ALTER TABLE adjudication_visits ADD COLUMN IF NOT EXISTS finalized_at TIMESTAMP;
ALTER TABLE adjudication_visits ADD COLUMN IF NOT EXISTS filing_status VARCHAR(30) NOT NULL DEFAULT 'NOT_READY';
ALTER TABLE adjudication_visits ADD COLUMN IF NOT EXISTS filing_error TEXT;
CREATE INDEX IF NOT EXISTS ix_adjudication_visits_status ON adjudication_visits(status);
CREATE INDEX IF NOT EXISTS ix_adjudication_visits_filing_status ON adjudication_visits(filing_status);

ALTER TABLE signed_case_artifacts ALTER COLUMN storage_provider DROP NOT NULL;
ALTER TABLE signed_case_artifacts ALTER COLUMN storage_reference DROP NOT NULL;
ALTER TABLE signed_case_artifacts ALTER COLUMN filed_at DROP NOT NULL;
ALTER TABLE signed_case_artifacts ADD COLUMN IF NOT EXISTS filing_status VARCHAR(30) NOT NULL DEFAULT 'PENDING';
ALTER TABLE signed_case_artifacts ADD COLUMN IF NOT EXISTS filing_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE signed_case_artifacts ADD COLUMN IF NOT EXISTS filing_error TEXT;
CREATE INDEX IF NOT EXISTS ix_signed_case_artifacts_filing_status ON signed_case_artifacts(filing_status);

-- Migration guard: do not silently erase an unexpected historical diagnosis.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM adjudication_records WHERE signed = TRUE AND diagnosis IS NULL) THEN
    RAISE EXCEPTION 'Signed adjudication records with NULL diagnosis found; repair legacy diagnosis mapping before release';
  END IF;
END $$;

COMMIT;
